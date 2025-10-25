from __future__ import annotations

import os
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi_cache import FastAPICache
from redis import asyncio as aioredis

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import log_user_activity, require_admin
from app.data.managers import database_admin as db_admin
from app.infrastructure.database.models import (
    User,
    UserActivityLog,
    UserPreferences,
    UserRole,
    UserRoleAssignment,
    UserSession,
)
from app.infrastructure.database.session import get_db
from app.schemas.auth_schemas import (
    ApiResponse,
    PaginatedResponse,
    UserResponse,
    UserSessionResponse,
    UserUpdate,
)
from app.services.auth_service import auth_service

router = APIRouter()


@router.get("/redis-health", status_code=200)
async def redis_health_check():
    """
    Checks the health of the Redis connection.
    """
    try:
        redis = await aioredis.from_url(settings.REDIS_URL)
        await redis.ping()
        await redis.close()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Redis connection failed.",
                "error_details": str(e),
            },
        ) from e
    else:
        return {"status": "ok", "message": "Redis connection is healthy."}


@router.post("/clear-cache", status_code=200)
async def clear_cache(db: Session = Depends(get_db)):
    """
    Endpoint to clear all cached financial data from the database and Redis.
    Intended for development and testing purposes.
    """
    try:
        # Clear database cache
        db_result = db_admin.clear_all_financial_data(db)

        # Clear Redis cache
        await FastAPICache.clear()

        db_result["message"] = (
            "All database and Redis cache has been cleared successfully."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Failed to clear cache.",
                "error_details": str(e),
            },
        ) from e
    else:
        return db_result


@router.post("/init-admin", response_model=ApiResponse)
async def initialize_admin_account(request: Request, db: Session = Depends(get_db)):
    """初始化默认管理员账号"""
    try:
        # 检查是否已存在管理员
        admin_criterion = cast("Any", (UserRole.name == "admin"))
        admin_role = db.query(UserRole).filter(admin_criterion).first()
        if admin_role:
            admin_exists_criterion = cast(
                "Any", (UserRoleAssignment.role_id == admin_role.id)
            )
            admin_exists = (
                db.query(UserRoleAssignment).filter(admin_exists_criterion).first()
            )
            if admin_exists:
                return ApiResponse(success=False, message="管理员账号已存在")

        roles_to_create = [
            {"name": "admin", "description": "系统管理员", "permissions": "*"},
            {"name": "moderator", "description": "版主", "permissions": "moderate"},
            {"name": "user", "description": "普通用户", "permissions": "read"},
        ]

        for role_data in roles_to_create:
            role_exists_criterion = cast("Any", (UserRole.name == role_data["name"]))
            existing_role = db.query(UserRole).filter(role_exists_criterion).first()
            if not existing_role:
                new_role = UserRole()
                new_role.name = role_data["name"]
                new_role.description = role_data["description"]
                new_role.permissions = role_data["permissions"]
                db.add(new_role)

        db.commit()

        # 创建默认管理员用户
        admin_username = "admin"
        admin_email = "admin@chronoretrace.com"
        # 通过环境变量提供初始管理员密码，否则生成一个安全随机密码
        admin_password = os.getenv("ADMIN_INITIAL_PASSWORD") or secrets.token_urlsafe(
            16
        )

        # 检查管理员用户是否已存在
        existing_admin_criterion = cast(
            "Any",
            ((User.username == admin_username) | (User.email == admin_email)),
        )
        existing_admin = db.query(User).filter(existing_admin_criterion).first()

        if existing_admin:
            return ApiResponse(success=False, message="管理员用户已存在")

        # 创建管理员用户
        hashed_password = auth_service.hash_password(admin_password)
        admin_user = User()
        admin_user.username = admin_username
        admin_user.email = admin_email
        admin_user.full_name = "系统管理员"
        admin_user.password_hash = hashed_password
        admin_user.is_active = True

        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # 分配管理员角色
        admin_role = db.query(UserRole).filter(admin_criterion).first()
        if admin_role:
            role_assignment = UserRoleAssignment()
            role_assignment.user_id = admin_user.id
            role_assignment.role_id = admin_role.id
            db.add(role_assignment)

        # 创建默认偏好设置
        admin_preferences = UserPreferences()
        admin_preferences.user_id = admin_user.id
        admin_preferences.theme_mode = "dark"
        admin_preferences.language = "zh-CN"
        admin_preferences.timezone = "Asia/Shanghai"
        admin_preferences.email_notifications = True
        admin_preferences.push_notifications = False
        db.add(admin_preferences)
        db.commit()

        # 记录管理员创建活动
        log_user_activity(
            admin_user, "admin_account_created", "默认管理员账号初始化", request, db
        )

        return ApiResponse(
            success=True,
            message="默认管理员账号创建成功",
            data={
                "username": admin_username,
                "email": admin_email,
                "password": admin_password,  # 仅在开发环境返回
                "note": "请立即修改默认密码",
            },
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建管理员账号失败: {e!s}",
        ) from None


