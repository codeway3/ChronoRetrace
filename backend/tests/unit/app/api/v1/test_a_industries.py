from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch("app.data.fetchers.a_industries_fetcher.ak.stock_board_industry_spot_em")
@patch("app.data.fetchers.a_industries_fetcher.ak.stock_board_industry_hist_em")
@patch("app.data.fetchers.a_industries_fetcher.ak.stock_board_industry_name_em")
def test_overview_em_with_fallback(mock_list, mock_hist, mock_spot):
    # Simulate spot failing (network)
    mock_spot.side_effect = Exception("network error")
    # Industry list returns names/codes
    mock_list.return_value = pd.DataFrame(
        {"板块名称": ["电子元件"], "板块代码": ["BK1234"]}
    )
    # Hist by name returns data
    mock_hist.return_value = pd.DataFrame(
        {
            "日期": pd.date_range("2024-01-01", periods=25),
            "开盘": [1] * 25,
            "最高": [2] * 25,
            "最低": [1] * 25,
            "收盘": list(range(1, 26)),
            "成交量": [100] * 25,
            "成交额": [1000] * 25,
        }
    )

    resp = client.get("/api/v1/a-industries/overview?window=20D")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list) and len(data) == 1
    item = data[0]
    assert item["industry_name"] == "电子元件"
    assert item["sparkline"] and len(item["sparkline"]) > 0


@patch("app.data.fetchers.a_industries_fetcher.ak.stock_board_industry_name_ths")
@patch("app.data.fetchers.a_industries_fetcher.ak.stock_board_industry_hist_em")
def test_overview_ths_provider(mock_hist, mock_ths):
    mock_ths.return_value = pd.DataFrame(
        {
            "name": ["汽车整车"],
            "code": ["885432"],
        }
    )
    mock_hist.return_value = pd.DataFrame(
        {
            "日期": pd.date_range("2024-01-01", periods=10),
            "开盘": [1] * 10,
            "最高": [2] * 10,
            "最低": [1] * 10,
            "收盘": list(range(1, 11)),
            "成交量": [100] * 10,
            "成交额": [1000] * 10,
        }
    )

    resp = client.get("/api/v1/a-industries/overview?window=5D&provider=ths")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["industry_name"] == "汽车整车"
