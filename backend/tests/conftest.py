#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pytest 配置文件
包含通用的测试工具和 fixture
"""

import asyncio
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.models import Base


def pytest_configure(config):
    """
    注册自定义标记，避免警告
    """
    config.addinivalue_line("markers", "asyncio: mark test as an asyncio coroutine")


def pytest_pyfunc_call(pyfuncitem):
    """
    Minimal async test runner hook to support @pytest.mark.asyncio tests
    when pytest-asyncio is not installed. Uses the provided event_loop fixture
    if available, otherwise creates a new loop.
    """
    import asyncio as _asyncio
    import inspect

    if inspect.iscoroutinefunction(pyfuncitem.obj):
        loop = pyfuncitem.funcargs.get("event_loop")
        if loop is None:
            loop = _asyncio.get_event_loop_policy().new_event_loop()
            try:
                _asyncio.set_event_loop(loop)
                loop.run_until_complete(pyfuncitem.obj(**pyfuncitem.funcargs))
            finally:
                loop.close()
                _asyncio.set_event_loop(None)
        else:
            loop.run_until_complete(pyfuncitem.obj(**pyfuncitem.funcargs))
        return True


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
