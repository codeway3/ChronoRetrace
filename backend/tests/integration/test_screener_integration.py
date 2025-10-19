"""
Integration tests for the screener service.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.infrastructure.database.models import DailyStockMetrics, StockInfo
from app.schemas.screener import ScreenerCondition, ScreenerRequest


@pytest.fixture(scope="function")
def stock_data(test_session: Session):
    """
    Populate the database with mock stock data for testing.
    """
    from app.infrastructure.database.models import StockInfo, DailyStockMetrics
    from datetime import date

    # Clear existing data
    test_session.query(StockInfo).delete()
    test_session.query(DailyStockMetrics).delete()
    test_session.commit()

    # Create mock data
    stocks = [
        StockInfo(ts_code="000001.SZ", name="平安银行", market_type="szse"),
        StockInfo(ts_code="600519.SH", name="贵州茅台", market_type="sse"),
    ]
    metrics = [
        DailyStockMetrics(
            code="000001.SZ",
            date=date(2023, 1, 1),
            market="szse",
            pe_ratio=10.0,
            market_cap=100_000_000,
        ),
        DailyStockMetrics(
            code="600519.SH",
            date=date(2023, 1, 1),
            market="sse",
            pe_ratio=30.0,
            market_cap=2_000_000_000,
        ),
    ]
    test_session.add_all(stocks)
    test_session.add_all(metrics)
    test_session.commit()
    yield
    test_session.rollback()


def test_screen_stocks_pe_ratio(client: TestClient, stock_data: None):
    """Test screening stocks by PE ratio."""
    request = ScreenerRequest(
        asset_type="A_share",
        conditions=[ScreenerCondition(field="pe_ratio", operator="le", value=20)],
        sort_by="pe_ratio",
        sort_order="asc",
        page=1,
        size=10,
    )
    response = client.post("/api/v1/screener/", json=request.model_dump())
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["items"][0]["symbol"] == "000001.SZ"


def test_screen_stocks_market_cap(client: TestClient, stock_data: None):
    """Test screening stocks by market capitalization."""
    request = ScreenerRequest(
        asset_type="A_share",
        conditions=[
            ScreenerCondition(field="market_cap", operator="ge", value=1_000_000_000)
        ],
        sort_by="market_cap",
        sort_order="desc",
        page=1,
        size=10,
    )
    response = client.post("/api/v1/screener/", json=request.model_dump())
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 1
    assert result["items"][0]["symbol"] == "600519.SH"


def test_screen_stocks_no_results(client: TestClient, stock_data: None):
    """Test a screening that returns no results."""
    request = ScreenerRequest(
        asset_type="A_share",
        conditions=[ScreenerCondition(field="pe_ratio", operator="ge", value=100)],
        sort_by="pe_ratio",
        sort_order="asc",
        page=1,
        size=10,
    )
    response = client.post("/api/v1/screener/", json=request.model_dump())
    assert response.status_code == 200
    result = response.json()
    assert result["total"] == 0
    assert len(result["items"]) == 0
