
from fastapi.testclient import TestClient
from unittest.mock import patch
import pandas as pd
from app.main import app
from app.services.commodity_fetcher import fetch_commodity_from_yfinance

client = TestClient(app)


@patch('app.services.commodity_fetcher.fetch_commodity_from_yfinance')
def test_get_commodity_data_success(mock_fetch):
    """
    Test successful retrieval of commodity data.
    """
    # Create a sample DataFrame to be returned by the mock
    mock_df = pd.DataFrame({
        'trade_date': ['2023-01-01', '2023-01-02'],
        'open': [1800.0, 1810.0],
        'high': [1820.0, 1825.0],
        'low': [1790.0, 1805.0],
        'close': [1810.0, 1820.0],
        'pre_close': [1800.0, 1810.0],
        'change': [10.0, 10.0],
        'pct_chg': [0.55, 0.55],
        'vol': [10000, 12000],
        'amount': [18100000, 21840000]
    })
    mock_fetch.return_value = mock_df

    response = client.get("/api/v1/commodities/GC=F")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]['ts_code'] == 'GC=F'
    assert data[0]['close'] == 1810.0
    assert data[1]['close'] == 1820.0
    mock_fetch.assert_called_once()


@patch('app.services.commodity_fetcher.fetch_commodity_from_yfinance')
def test_get_commodity_data_empty(mock_fetch):
    """
    Test case where the fetcher returns an empty DataFrame.
    """
    mock_fetch.return_value = pd.DataFrame()

    response = client.get("/api/v1/commodities/UNKNOWN")

    assert response.status_code == 200
    assert response.json() == []
    mock_fetch.assert_called_once()


@patch('app.services.commodity_fetcher.fetch_commodity_from_yfinance')
def test_get_commodity_data_exception(mock_fetch):
    """
    Test case where the fetcher raises an exception.
    """
    mock_fetch.side_effect = Exception("Network Error")

    # Use a unique symbol to avoid hitting a cached result from other tests
    response = client.get("/api/v1/commodities/FAIL-SYMBOL")

    assert response.status_code == 500
    assert "Failed to fetch data" in response.json()['detail']
    mock_fetch.assert_called_once()


def test_get_commodity_list():
    """
    Test the endpoint for retrieving the list of known commodities.
    """
    response = client.get("/api/v1/commodities/list")

    assert response.status_code == 200
    data = response.json()
    assert "GC=F" in data
    assert data["GC=F"] == "黄金"
    assert "CL=F" in data
    assert data["CL=F"] == "原油"

