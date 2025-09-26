from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# 新增：测试环境检测
import os


def _is_test_environment() -> bool:
    """判断是否处于测试环境。
    优先检查 PyTest 的环境变量，其次检查自定义 UNIT_TEST，最后检查配置中的 ENVIRONMENT。
    """
    try:
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        if os.environ.get("UNIT_TEST") == "1":
            return True
        if getattr(settings, "ENVIRONMENT", "production") == "test":
            return True
    except Exception:
        # 安全兜底，任何异常都视为非测试环境
        return False
    return False


# 新增：统一的引擎创建函数，按数据库类型配置连接池与安全参数
def create_configured_engine(url: str):
    # SQLite 场景：避免使用 QueuePool，开启跨线程访问（开发/测试友好）
    if url.startswith("sqlite://"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )

    # 非 SQLite（例如 PostgreSQL/MySQL）：统一连接池参数与 pool_pre_ping
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )


# 使用统一函数创建全局引擎
engine = create_configured_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 测试环境下改用轻量 SQLite，避免依赖外部数据库
if _is_test_environment():
    test_engine = create_configured_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
