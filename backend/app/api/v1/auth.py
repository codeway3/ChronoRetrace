from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.security import (
    check_rate_limit,
    get_current_active_user,
    log_user_activity,
)
from ...infrastructure.database.models import (
    User,
    UserPreferences,
    UserRole,
    UserRoleAssignment,
)
from ...infrastructure.database.session import get_db
from ...schemas.auth_schemas import (
    ApiResponse,
    PasswordChange,
    PasswordReset,
    PasswordResetConfirm,
    Token,
    TokenRefresh,
    UserCreate,
    UserLogin,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    UserResponse,
)
from ...services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/register", response_model=ApiResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate, request: Request, db: Session = Depends(get_db)
):
    """用户注册"""
    # 检查频率限制
    check_rate_limit(request)

    # 检查用户名是否已存在
    existing_user = (
        db.query(User)
        .filter(
            (User.username == user_data.username) | (User.email == user_data.email)  # type: ignore
        )
        .first()
    )

    if existing_user:
        if existing_user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已被注册"
            )

    # 创建新用户
    hashed_password = auth_service.hash_password(user_data.password)

    new_user = User()
    new_user.username = user_data.username
    new_user.email = user_data.email
    new_user.full_name = user_data.full_name
    new_user.password_hash = hashed_password
    new_user.is_active = True

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 分配默认用户角色
    user_role = db.query(UserRole).filter_by(name="user").first()
    if user_role:
        role_assignment = UserRoleAssignment()
        role_assignment.user_id = new_user.id
        role_assignment.role_id = user_role.id
        db.add(role_assignment)

    # 创建默认用户偏好设置
    user_preferences = UserPreferences()
    user_preferences.user_id = new_user.id
    user_preferences.theme_mode = "light"
    user_preferences.language = "zh-CN"
    user_preferences.timezone = "Asia/Shanghai"
    db.add(user_preferences)
    db.commit()

    # 记录用户活动
    log_user_activity(new_user, "user_registered", None, request, db)

    return ApiResponse(
        success=True, message="用户注册成功", data={"user_id": new_user.id}
    )


@router.post("/login", response_model=Token)
async def login(
    user_credentials: UserLogin, request: Request, db: Session = Depends(get_db)
):
    """用户登录"""
    # 检查频率限制
    check_rate_limit(request)

    # 验证用户凭据
    user = auth_service.authenticate_user(
        db, user_credentials.username, user_credentials.password
    )

    if not user:
        # 记录失败的登录尝试
        log_user_activity(
            None, "login_failed", f"用户名: {user_credentials.username}", request, db
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    # 创建访问令牌和刷新令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    refresh_token = auth_service.create_refresh_token(data={"sub": str(user.id)})

    # 创建用户会话
    # 获取客户端IP地址,优先使用X-Forwarded-For头,如果不存在则使用连接的远程地址
    client_host = request.client.host if request.client else "unknown"
    ip_address = request.headers.get("X-Forwarded-For", client_host)
    user_agent = request.headers.get("user-agent", "unknown")

    auth_service.create_user_session(db, user.id, refresh_token, ip_address, user_agent)

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # 记录登录活动
    log_user_activity(user, "user_login", None, request, db)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(user),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh, request: Request, db: Session = Depends(get_db)
):
    """刷新访问令牌"""
    # 验证刷新令牌
    payload = auth_service.verify_token(token_data.refresh_token, "refresh")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        )

    # 验证会话
    session = auth_service.validate_session(db, token_data.refresh_token)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="会话已过期或无效"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter_by(id=user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被禁用"
        )

    # 创建新的访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    # 记录令牌刷新活动
    log_user_activity(user, "token_refreshed", None, request, db)

    return Token(
        access_token=access_token,
        refresh_token=token_data.refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.from_orm(user),
    )


@router.post("/logout", response_model=ApiResponse)
async def logout(
    token_data: TokenRefresh,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """用户登出"""
    # 使刷新令牌失效
    auth_service.invalidate_session(db, token_data.refresh_token)

    # 记录登出活动
    log_user_activity(current_user, "user_logout", None, request, db)

    return ApiResponse(success=True, message="登出成功")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/change-password", response_model=ApiResponse)
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    # 验证当前密码
    if not auth_service.verify_password(
        password_data.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="当前密码错误"
        )

    # 更新密码
    new_password_hash = auth_service.hash_password(password_data.new_password)
    current_user.password_hash = new_password_hash
    current_user.updated_at = datetime.utcnow()

    db.commit()

    # 记录密码修改活动
    log_user_activity(current_user, "password_changed", None, request, db)

    return ApiResponse(success=True, message="密码修改成功")


@router.post("/reset-password", response_model=ApiResponse)
async def reset_password(
    reset_data: PasswordReset, request: Request, db: Session = Depends(get_db)
):
    """请求密码重置"""
    # 检查频率限制
    check_rate_limit(request)

    user = db.query(User).filter_by(email=reset_data.email).first()
    if not user:
        # 为了安全, 即使用户不存在也返回成功消息
        return ApiResponse(success=True, message="如果邮箱存在, 重置链接已发送")

    # 生成重置令牌
    reset_token = auth_service.create_password_reset_token(user.id)

    # 这里应该发送邮件, 暂时只记录日志
    log_user_activity(
        user, "password_reset_requested", f"重置令牌: {reset_token}", request, db
    )

    return ApiResponse(
        success=True,
        message="如果邮箱存在, 重置链接已发送",
        data={"reset_token": reset_token},  # 生产环境中不应返回令牌
    )


@router.post("/reset-password/confirm", response_model=ApiResponse)
async def confirm_password_reset(
    reset_data: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)
):
    """确认密码重置"""
    # 验证重置令牌
    user_id = auth_service.verify_password_reset_token(reset_data.token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效或已过期的重置令牌"
        )

    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    # 更新密码
    new_password_hash = auth_service.hash_password(reset_data.new_password)
    user.password_hash = new_password_hash
    user.updated_at = datetime.utcnow()

    db.commit()

    # 记录密码重置活动
    log_user_activity(user, "password_reset_completed", None, request, db)

    return ApiResponse(success=True, message="密码重置成功")


@router.get("/preferences", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """获取用户偏好设置"""
    preferences = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="用户偏好设置不存在"
        )

    return preferences


@router.put("/preferences", response_model=UserPreferencesResponse)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """更新用户偏好设置"""
    preferences = db.query(UserPreferences).filter_by(user_id=current_user.id).first()

    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="用户偏好设置不存在"
        )

    # 更新偏好设置
    update_data = preferences_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)

    # 记录偏好设置更新活动
    log_user_activity(
        current_user, "preferences_updated", str(update_data), request, db
    )

    return preferences
