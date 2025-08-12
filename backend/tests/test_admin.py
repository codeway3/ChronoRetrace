from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app

client = TestClient(app)


@patch('app.api.v1.admin.db_admin.clear_all_financial_data')
@patch('app.api.v1.admin.FastAPICache.clear')
def test_clear_cache_success(mock_redis_clear, mock_db_clear):
    """Test successful cache clearing."""
    # Mock the database admin function
    mock_db_clear.return_value = {
        'deleted_stocks': 10,
        'deleted_commodities': 5,
        'deleted_crypto': 3,
        'message': 'Database cache cleared successfully.'
    }

    # Mock the Redis clear function
    mock_redis_clear.return_value = None

    response = client.post("/api/v1/admin/clear-cache")

    assert response.status_code == 200
    data = response.json()

    # Verify the response contains expected fields
    assert 'deleted_stocks' in data
    assert 'deleted_commodities' in data
    assert 'deleted_crypto' in data
    assert 'message' in data

    # Verify the message was updated
    assert "All database and Redis cache has been cleared successfully." in data['message']

    # Verify both functions were called
    mock_db_clear.assert_called_once()
    mock_redis_clear.assert_called_once()


@patch('app.api.v1.admin.db_admin.clear_all_financial_data')
@patch('app.api.v1.admin.FastAPICache.clear')
def test_clear_cache_database_error(mock_redis_clear, mock_db_clear):
    """Test cache clearing when database operation fails."""
    # Mock the database admin function to raise an exception
    mock_db_clear.side_effect = Exception("Database connection failed")

    # Mock the Redis clear function
    mock_redis_clear.return_value = None

    response = client.post("/api/v1/admin/clear-cache")

    assert response.status_code == 500
    data = response.json()

    # Verify error message
    assert "Database connection failed" in data['detail']

    # Verify database function was called but Redis was not
    mock_db_clear.assert_called_once()
    mock_redis_clear.assert_not_called()


@patch('app.api.v1.admin.db_admin.clear_all_financial_data')
@patch('app.api.v1.admin.FastAPICache.clear')
def test_clear_cache_redis_error(mock_redis_clear, mock_db_clear):
    """Test cache clearing when Redis operation fails."""
    # Mock the database admin function to succeed
    mock_db_clear.return_value = {
        'deleted_stocks': 5,
        'deleted_commodities': 2,
        'deleted_crypto': 1,
        'message': 'Database cache cleared successfully.'
    }

    # Mock the Redis clear function to raise an exception
    mock_redis_clear.side_effect = Exception("Redis connection failed")

    response = client.post("/api/v1/admin/clear-cache")

    assert response.status_code == 500
    data = response.json()

    # Verify error message
    assert "Redis connection failed" in data['detail']

    # Verify both functions were called
    mock_db_clear.assert_called_once()
    mock_redis_clear.assert_called_once()


@patch('app.api.v1.admin.db_admin.clear_all_financial_data')
@patch('app.api.v1.admin.FastAPICache.clear')
def test_clear_cache_empty_database_result(mock_redis_clear, mock_db_clear):
    """Test cache clearing with empty database result."""
    # Mock the database admin function to return empty result
    mock_db_clear.return_value = {
        'deleted_stocks': 0,
        'deleted_commodities': 0,
        'deleted_crypto': 0,
        'message': 'No data to clear.'
    }

    # Mock the Redis clear function
    mock_redis_clear.return_value = None

    response = client.post("/api/v1/admin/clear-cache")

    assert response.status_code == 200
    data = response.json()

    # Verify the response contains expected fields
    assert data['deleted_stocks'] == 0
    assert data['deleted_commodities'] == 0
    assert data['deleted_crypto'] == 0
    assert "All database and Redis cache has been cleared successfully." in data['message']


@patch('app.api.v1.admin.db_admin.clear_all_financial_data')
@patch('app.api.v1.admin.FastAPICache.clear')
def test_clear_cache_large_deletion_numbers(mock_redis_clear, mock_db_clear):
    """Test cache clearing with large numbers of deleted records."""
    # Mock the database admin function to return large numbers
    mock_db_clear.return_value = {
        'deleted_stocks': 10000,
        'deleted_commodities': 5000,
        'deleted_crypto': 2000,
        'message': 'Database cache cleared successfully.'
    }

    # Mock the Redis clear function
    mock_redis_clear.return_value = None

    response = client.post("/api/v1/admin/clear-cache")

    assert response.status_code == 200
    data = response.json()

    # Verify large numbers are handled correctly
    assert data['deleted_stocks'] == 10000
    assert data['deleted_commodities'] == 5000
    assert data['deleted_crypto'] == 2000
