from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache

from app.main import app

client = TestClient(app)


@patch("akshare.futures_display_main_sina")
@patch("app.data.fetchers.commodity_fetcher.fetch_commodity_from_yfinance")
def test_get_commodity_data_success(mock_fetch, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.return_value = pd.DataFrame(
        {"symbol": ["ag2412"], "name": ["白银2412"]}
    )

    successful_mock = MagicMock()
    successful_mock.return_value = pd.DataFrame(
        {
            "trade_date": ["2023-01-01"],
            "close": [1810.0],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "vol": [1.0],
        }
    )
    mock_fetch.side_effect = [pd.DataFrame(), successful_mock.return_value]
    response = client.get("/api/v1/commodities/ag2412")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["ts_code"] == "ag2412"


@patch("akshare.futures_display_main_sina")
@patch("app.data.fetchers.commodity_fetcher.fetch_commodity_from_yfinance")
def test_get_commodity_data_not_found(mock_fetch, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.return_value = pd.DataFrame(
        {"symbol": ["ag2412"], "name": ["白银2412"]}
    )

    mock_fetch.return_value = pd.DataFrame()
    response = client.get("/api/v1/commodities/invalid_symbol")
    assert response.status_code == 404


pytestmark = [pytest.mark.anyio, pytest.mark.usefixtures("setup_fastapi_cache")]


@patch("app.api.v1.commodities.run_in_threadpool", new_callable=AsyncMock)
async def test_get_commodity_list_success(mock_run_in_threadpool):
    # Mock successful akshare call
    mock_run_in_threadpool.return_value = pd.DataFrame(
        {"symbol": ["ag2412", "CL2412"], "name": ["白银2412", "原油2412"]}
    )
    response = client.get("/api/v1/commodities/list")
    assert response.status_code == 200
    data = response.json()
    assert "ag2412" in data
    assert data["ag2412"] == "白银2412"


@patch("app.api.v1.commodities.run_in_threadpool", new_callable=AsyncMock)
async def test_get_commodity_list_akshare_fails(mock_run_in_threadpool):
    # Mock akshare failure
    mock_run_in_threadpool.side_effect = Exception("Akshare down")
    response = client.get("/api/v1/commodities/list")
    assert response.status_code == 200
    data = response.json()
    assert data == {"GC=F": "黄金", "SI=F": "白银", "CL=F": "原油"}
