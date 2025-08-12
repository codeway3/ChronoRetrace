from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


def test_run_grid_backtest_success():
    """Test successful grid backtest execution."""
    # Create test configuration
    config_data = {
        "stock_code": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "upper_price": 200.0,
        "lower_price": 100.0,
        "grid_count": 5,
        "total_investment": 10000
    }

    # Mock the backtester service
    with patch('app.api.v1.backtest.backtester.run_grid_backtest') as mock_backtest:
        mock_result = {
            "total_pnl": 1500.0,
            "total_return_rate": 0.15,
            "annualized_return_rate": 0.12,
            "max_drawdown": -0.08,
            "win_rate": 0.6,
            "trade_count": 2,
            "chart_data": [
                {"date": "2023-01-01", "portfolio_value": 10000,
                    "benchmark_value": 10000},
                {"date": "2023-12-31", "portfolio_value": 11500,
                    "benchmark_value": 11000}
            ],
            "kline_data": [
                {"trade_date": "2023-01-01", "open": 150.0, "high": 155.0,
                    "low": 148.0, "close": 152.0, "vol": 1000},
                {"trade_date": "2023-12-31", "open": 160.0, "high": 165.0,
                    "low": 158.0, "close": 163.0, "vol": 1200}
            ],
            "transaction_log": [
                {"trade_date": "2023-01-15", "trade_type": "buy",
                    "price": 150.0, "quantity": 10, "pnl": None},
                {"trade_date": "2023-06-20", "trade_type": "sell",
                    "price": 165.0, "quantity": 10, "pnl": 150.0}
            ],
            "strategy_config": {
                "stock_code": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "upper_price": 200.0,
                "lower_price": 100.0,
                "grid_count": 5,
                "total_investment": 10000
            },
            "market_type": "US_stock",
            "final_holding_quantity": 0,
            "average_holding_cost": 0.0
        }
        mock_backtest.return_value = mock_result

        response = client.post("/api/v1/backtest/grid", json=config_data)

        assert response.status_code == 200
        data = response.json()

        # Verify the response contains expected fields
        assert 'total_pnl' in data
        assert 'total_return_rate' in data
        assert 'annualized_return_rate' in data
        assert 'max_drawdown' in data
        assert 'win_rate' in data
        assert 'trade_count' in data
        assert 'chart_data' in data
        assert 'kline_data' in data
        assert 'transaction_log' in data
        assert 'strategy_config' in data
        assert 'market_type' in data
        assert 'final_holding_quantity' in data
        assert 'average_holding_cost' in data

        # Verify the backtester was called with correct parameters
        mock_backtest.assert_called_once()
        call_args = mock_backtest.call_args
        assert call_args[1]['config'].stock_code == "AAPL"


def test_run_grid_backtest_value_error():
    """Test grid backtest with invalid configuration (ValueError)."""
    config_data = {
        "stock_code": "INVALID",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "upper_price": 200.0,
        "lower_price": 100.0,
        "grid_count": 0,  # Invalid grid count
        "total_investment": -1000  # Invalid negative investment
    }

    # Mock the backtester service to raise ValueError
    with patch('app.api.v1.backtest.backtester.run_grid_backtest') as mock_backtest:
        mock_backtest.side_effect = ValueError(
            "Invalid configuration parameters")

        response = client.post("/api/v1/backtest/grid", json=config_data)

        assert response.status_code == 400
        data = response.json()
        assert "Invalid configuration parameters" in data['detail']


def test_run_grid_backtest_unexpected_error():
    """Test grid backtest with unexpected error."""
    config_data = {
        "stock_code": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "upper_price": 200.0,
        "lower_price": 100.0,
        "grid_count": 5,
        "total_investment": 10000
    }

    # Mock the backtester service to raise unexpected error
    with patch('app.api.v1.backtest.backtester.run_grid_backtest') as mock_backtest:
        mock_backtest.side_effect = Exception("Database connection failed")

        response = client.post("/api/v1/backtest/grid", json=config_data)

        assert response.status_code == 500
        data = response.json()
        assert "An internal error occurred during the backtest." in data['detail']


