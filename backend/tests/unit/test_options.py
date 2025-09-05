from unittest.mock import AsyncMock, patch

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
    try:
        anyio.run(FastAPICache.clear)
    except Exception:
        pass


client = TestClient(app)


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_option_expirations_success(mock_run_in_threadpool):
    mock_run_in_threadpool.return_value = ("2025-12-19", "2026-12-18")
    response = client.get("/api/v1/options/expirations/SPY")
    assert response.status_code == 200
    assert response.json() == ["2025-12-19", "2026-12-18"]


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_option_expirations_not_found(mock_run_in_threadpool):
    mock_run_in_threadpool.side_effect = Exception("Not found")
    response = client.get("/api/v1/options/expirations/INVALID")
    assert response.status_code == 404


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_option_chain_success(mock_run_in_threadpool):
    mock_run_in_threadpool.return_value = [
        {"contract_symbol": "SPY251219C00600000", "type": "call"},
        {"contract_symbol": "SPY251219P00600000", "type": "put"},
    ]
    response = client.get("/api/v1/options/chain/SPY?expiration_date=2025-12-19")
    assert response.status_code == 200
    assert len(response.json()) == 2


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_option_chain_failure(mock_run_in_threadpool):
    mock_run_in_threadpool.side_effect = Exception("Fetch failed")
    response = client.get("/api/v1/options/chain/SPY?expiration_date=2025-12-19")
    assert response.status_code == 500


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_options_data_success(mock_run_in_threadpool):
    mock_df = pd.DataFrame(
        {
            "trade_date": ["2023-01-01"],
            "close": [10.8],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "vol": [1.0],
            "pre_close": [1.0],
            "change": [1.0],
            "pct_chg": [1.0],
            "amount": [1.0],
            "ma5": [1.0],
            "ma10": [1.0],
            "ma20": [1.0],
            "ma60": [1.0],
        }
    )
    mock_run_in_threadpool.return_value = mock_df
    response = client.get("/api/v1/options/SPY251219C00600000")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["ts_code"] == "SPY251219C00600000"


@patch("app.api.v1.options.run_in_threadpool", new_callable=AsyncMock)
async def test_get_options_data_empty(mock_run_in_threadpool):
    mock_run_in_threadpool.return_value = pd.DataFrame()
    response = client.get("/api/v1/options/UNKNOWN_CONTRACT")
    assert response.status_code == 200
    assert response.json() == []
