from unittest.mock import AsyncMock, MagicMock, patch

import anyio
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache

from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    # Ensure cache does not leak across tests and affect expectations
    try:
        anyio.run(FastAPICache.clear)
    except Exception:
        pass


client = TestClient(app)


@patch("akshare.futures_display_main_sina")
@patch("app.data.fetchers.futures_fetcher.fetch_china_futures_from_akshare")
def test_get_futures_data_success(mock_fetch, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.return_value = pd.DataFrame(
        {"symbol": ["rb2410"], "name": ["螺纹钢2410"]}
    )

    successful_mock = MagicMock()
    successful_mock.return_value = pd.DataFrame(
        {
            "trade_date": ["2023-01-01"],
            "close": [4010.0],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "vol": [1.0],
        }
    )
    mock_fetch.side_effect = [pd.DataFrame(), successful_mock.return_value]

    response = client.get("/api/v1/futures/rb2410")

    assert response.status_code == 200
    data = response.json()
    assert data[0]["ts_code"] == "rb2410"
    assert mock_fetch.call_count == 2


@patch("akshare.futures_display_main_sina")
@patch("app.data.fetchers.futures_fetcher.fetch_futures_from_yfinance")
def test_get_futures_data_not_found(mock_fetch, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.return_value = pd.DataFrame(
        {"symbol": ["rb2410"], "name": ["螺纹钢2410"]}
    )

    mock_fetch.return_value = pd.DataFrame()
    response = client.get("/api/v1/futures/invalid_symbol")
    assert response.status_code == 404


@patch("app.api.v1.futures.ak.futures_display_main_sina")
@patch("app.api.v1.futures.run_in_threadpool", new_callable=AsyncMock)
async def test_get_futures_list_success(mock_run_in_threadpool, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.return_value = pd.DataFrame(
        {"symbol": ["rb2410", "hc2410"], "name": ["螺纹钢2410", "热卷2410"]}
    )
    mock_run_in_threadpool.return_value = pd.DataFrame(
        {"symbol": ["rb2410", "hc2410"], "name": ["螺纹钢2410", "热卷2410"]}
    )
    response = client.get("/api/v1/futures/list")
    assert response.status_code == 200
    data = response.json()
    assert "rb2410" in data


@patch("app.api.v1.futures.ak.futures_display_main_sina")
@patch("app.api.v1.futures.run_in_threadpool", new_callable=AsyncMock)
async def test_get_futures_list_akshare_fails(mock_run_in_threadpool, mock_akshare):
    # Mock akshare to avoid initialization error
    mock_akshare.side_effect = Exception("Akshare down")
    mock_run_in_threadpool.side_effect = Exception("Akshare down")
    response = client.get("/api/v1/futures/list")
    assert response.status_code == 200
    # Check that fallback data is returned
    data = response.json()
    assert "ES=F" in data
    assert "NQ=F" in data
    assert data["ES=F"] == "E-mini S&P 500"
    assert data["NQ=F"] == "E-mini NASDAQ 100"
