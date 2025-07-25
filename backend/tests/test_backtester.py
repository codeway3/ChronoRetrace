import pytest
import pandas as pd
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Make sure the app's root is in the Python path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.db.session import get_db
from app.schemas.backtest import GridStrategyConfig
from app.services import backtester

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Mock Dependencies ---
# Override the get_db dependency to use the test database
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
    """Creates a mock DataFrame of stock data for testing, now including open, high, low."""
    data = {
        'trade_date': pd.to_datetime([
            '2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', 
            '2023-01-05', '2023-01-06', '2023-01-07', '2023-01-08'
        ]),
        'open': [10.0, 10.0, 9.8, 9.5, 10.2, 10.6, 11.1, 10.8],
        'high': [10.1, 10.0, 9.6, 10.3, 10.7, 11.2, 11.0, 11.6],
        'low':  [9.9,  9.8,  9.4, 9.8,  10.1, 10.5, 10.7, 11.2],
        'close':[10.0, 9.8,  9.5, 10.2, 10.6, 11.1, 10.8, 11.5]
    }
    return pd.DataFrame(data)

# --- Unit Test for the Service Layer ---
def test_run_grid_backtest_logic(mocker, mock_stock_data):
    """
    Tests the core logic of the run_grid_backtest function with A-share lot rules.
    """
    mocker.patch('app.services.data_fetcher.fetch_stock_data', return_value=mock_stock_data)
    
    config = GridStrategyConfig(
        stock_code="TEST.SH",
        start_date=date(2023, 1, 1),
        end_date=date(2023, 1, 8),
        upper_price=11.0,
        lower_price=10.0,
        grid_count=2, # Grids: [10.0, 10.5], [10.5, 11.0]
        total_investment=20000.0 # Increased investment to afford lots
    )
    
    db_session = next(override_get_db())
    result = backtester.run_grid_backtest(db=db_session, config=config)
    
    # --- Assertions based on the final, correct, A-share rules walkthrough ---
    assert result is not None
    assert result.trade_count == 4

    # --- Manual Walkthrough Verification ---
    # Investment: 20000, Cash per grid: 10000
    # Grid 0: buy <= 10.0, sell >= 10.5
    # Grid 1: buy <= 10.5, sell >= 11.0

    # Day 1 (low 9.9): BUY grid 0. 10000/10.0 = 1000 shares (10 lots). Cost=10000.
    assert result.transaction_log[0].trade_type == "buy"
    assert result.transaction_log[0].price == 10.0
    assert result.transaction_log[0].quantity == 1000
    assert result.transaction_log[0].trade_date == date(2023, 1, 1)

    # Day 2 (low 9.8): BUY grid 1. 10000/10.5 = 952 shares -> 900 shares (9 lots). Cost=9450.
    assert result.transaction_log[1].trade_type == "buy"
    assert result.transaction_log[1].price == 10.5
    assert result.transaction_log[1].quantity == 900
    assert result.transaction_log[1].trade_date == date(2023, 1, 2)

    # Day 5 (high 10.7): SELL grid 0. Sell 1000 shares. Revenue=1000*10.5=10500.
    assert result.transaction_log[2].trade_type == "sell"
    assert result.transaction_log[2].price == 10.5
    assert result.transaction_log[2].quantity == 1000
    assert result.transaction_log[2].trade_date == date(2023, 1, 5)

    # Day 6 (high 11.2): SELL grid 1. Sell 900 shares. Revenue=900*11.0=9900.
    assert result.transaction_log[3].trade_type == "sell"
    assert result.transaction_log[3].price == 11.0
    assert result.transaction_log[3].quantity == 900
    assert result.transaction_log[3].trade_date == date(2023, 1, 6)

    # --- PnL Calculation ---
    # PnL Grid 0: 10500 (revenue) - 10000 (cost) = 500
    # PnL Grid 1: 9900 (revenue) - 9450 (cost) = 450
    # Total PnL = 500 + 450 = 950
    assert round(result.total_pnl, 2) == 950.0

# --- Integration Test for the API Endpoint ---
def test_grid_backtest_api_endpoint(mocker, mock_stock_data):
    """
    Tests the /api/v1/backtest/grid API endpoint with A-share lot rules.
    """
    mocker.patch('app.services.data_fetcher.fetch_stock_data', return_value=mock_stock_data)
    
    request_payload = {
        "stock_code": "API.TEST",
        "start_date": "2023-01-01",
        "end_date": "2023-01-08",
        "upper_price": 11.0,
        "lower_price": 10.0,
        "grid_count": 2,
        "total_investment": 20000.0
    }
    
    response = client.post("/api/v1/backtest/grid", json=request_payload)
    
    assert response.status_code == 200
    result_json = response.json()
    assert result_json is not None
    assert result_json["trade_count"] == 4
    assert round(result_json["total_pnl"], 2) == 950.0

def test_backtest_api_no_data_error(mocker):
    """
    Tests that the API returns a 400 error if no data is available.
    """
    # Mock the data fetcher to return an empty DataFrame
    mocker.patch('app.services.data_fetcher.fetch_stock_data', return_value=pd.DataFrame())
    
    request_payload = {
        "stock_code": "NO.DATA",
        "start_date": "2023-01-01",
        "end_date": "2023-01-08",
        "upper_price": 11.0,
        "lower_price": 10.0,
        "grid_count": 2,
        "total_investment": 1000.0
    }
    
    response = client.post("/api/v1/backtest/grid", json=request_payload)
    
    assert response.status_code == 400
    assert "Could not fetch historical data" in response.json()["detail"]
