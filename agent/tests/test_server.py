"""Tests for FastAPI server and health endpoints.

NOTE: This test file is currently skipped. The FastAPI server module
is not implemented in the current agent architecture.
To re-enable, implement gemini_agent/server.py with FastAPI app.
"""

import pytest

# Commented out - server.py not implemented in current architecture
# from fastapi.testclient import TestClient
# from gemini_agent.server import app

pytestmark = pytest.mark.skip(reason="FastAPI server not implemented")


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        return TestClient(app)

    def test_liveness_endpoint(self, client):
        """Test the /health/live endpoint."""
        response = client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data

    def test_readiness_endpoint(self, client):
        """Test the /health/ready endpoint."""
        response = client.get("/health/ready")

        # Response code may vary based on configuration
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ready" in data
        assert "timestamp" in data
        assert "api_key" in data

    def test_health_endpoint(self, client):
        """Test the /health endpoint."""
        response = client.get("/health")

        # Response code may vary based on system state
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert data["service"] == "gemini-agent"
        assert "checks" in data
        assert isinstance(data["checks"], list)

    def test_docs_endpoint(self, client):
        """Test that API documentation is available."""
        response = client.get("/docs")

        assert response.status_code == 200
