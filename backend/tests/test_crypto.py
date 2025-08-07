import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)

@patch('app.api.v1.crypto.get_top_cryptos')
def test_read_top_cryptos_success(mock_get_top_cryptos):
    """
    Test successful retrieval of top cryptos.
    """
    mock_get_top_cryptos.return_value = [
        {"CoinInfo": {"Name": "BTC", "FullName": "Bitcoin"}, "RAW": {"USD": {"PRICE": 50000, "MKTCAP": 1000000000000}}},
        {"CoinInfo": {"Name": "ETH", "FullName": "Ethereum"}, "RAW": {"USD": {"PRICE": 4000, "MKTCAP": 500000000000}}},
    ]
    response = client.get("/api/v1/crypto/top")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["CoinInfo"]["Name"] == "BTC"
    assert data[1]["CoinInfo"]["Name"] == "ETH"

@patch('app.api.v1.crypto.get_top_cryptos')
def test_read_top_cryptos_not_found(mock_get_top_cryptos):
    """
    Test case where top cryptos cannot be fetched.
    """
    mock_get_top_cryptos.return_value = []
    response = client.get("/api/v1/crypto/top")
    assert response.status_code == 404
    assert response.json() == {"detail": "Could not fetch top cryptocurrencies."}

@patch('app.api.v1.crypto.get_crypto_ohlcv')
def test_read_crypto_history_success(mock_get_crypto_ohlcv):
    """
    Test successful retrieval of crypto historical data.
    """
    mock_get_crypto_ohlcv.return_value = [
        {"time": 1672531200, "open": 48000, "high": 52000, "low": 47000, "close": 51000, "volumeto": 10000},
        {"time": 1672617600, "open": 51000, "high": 53000, "low": 50000, "close": 52000, "volumeto": 12000},
    ]
    response = client.get("/api/v1/crypto/BTC/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["close"] == 51000

@patch('app.api.v1.crypto.get_crypto_ohlcv')
def test_read_crypto_history_not_found(mock_get_crypto_ohlcv):
    """
    Test case where historical data for a symbol cannot be fetched.
    """
    mock_get_crypto_ohlcv.return_value = []
    response = client.get("/api/v1/crypto/NONEXISTENT/history")
    assert response.status_code == 404
    assert response.json() == {"detail": "Could not fetch historical data for NONEXISTENT."}