def test_run_grid_backtest_missing_required_fields():
    """Test grid backtest with missing required fields."""
    # Missing required fields
    config_data = {
        "stock_code": "AAPL"
        # Missing other required fields
    }

    response = client.post("/api/v1/backtest/grid", json=config_data)

    # Should return 422 (Unprocessable Entity) due to validation error
    assert response.status_code == 422


def test_run_grid_backtest_invalid_date_format():
    """Test grid backtest with invalid date format."""
    config_data = {
        "stock_code": "AAPL",
        "start_date": "invalid-date",  # Invalid date format
        "end_date": "2023-12-31",
        "initial_capital": 10000,
        "grid_levels": 5,
        "grid_spacing": 0.05
    }

    response = client.post("/api/v1/backtest/grid", json=config_data)

    # Should return 422 (Unprocessable Entity) due to validation error
    assert response.status_code == 422


def test_run_grid_backtest_end_date_before_start_date():
    """Test grid backtest with end date before start date."""
    config_data = {
        "stock_code": "AAPL",
        "start_date": "2023-12-31",
        "end_date": "2023-01-01",  # End date before start date
        "initial_capital": 10000,
        "grid_levels": 5,
        "grid_spacing": 0.05
    }

    response = client.post("/api/v1/backtest/grid", json=config_data)

    # Should return 422 (Unprocessable Entity) due to validation error
    assert response.status_code == 422


def test_run_grid_backtest_invalid_date_range():
    """Test grid backtest with invalid date range (end date before start date)."""
    config_data = {
        "stock_code": "AAPL",
        "start_date": "2023-12-31",  # Start date after end date
        "end_date": "2023-01-01",    # End date before start date
        "upper_price": 200.0,
        "lower_price": 100.0,
        "grid_count": 5,
        "total_investment": 10000
    }

    response = client.post("/api/v1/backtest/grid", json=config_data)

    # Should return 400 (Bad Request) due to business logic error
    assert response.status_code == 400


def test_run_grid_backtest_large_grid_levels():
    """Test grid backtest with very large grid levels."""
    config_data = {
        "stock_code": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "upper_price": 200.0,
        "lower_price": 100.0,
        "grid_count": 1000,  # Very large grid count
        "total_investment": 10000
    }

    # Mock the backtester service to handle large grid levels
    with patch('app.api.v1.backtest.backtester.run_grid_backtest') as mock_backtest:
        mock_result = {
            "total_pnl": 1000.0,
            "total_return_rate": 0.10,
            "annualized_return_rate": 0.08,
            "max_drawdown": -0.05,
            "win_rate": 0.5,
            "trade_count": 0,
            "chart_data": [
                {"date": "2023-01-01", "portfolio_value": 10000,
                    "benchmark_value": 10000},
                {"date": "2023-12-31", "portfolio_value": 11000,
                    "benchmark_value": 10800}
            ],
            "kline_data": [
                {"trade_date": "2023-01-01", "open": 150.0, "high": 155.0,
                    "low": 148.0, "close": 152.0, "vol": 1000},
                {"trade_date": "2023-12-31", "open": 160.0, "high": 165.0,
                    "low": 158.0, "close": 163.0, "vol": 1200}
            ],
            "transaction_log": [],
            "strategy_config": {
                "stock_code": "AAPL",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "upper_price": 200.0,
                "lower_price": 100.0,
                "grid_count": 1000,
                "total_investment": 10000
            },
            "market_type": "US_stock",
            "final_holding_quantity": 0,
            "average_holding_cost": 0.0
        }
        mock_backtest.return_value = mock_result

        response = client.post("/api/v1/backtest/grid", json=config_data)

        assert response.status_code == 200
        data = response.json()
        assert 'total_pnl' in data
