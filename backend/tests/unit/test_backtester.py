import os

# Make sure the app's root is in the Python path
import sys
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.infrastructure.database.session import get_db
from app.main import app
from app.schemas.backtest import GridStrategyConfig
from app.analytics.backtest import backtester

# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# --- Mock Dependencies ---
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# --- Test Client ---
client = TestClient(app)


# --- Mock Data ---
@pytest.fixture
def mock_stock_data():
    """Creates a mock DataFrame of stock data for testing."""
    data = {
        "trade_date": pd.to_datetime(
            [
                "2023-01-01",
                "2023-01-02",
                "2023-01-03",
                "2023-01-04",
                "2023-01-05",
                "2023-01-06",
                "2023-01-07",
                "2023-01-08",
            ]
        ),
        "open": [10.0, 10.0, 9.8, 9.5, 10.2, 10.6, 11.1, 10.8],
        "high": [10.1, 10.0, 9.6, 10.3, 10.7, 11.2, 11.0, 11.6],
        "low": [9.9, 9.8, 9.4, 9.8, 10.1, 10.5, 10.7, 11.2],
        "close": [10.0, 9.8, 9.5, 10.2, 10.6, 11.1, 10.8, 11.5],
        "vol": [10000] * 8,
    }
    return pd.DataFrame(data)


# --- Unit Test for the Service Layer (No Costs) ---
def test_run_grid_backtest_logic_no_costs(mocker, mock_stock_data):
    """
    Tests the core logic without transaction costs. The logic should allow
    a grid to be reused after a sell.
    """
    mocker.patch(
        "app.data.managers.data_manager.fetch_stock_data", return_value=mock_stock_data
    )

    config = GridStrategyConfig(
        stock_code="TEST.SH",
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 8),
        upper_price=11.0,
        lower_price=10.0,
        grid_count=2,  # Grids: [10.0, 10.5], [10.5, 11.0]
        total_investment=20000.0,
        commission_rate=0,
        min_commission=0,
        stamp_duty_rate=0,
    )

    db_session = next(override_get_db())
    result = backtester.run_grid_backtest(db=db_session, config=config)

    # Walkthrough:
    # Day 1: Buy Grid 0 (1000 shares @ 10.0). Cash: 10000, Pos: 1000
    # Day 2: Buy Grid 1 (900 shares @ 10.5). Cash: 550, Pos: 1900
    # Day 5: Sell Grid 0 (1000 shares @ 10.5). Cash: 11050, Pos: 900. Grid 0 is now open.
    # Day 6: Sell Grid 1 (900 shares @ 11.0). Cash: 20950, Pos: 0. Grid 1 is now open.
    assert result.trade_count == 4
    assert round(result.total_pnl, 2) == 950.0


# --- Integration Test for the API Endpoint ---
def test_grid_backtest_api_endpoint(mocker, mock_stock_data):
    """Tests the API endpoint, expecting the same logic as the unit test."""
    mocker.patch(
        "app.data.managers.data_manager.fetch_stock_data", return_value=mock_stock_data
    )

    request_payload = {
        "stock_code": "API.TEST.SH",
        "start_date": "2023-01-01",
        "end_date": "2023-01-08",
        "upper_price": 11.0,
        "lower_price": 10.0,
        "grid_count": 2,
        "total_investment": 20000.0,
        "commission_rate": 0,
        "min_commission": 0,
        "stamp_duty_rate": 0,
    }

    response = client.post("/api/v1/backtest/grid", json=request_payload)

    assert response.status_code == 200
    result_json = response.json()
    assert result_json["trade_count"] == 4
    assert round(result_json["total_pnl"], 2) == 950.0


