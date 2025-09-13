import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from the backend directory
dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
)
load_dotenv(dotenv_path=dotenv_path)


class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = (
        "postgresql://chronoretrace:password@localhost:5432/chronoretrace"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security Settings
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    PASSWORD_HASH_ALGORITHM: str = "bcrypt"
    PASSWORD_MIN_LENGTH: int = 8
    SESSION_EXPIRE_HOURS: int = 24
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # API Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST_SIZE: int = 10
    RATE_LIMIT_ENABLED: bool = True

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"

    # IP Whitelist
    IP_WHITELIST: str = ""
    IP_WHITELIST_ENABLED: bool = False

    # Third-party API Keys
    TUSHARE_API_TOKEN: str = ""
    ALPHAVANTAGE_API_KEY: str = ""

    # Application Settings
    APP_NAME: str = "ChronoRetrace"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Stock Market Analysis Platform"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE_PATH: str = "./logs/app.log"
    LOG_MAX_SIZE_MB: int = 10
    LOG_BACKUP_COUNT: int = 5

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: str = "noreply@chronoretrace.com"

    # File Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: str = "jpg,jpeg,png,pdf,csv,xlsx"

    # Cache Settings
    CACHE_TTL_SECONDS: int = 300
    CACHE_MAX_SIZE: int = 1000
    CACHE_ENABLED: bool = True

    # Monitoring and Analytics
    MONITORING_ENABLED: bool = False
    ANALYTICS_ENABLED: bool = False
    METRICS_ENDPOINT: str = "/metrics"

    # Development Settings
    RELOAD: bool = False
    AUTO_RELOAD: bool = False

    # Computed properties for backward compatibility
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        """Convert CORS_ALLOWED_ORIGINS string to list"""
        return [
            origin.strip()
            for origin in self.CORS_ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def IP_WHITELIST_LIST(self) -> list[str]:
        """Convert IP_WHITELIST string to list"""
        if not self.IP_WHITELIST:
            return []
        return [ip.strip() for ip in self.IP_WHITELIST.split(",") if ip.strip()]

    @property
    def ALLOWED_FILE_TYPES_LIST(self) -> list[str]:
        """Convert ALLOWED_FILE_TYPES string to list"""
        return [
            ext.strip() for ext in self.ALLOWED_FILE_TYPES.split(",") if ext.strip()
        ]

    # Backward compatibility aliases
    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """Backward compatibility for JWT_ACCESS_TOKEN_EXPIRE_MINUTES"""
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    @property
    def REFRESH_TOKEN_EXPIRE_DAYS(self) -> int:
        """Backward compatibility for JWT_REFRESH_TOKEN_EXPIRE_DAYS"""
        return self.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