@router.get("/users", response_model=PaginatedResponse)
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户列表(分页)"""
    query = db.query(User)

    # 搜索过滤
    if search:
        search_criterion = cast(
            "Any",
            (
                cast("Any", User.username).contains(search)
                | cast("Any", User.email).contains(search)
                | cast("Any", User.full_name).contains(search)
            ),
        )
        query = query.filter(search_criterion)

    # 状态过滤
    if is_active is not None:
        active_criterion = cast("Any", (User.is_active == is_active))
        query = query.filter(active_criterion)

    # 计算总数
    total = query.count()
    # 分页
    users = (
        query.order_by(cast("Any", User.created_at).desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    # 转换为响应格式
    user_data: list[dict] = []
    for user in users:
        user_dict = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "created_at": (
                user.created_at.isoformat()
                if hasattr(user, "created_at") and user.created_at
                else None
            ),
            "last_login_at": (
                user.last_login_at.isoformat()
                if hasattr(user, "last_login_at") and user.last_login_at
                else None
            ),
        }
        user_data.append(user_dict)

    return PaginatedResponse(
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
        items=user_data,
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户详情"""
    user = db.query(User).filter(cast("Any", (User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.from_orm(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新用户信息"""
    user = db.query(User).filter(cast("Any", (User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新用户信息
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    # 更新时间戳
    if hasattr(user, "updated_at"):
        user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    log_user_activity(
        _,
        "admin_user_updated",
        f"更新用户 {user.username} 信息: {update_data}",
        request,
        db,
    )

    return UserResponse.from_orm(user)


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: int,
    request: Request,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """软删除用户(设置为不活跃)"""
    user = db.query(User).filter(cast("Any", (User.id == user_id))).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.is_active = False
    db.commit()

    log_user_activity(user, "user_deleted", f"用户 {user_id} 被软删除", request, db)

    return ApiResponse(success=True, message="用户已软删除")


@router.get("/users/{user_id}/sessions", response_model=list[UserSessionResponse])
async def get_user_sessions(
    user_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户会话列表"""
    sessions = (
        db.query(UserSession)
        .filter(cast("Any", (UserSession.user_id == user_id)))
        .order_by(cast("Any", UserSession.created_at).desc())
        .all()
    )

    return [UserSessionResponse.from_orm(s) for s in sessions]


@router.delete("/users/{user_id}/sessions/{session_id}", response_model=ApiResponse)
async def revoke_user_session(
    user_id: int,
    session_id: int,
    request: Request,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """撤销用户会话"""
    session = (
        db.query(UserSession)
        .filter(
            cast("Any", (UserSession.user_id == user_id))
            & cast("Any", (UserSession.id == session_id))
        )
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在或已失效")

    session.is_active = False
    db.commit()

    log_user_activity(
        _, "session_revoked", f"撤销用户 {user_id} 会话 {session_id}", request, db
    )

    return ApiResponse(success=True, message="会话已撤销")


@router.get("/users/{user_id}/activities", response_model=PaginatedResponse)
async def get_user_activities(
    user_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户活动日志"""
    query = db.query(UserActivityLog).filter(
        cast("Any", (UserActivityLog.user_id == user_id))
    )

    total = query.count()
    activities = (
        query.order_by(cast("Any", UserActivityLog.created_at).desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    activity_data: list[dict] = []
    for activity in activities:
        activity_dict = {
            "id": activity.id,
            "action": activity.action,
            "details": activity.details,
            "ip_address": activity.ip_address,
            "user_agent": activity.user_agent,
            "created_at": (
                activity.created_at.isoformat()
                if hasattr(activity, "created_at") and activity.created_at
                else None
            ),
        }
        activity_data.append(activity_dict)

    return PaginatedResponse(
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
        items=activity_data,
    )


@router.get("/stats", response_model=dict)
async def get_admin_stats(
    _: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """获取管理员统计信息"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(cast("Any", User.is_active)).count()
    total_roles = db.query(UserRole).count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_roles": total_roles,
    }
