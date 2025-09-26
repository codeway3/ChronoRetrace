from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.infrastructure.database.session import get_db
from app.main import app


def override_get_db():
    try:
        db = MagicMock()
        yield db
    finally:
        pass


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to ChronoRetrace API"}


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
