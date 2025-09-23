#!/usr/bin/env python3
"""
pytest 配置文件
包含通用的测试工具和 fixture
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.infrastructure.database.session import get_db
from app.infrastructure.database.models import Base

# import akshare as ak  # Removed to avoid initialization issues in tests
# Mock akshare module completely to avoid initialization issues
sys.modules["akshare"] = MagicMock()


@pytest.fixture(scope="session")
def test_engine():
    """创建测试数据库引擎"""
    # 使用内存数据库进行测试
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    yield engine

    # 清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_session(test_engine):
    """创建测试数据库会话"""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_db_session():
    """创建模拟数据库会话"""
    return Mock(spec=Session)


@pytest.fixture
def sample_stock_data():
    """示例股票数据"""
    return [
        {"ts_code": "000001.SZ", "name": "平安银行", "market_type": "A_share"},
        {"ts_code": "000002.SZ", "name": "万科A", "market_type": "A_share"},
        {"ts_code": "600519.SH", "name": "贵州茅台", "market_type": "A_share"},
    ]


@pytest.fixture
def sample_metrics_data():
    """示例指标数据"""
    return {
        "code": "000001.SZ",
        "market": "A_share",
        "date": "2025-08-28",
        "close_price": 12.50,
        "pe_ratio": 15.2,
        "pb_ratio": 1.8,
        "market_cap": 250000000000,
        "dividend_yield": 3.5,
        "ma5": 12.8,
        "ma20": 13.2,
        "volume": 50000000,
    }


@pytest.fixture(scope="session")
def setup_redis_environment():
    """设置Redis环境变量"""
    # 如果在CI环境中，使用环境变量中的Redis配置
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        os.environ["REDIS_HOST"] = os.getenv("REDIS_HOST", "localhost")
        os.environ["REDIS_PORT"] = os.getenv("REDIS_PORT", "6379")
    else:
        # 本地开发环境，使用默认配置
        os.environ.setdefault("REDIS_HOST", "localhost")
        os.environ.setdefault("REDIS_PORT", "6379")


@pytest.fixture
def mock_redis_manager():
    """Mock Redis Manager for unit tests"""
    mock_manager = AsyncMock()
    mock_manager.set.return_value = True
    mock_manager.get.return_value = None
    mock_manager.delete.return_value = True
    mock_manager.exists.return_value = False
    mock_manager.health_check.return_value = True
    return mock_manager


@pytest.fixture
def mock_cache_service():
    """Mock Cache Service for unit tests"""
    mock_service = AsyncMock()
    mock_service.set_stock_info.return_value = True
    mock_service.get_stock_info.return_value = None
    mock_service.health_check.return_value = True
    return mock_service


@pytest.fixture(scope="session", autouse=True)
def setup_fastapi_cache():
    """Initialize FastAPICache for all tests"""
    try:
        from fastapi_cache import FastAPICache
        from fastapi_cache.backends.inmemory import InMemoryBackend

        if not hasattr(FastAPICache, "_prefix") or FastAPICache._prefix is None:
            FastAPICache.init(InMemoryBackend(), prefix="test-cache")
    except Exception:
        pass


@pytest.fixture(scope="session")
def client(test_engine):
    """
    Create a test client for the FastAPI application.
    """

    # Dependency override for database session
    def override_get_db():
        try:
            db = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
async def clear_cache_between_tests():
    """Clear cache between individual tests"""
    from fastapi_cache import FastAPICache

    await FastAPICache.clear()