# Direct testing of commodity_fetcher functions


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_success(mock_download):
    """Test successful commodity data fetching and processing."""
    # Mock yfinance download response
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=5),
        'Open': [1800.0, 1810.0, 1820.0, 1830.0, 1840.0],
        'High': [1820.0, 1830.0, 1840.0, 1850.0, 1860.0],
        'Low': [1790.0, 1800.0, 1810.0, 1820.0, 1830.0],
        'Close': [1810.0, 1820.0, 1830.0, 1840.0, 1850.0],
        'Volume': [10000, 12000, 14000, 16000, 18000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-05')

    assert not result.empty
    assert len(result) == 5
    assert 'trade_date' in result.columns
    assert 'open' in result.columns
    assert 'high' in result.columns
    assert 'low' in result.columns
    assert 'close' in result.columns
    assert 'vol' in result.columns
    assert 'ma5' in result.columns
    assert 'ma10' in result.columns
    assert 'ma20' in result.columns
    assert 'ma60' in result.columns


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_empty_response(mock_download):
    """Test handling of empty response from yfinance."""
    mock_download.return_value = pd.DataFrame()

    result = fetch_commodity_from_yfinance(
        'UNKNOWN', '2023-01-01', '2023-01-05')

    assert result.empty


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_multiindex_columns(mock_download):
    """Test handling of MultiIndex columns from yfinance."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    # Create MultiIndex columns
    mock_data.columns = pd.MultiIndex.from_tuples([
        ('Date', ''), ('Open', ''), ('High',
                                     ''), ('Low', ''), ('Close', ''), ('Volume', '')
    ])
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-03')

    assert not result.empty
    assert 'trade_date' in result.columns
    assert 'open' in result.columns


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_missing_volume(mock_download):
    """Test handling of missing volume column."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0]
        # Missing Volume column
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-03')

    assert not result.empty
    assert 'vol' in result.columns
    assert result['vol'].iloc[0] == 0.0


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_weekly_interval(mock_download):
    """Test weekly interval handling."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3, freq='W'),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance(
        'GC=F', '2023-01-01', '2023-01-21', 'weekly')

    assert not result.empty
    # Verify that yfinance was called with correct interval
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]['interval'] == '1wk'


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_monthly_interval(mock_download):
    """Test monthly interval handling."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3, freq='ME'),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance(
        'GC=F', '2023-01-01', '2023-03-31', 'monthly')

    assert not result.empty
    # Verify that yfinance was called with correct interval
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]['interval'] == '1mo'


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_invalid_interval(mock_download):
    """Test handling of invalid interval."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance(
        'GC=F', '2023-01-01', '2023-01-03', 'invalid')

    assert not result.empty
    # Should default to '1d' interval
    mock_download.assert_called_once()
    call_args = mock_download.call_args
    assert call_args[1]['interval'] == '1d'


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_zero_prices_handling(mock_download):
    """Test handling of zero prices and MA calculation."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=10),
        'Open': [0.0, 1810.0, 1820.0, 1830.0, 1840.0, 1850.0, 1860.0, 1870.0, 1880.0, 1890.0],
        'High': [0.0, 1830.0, 1840.0, 1850.0, 1860.0, 1870.0, 1880.0, 1890.0, 1900.0, 1910.0],
        'Low': [0.0, 1800.0, 1810.0, 1820.0, 1830.0, 1840.0, 1850.0, 1860.0, 1870.0, 1880.0],
        'Close': [0.0, 1820.0, 1830.0, 1840.0, 1850.0, 1860.0, 1870.0, 1880.0, 1890.0, 1900.0],
        'Volume': [10000, 12000, 14000, 16000, 18000, 20000, 22000, 24000, 26000, 28000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-10')

    assert not result.empty
    # First row should have None for MAs due to zero prices being converted to NaN
    assert result['ma5'].iloc[0] is None
    # Later rows should have valid MAs
    assert result['ma5'].iloc[5] is not None


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_missing_amount_column(mock_download):
    """Test automatic calculation of amount column when missing."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-03')

    assert not result.empty
    assert 'amount' in result.columns
    # Verify amount calculation: close * volume
    expected_amount = 1810.0 * 10000
    assert abs(result['amount'].iloc[0] - expected_amount) < 0.01


@patch('app.services.commodity_fetcher.yf.download')
def test_fetch_commodity_from_yfinance_final_columns_handling(mock_download):
    """Test that all required final columns are present."""
    mock_data = pd.DataFrame({
        'Date': pd.date_range('2023-01-01', periods=3),
        'Open': [1800.0, 1810.0, 1820.0],
        'High': [1820.0, 1830.0, 1840.0],
        'Low': [1790.0, 1800.0, 1810.0],
        'Close': [1810.0, 1820.0, 1830.0],
        'Volume': [10000, 12000, 14000]
    })
    mock_download.return_value = mock_data

    result = fetch_commodity_from_yfinance('GC=F', '2023-01-01', '2023-01-03')

    expected_columns = [
        "trade_date", "open", "high", "low", "close", "pre_close",
        "change", "pct_chg", "vol", "amount",
        "ma5", "ma10", "ma20", "ma60"
    ]

    for col in expected_columns:
        assert col in result.columns
