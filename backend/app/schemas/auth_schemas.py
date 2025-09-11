from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..core.config import settings


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str | None = Field(None, max_length=100)
    is_active: bool = True


class UserCreate(UserBase):
    """用户创建模型"""
    password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('密码确认不匹配')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f'密码长度至少{settings.PASSWORD_MIN_LENGTH}位')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class UserUpdate(BaseModel):
    """用户更新模型"""
    full_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str  # 可以是用户名或邮箱
    password: str
    remember_me: bool = False


class Token(BaseModel):
    """令牌响应模型"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # 秒数


class TokenRefresh(BaseModel):
    """令牌刷新模型"""
    refresh_token: str


class PasswordChange(BaseModel):
    """密码修改模型"""
    current_password: str
    new_password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('密码确认不匹配')
        return v

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f'密码长度至少{settings.PASSWORD_MIN_LENGTH}位')
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v


class PasswordReset(BaseModel):
    """密码重置模型"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""
    token: str
    new_password: str = Field(..., min_length=settings.PASSWORD_MIN_LENGTH)
    confirm_password: str

    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('密码确认不匹配')
        return v


class UserPreferencesBase(BaseModel):
    """用户偏好设置基础模型"""
    theme_mode: str = "light"  # light, dark, auto
    language: str = "zh-CN"  # zh-CN, en-US
    timezone: str = "Asia/Shanghai"
    email_notifications: bool = True
    push_notifications: bool = True


class UserPreferencesCreate(UserPreferencesBase):
    """用户偏好设置创建模型"""
    pass


class UserPreferencesUpdate(BaseModel):
    """用户偏好设置更新模型"""
    theme_mode: str | None = None
    language: str | None = None
    timezone: str | None = None
    email_notifications: bool | None = None
    push_notifications: bool | None = None


class UserPreferencesResponse(UserPreferencesBase):
    """用户偏好设置响应模型"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserSessionResponse(BaseModel):
    """用户会话响应模型"""
    id: int
    ip_address: str
    user_agent: str
    created_at: datetime
    last_activity: datetime | None = None
    expires_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserActivityLogResponse(BaseModel):
    """用户活动日志响应模型"""
    id: int
    action: str
    details: str | None = None
    ip_address: str
    user_agent: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel):
    """通用API响应模型"""
    success: bool
    message: str
    data: dict | None = None


class PaginatedResponse(BaseModel):
    """分页响应模型"""
    items: list[dict]
    total: int
    page: int
    size: int
    pages: int
