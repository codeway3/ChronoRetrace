"""创建用户认证相关数据表

迁移版本: 001
创建时间: 2024-01-15
描述: 创建用户、角色、会话、活动日志等认证相关表
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def upgrade(engine):
    """执行数据库升级"""
    # 创建所有表
    Base.metadata.create_all(bind=engine)

    print("✅ 用户认证相关数据表创建完成")


def downgrade(engine):
    """执行数据库降级"""
    # 删除所有表（谨慎操作）
    Base.metadata.drop_all(bind=engine)

    print("⚠️ 用户认证相关数据表已删除")


# 用户角色表
class UserRole(Base):
    __tablename__ = "user_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(200))
    permissions = Column(Text)  # JSON格式存储权限
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_user_roles_name", "name"),)


# 用户表
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    birth_date = Column(DateTime, nullable=True)
    gender = Column(String(10), nullable=True)
    profession = Column(String(100), nullable=True)
    investment_experience = Column(String(20), default="beginner")

    # 账户状态
    is_active = Column(Boolean, default=True, index=True)
    is_locked = Column(Boolean, default=False, index=True)
    vip_level = Column(Integer, default=0, index=True)
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)

    # 安全相关
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime, nullable=True)
    email_verification_token = Column(String(255), nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_users_username", "username"),
        Index("idx_users_email", "email"),
        Index("idx_users_active", "is_active"),
        Index("idx_users_email_verified", "email_verified"),
        Index("idx_users_created_at", "created_at"),
    )


# 用户角色分配表
class UserRoleAssignment(Base):
    __tablename__ = "user_role_assignments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role_id = Column(
        Integer, ForeignKey("user_roles.id", ondelete="CASCADE"), nullable=False
    )
    assigned_at = Column(DateTime, default=func.now(), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"))

    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        Index("idx_user_role_assignments_user", "user_id"),
        Index("idx_user_role_assignments_role", "role_id"),
    )


# 用户会话表
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    refresh_token = Column(String(255), unique=True, nullable=True, index=True)
    device_info = Column(Text)  # JSON格式存储设备信息
    ip_address = Column(String(45))  # 支持IPv6
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_user_sessions_user", "user_id"),
        Index("idx_user_sessions_token", "session_token"),
        Index("idx_user_sessions_active", "is_active"),
        Index("idx_user_sessions_expires", "expires_at"),
    )


# 用户活动日志表
class UserActivityLog(Base):
    __tablename__ = "user_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(200))  # 操作的资源
    details = Column(Text)  # JSON格式存储详细信息
    ip_address = Column(String(45))
    user_agent = Column(Text)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_user_activity_logs_user", "user_id"),
        Index("idx_user_activity_logs_action", "action"),
        Index("idx_user_activity_logs_created", "created_at"),
        Index("idx_user_activity_logs_success", "success"),
    )


# 用户设置表
class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    theme_mode = Column(String(20), default="light")
    language = Column(String(10), default="zh-CN")
    timezone = Column(String(50), default="Asia/Shanghai")
    notification_email = Column(Boolean, default=True)
    notification_sms = Column(Boolean, default=False)
    notification_push = Column(Boolean, default=True)
    privacy_level = Column(String(20), default="normal")
    data_retention_days = Column(Integer, default=365)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_user_settings_user", "user_id"),)


# 用户验证码表
class UserVerificationCode(Base):
    __tablename__ = "user_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    email = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    code = Column(String(10), nullable=False)
    code_type = Column(
        String(20), nullable=False, index=True
    )  # email_verify, phone_verify, password_reset, login_2fa
    is_used = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_user_verification_codes_user", "user_id"),
        Index("idx_user_verification_codes_email", "email"),
        Index("idx_user_verification_codes_phone", "phone"),
        Index("idx_user_verification_codes_type", "code_type"),
        Index("idx_user_verification_codes_expires", "expires_at"),
    )


# 用户登录历史表
class UserLoginHistory(Base):
    __tablename__ = "user_login_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    login_method = Column(String(20), nullable=False)  # password, sms, email, oauth
    ip_address = Column(String(45))
    user_agent = Column(Text)
    device_info = Column(Text)  # JSON格式存储设备信息
    location = Column(String(200))  # 登录地点
    success = Column(Boolean, default=True, nullable=False)
    failure_reason = Column(String(200))
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)

    __table_args__ = (
        Index("idx_user_login_history_user", "user_id"),
        Index("idx_user_login_history_method", "login_method"),
        Index("idx_user_login_history_success", "success"),
        Index("idx_user_login_history_created", "created_at"),
    )


# 用户偏好设置表
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    theme_mode = Column(String(20), default="light")
    language = Column(String(10), default="zh-CN")
    timezone = Column(String(50), default="Asia/Shanghai")
    notification_email = Column(Boolean, default=True)
    notification_sms = Column(Boolean, default=False)
    notification_push = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_user_preferences_user", "user_id"),)


# 用户关注列表表
class UserWatchlist(Base):
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (Index("idx_user_watchlists_user", "user_id"),)


# 关注列表股票表
class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(
        Integer, ForeignKey("user_watchlists.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String(20), nullable=False, index=True)
    market = Column(String(10), nullable=False)
    added_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_watchlist_stocks_watchlist", "watchlist_id"),
        Index("idx_watchlist_stocks_symbol", "symbol"),
    )
