from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from ..core.config import settings
from ..infrastructure.database.models import User, UserSession


class AuthService:
    """用户认证服务类"""

    def __init__(self):
        # 密码加密上下文 - 修复bcrypt版本兼容性问题
        try:
            self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        except Exception:
            # 如果bcrypt有版本兼容性问题，使用更兼容的配置
            self.pwd_context = CryptContext(
                schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12
            )

        # JWT配置
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.REFRESH_TOKEN_EXPIRE_DAYS

    def hash_password(self, password: str) -> str:
        """加密密码"""
        return self.pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.access_token_expire_minutes
            )

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid.uuid4())})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(
        self,
        token: str,
        token_type: str = "access",  # nosec B107
    ) -> dict[str, Any] | None:
        """验证令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != token_type:
                return None
            return payload
        except JWTError:
            return None

    def authenticate_user(
        self, db: Session, username: str, password: str
    ) -> User | None:
        """用户认证"""
        user = (
            db.query(User)
            .filter((User.username == username) | (User.email == username))
            .first()
        )

        if not user or not user.is_active:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        return user

    def create_user_session(
        self,
        db: Session,
        user_id: int,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
    ) -> UserSession:
        """创建用户会话"""
        # 删除用户的旧会话（可选：限制同时登录数量）
        db.query(UserSession).filter(
            UserSession.user_id == user_id, UserSession.is_active
        ).update({"is_active": False})

        session = UserSession(
            user_id=user_id,
            session_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.utcnow()
            + timedelta(days=self.refresh_token_expire_days),
            is_active=True,
        )

        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def invalidate_session(self, db: Session, refresh_token: str) -> bool:
        """使会话失效"""
        session = (
            db.query(UserSession)
            .filter(UserSession.session_token == refresh_token, UserSession.is_active)
            .first()
        )

        if session:
            session.is_active = False
            db.commit()
            return True
        return False

    def validate_session(self, db: Session, refresh_token: str) -> UserSession | None:
        """验证会话"""
        session = (
            db.query(UserSession)
            .filter(
                UserSession.session_token == refresh_token,
                UserSession.is_active,
                UserSession.expires_at > datetime.utcnow(),
            )
            .first()
        )

        return session

    def generate_reset_token(self) -> str:
        """生成密码重置令牌"""
        return secrets.token_urlsafe(32)

    def create_password_reset_token(self, user_id: int) -> str:
        """创建密码重置令牌"""
        data = {
            "user_id": user_id,
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1),  # 1小时有效期
        }
        return jwt.encode(data, self.secret_key, algorithm=self.algorithm)

    def verify_password_reset_token(self, token: str) -> int | None:
        """验证密码重置令牌"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "password_reset":
                return None
            return payload.get("user_id")
        except JWTError:
            return None


# 全局认证服务实例
auth_service = AuthService()