# --- Unit Test for Transaction Costs ---
def test_run_grid_backtest_with_transaction_costs(mocker, mock_stock_data):
    """
    Tests the backtest logic with commission and stamp duty, ensuring
    the cash per grid is sufficient for the trade.
    """
    mocker.patch(
        "app.data.managers.data_manager.fetch_stock_data", return_value=mock_stock_data
    )

    config = GridStrategyConfig(
        stock_code="COST.TEST.SH",
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 8),
        upper_price=11.0,
        lower_price=10.0,
        grid_count=1,
        total_investment=20000.0,  # Cash per grid is 20000
        commission_rate=0.001,  # 0.1%
        min_commission=5.0,
        stamp_duty_rate=0.001,  # 0.1%
    )

    db_session = next(override_get_db())
    result = backtester.run_grid_backtest(db=db_session, config=config)

    # --- Manual Calculation Verification ---
    # 1. BUY on Day 1 (low 9.9, triggers at 10.0)
    #    - Potential shares: 20000 / 10.0 = 2000. A-share lots -> 2000 shares.
    #    - Gross cost: 2000 * 10.0 = 20000.0
    #    - Commission: max(20000 * 0.001, 5.0) = max(20.0, 5.0) = 20.0
    #    - Total cost for buy: 20000.0 + 20.0 = 20020.0
    #    - This buy FAILS because total_cost (20020) > cash_per_grid (20000).
    #    - The logic will then try with one less lot: 1900 shares.
    #    - Gross cost: 1900 * 10.0 = 19000.0
    #    - Commission: max(19000 * 0.001, 5.0) = max(19.0, 5.0) = 19.0
    #    - Total cost for buy: 19000.0 + 19.0 = 19019.0. This is < 20000. SUCCESS.
    #    - This is the grid's `cost_basis`.

    # 2. SELL on Day 6 (high 11.2, triggers at 11.0)
    #    - Shares to sell: 1900
    #    - Gross revenue: 1900 * 11.0 = 20900.0
    #    - Commission: max(20900 * 0.001, 5.0) = max(20.9, 5.0) = 20.9
    #    - Stamp duty: 20900 * 0.001 = 20.9
    #    - Total fees: 20.9 + 20.9 = 41.8
    #    - Net revenue: 20900.0 - 41.8 = 20858.2

    # 3. PnL Calculation
    #    - Grid PnL: net_revenue - grid_cost_basis = 20858.2 - 19019.0 = 1839.2
    #    - Total PnL: final_cash - initial_cash.
    #      - Initial cash = 20000
    #      - Cash after buy = 20000 - 19019.0 = 981.0
    #      - Cash after sell = 981.0 + 20858.2 = 21839.2
    #      - Final PnL = 21839.2 - 20000 = 1839.2

    assert result is not None
    assert result.trade_count == 2
    assert result.total_pnl is not None and round(result.total_pnl, 2) == 1839.20
    assert result.transaction_log[1].pnl is not None and round(result.transaction_log[1].pnl, 2) == 1839.20
    assert result.final_holding_quantity == 0


# --- Error Handling Tests ---
def test_backtest_api_no_data_error(mocker):
    """Tests that the API returns a 400 error if no data is available."""
    mocker.patch(
        "app.data.managers.data_manager.fetch_stock_data", return_value=pd.DataFrame()
    )
    request_payload = {
        "stock_code": "NO.DATA",
        "start_date": "2023-01-01",
        "end_date": "2023-01-08",
        "upper_price": 11.0,
        "lower_price": 10.0,
        "grid_count": 2,
        "total_investment": 1000.0,
    }
    response = client.post("/api/v1/backtest/grid", json=request_payload)
    assert response.status_code == 400
    assert "Could not fetch historical data" in response.json()["detail"]


def test_backtest_api_no_data_in_range_error(mocker, mock_stock_data):
    """Tests that the API returns a 400 error if data exists but not in the specified range."""
    mocker.patch(
        "app.data.managers.data_manager.fetch_stock_data", return_value=mock_stock_data
    )
    request_payload = {
        "stock_code": "OUT.OF.RANGE",
        "start_date": "2024-01-01",
        "end_date": "2024-01-08",
        "upper_price": 11.0,
        "lower_price": 10.0,
        "grid_count": 2,
        "total_investment": 1000.0,
    }
    response = client.post("/api/v1/backtest/grid", json=request_payload)
    assert response.status_code == 400
    assert "No historical data available" in response.json()["detail"]
