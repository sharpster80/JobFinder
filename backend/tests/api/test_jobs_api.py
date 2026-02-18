import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.database import get_db

@pytest.fixture
def client(db_session):
    """Create a test client with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200

def test_get_jobs_returns_list(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_jobs_filters_by_status(client):
    response = client.get("/api/jobs?status=new")
    assert response.status_code == 200
