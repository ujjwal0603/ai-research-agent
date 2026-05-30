import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    """Create test client"""
    app = create_app()
    return TestClient(app)

class TestHealth:
    """Health check endpoint tests"""

    def test_health_check(self, client):
        """Test health endpoint returns ok status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_readiness_check(self, client):
        """Test readiness endpoint"""
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

class TestRoot:
    """Root endpoint tests"""

    def test_root_endpoint(self, client):
        """Test root endpoint returns app info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "docs" in data
