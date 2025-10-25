from __future__ import annotations

import ipaddress
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from ..infrastructure.database.models import (
    User,
    UserActivityLog,
    UserRole,
    UserRoleAssignment,
)
from ..infrastructure.database.session import get_db
from ..services.auth_service import auth_service

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    def raise_exc() -> None:
        raise credentials_exception

    user_id: int | None = None
    payload: dict[str, Any] | None = None

    try:
        payload = auth_service.verify_token(credentials.credentials)
        if payload is None:
            raise_exc()

        assert payload is not None
        sub = payload.get("sub")
        user_id = int(sub) if sub is not None else None
        if user_id is None:
            raise_exc()

    except Exception:
        raise_exc()

    user = db.query(User).filter_by(id=user_id).first()
    if user is None or not user.is_active:
        raise_exc()

    assert user is not None
    return user


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """获取当前用户（可选，不抛出异常）"""
    if not credentials:
        return None

    try:
        payload = auth_service.verify_token(credentials.credentials)
        if payload is None:
            return None

        sub = payload.get("sub")
        user_id = int(sub) if sub is not None else None
        if user_id is None:
            return None

    except Exception:
        return None

    user = db.query(User).filter_by(id=user_id).first()
    if user is None or not user.is_active:
        return None

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """获取当前活跃用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="用户账号已被禁用"
        )
    return current_user


def require_roles(required_roles: list[str]):
    """角色权限装饰器"""

    def role_checker(
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db),
    ):
        user_roles = (
            db.query(UserRole)
            .join(UserRoleAssignment)
            .filter_by(user_id=current_user.id)
            .all()
        )

        user_role_names = [role.name for role in user_roles]

        if not any(role in user_role_names for role in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="权限不足"
            )

        return current_user

    return role_checker


def require_admin(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """需要管理员权限"""
    return require_roles(["admin"])(current_user, db)


def require_moderator(
    current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)
):
    """需要版主权限"""
    return require_roles(["admin", "moderator"])(current_user, db)


class RateLimiter:
    """API限流器"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}  # 在生产环境中应使用Redis

    def is_allowed(self, key: str) -> bool:
        """检查是否允许请求"""
        now = datetime.utcnow().timestamp()

        if key not in self.requests:
            self.requests[key] = []

        # 清理过期请求
        self.requests[key] = [
            req_time
            for req_time in self.requests[key]
            if now - req_time < self.window_seconds
        ]

        # 检查是否超过限制
        if len(self.requests[key]) >= self.max_requests:
            return False

        # 记录当前请求
        self.requests[key].append(now)
        return True


# 全局限流器实例
rate_limiter = RateLimiter()


def check_rate_limit(request: Request):
    """检查请求频率限制"""
    client_ip = request.client.host if request.client else None

    if client_ip and not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁, 请稍后再试",
        )


def log_user_activity(
    user: User | None,
    action: str,
    details: str | None = None,
    request: Request | None = None,
    db: Session | None = None,
):
    """记录用户活动"""
    if db is None:
        return

    ip_address = "unknown"
    user_agent = "unknown"

    if request:
        ip_address = (
            request.client.host
            if request.client and hasattr(request.client, "host")
            else "unknown"
        )
        user_agent = request.headers.get("user-agent", "unknown")

    activity_log = UserActivityLog()
    activity_log.user_id = user.id if user else None
    activity_log.action = action
    activity_log.details = details
    activity_log.ip_address = ip_address
    activity_log.user_agent = user_agent

    db.add(activity_log)
    db.commit()


def validate_ip_whitelist(request: Request, whitelist: list[str] | None = None):
    """验证IP白名单"""
    if not whitelist:
        return True

    client_ip = (
        request.client.host
        if request.client and hasattr(request.client, "host")
        else None
    )
    if not client_ip:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无法确定IP地址"
        )

    try:
        client_addr = ipaddress.ip_address(client_ip)
        for allowed_ip in whitelist:
            if "/" in allowed_ip:  # CIDR notation
                if client_addr in ipaddress.ip_network(allowed_ip):
                    return True
            elif client_addr == ipaddress.ip_address(allowed_ip):
                return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="IP地址不在允许列表中"
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的IP地址"
        ) from None


def check_user_permissions(
    user: User, _resource: str, _action: str, db: Session
) -> bool:
    """检查用户权限"""
    # 管理员拥有所有权限
    admin_role = db.query(UserRole).filter_by(name="admin").first()
    if admin_role:
        user_admin = (
            db.query(UserRoleAssignment)
            .filter_by(
                user_id=user.id,
                role_id=admin_role.id,
            )
            .first()
        )
        if user_admin:
            return True

    # 这里可以扩展更复杂的权限检查逻辑
    # 例如基于资源和操作的细粒度权限控制

    return False


class SecurityHeaders:
    """安全头部中间件"""

    @staticmethod
    def add_security_headers(response):
        """添加安全头部"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
