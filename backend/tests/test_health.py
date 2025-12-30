"""
Health Endpoint Tests

Tests for health, readiness, and info endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_returns_ok(self):
        """Test /health returns ok status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
    
    def test_ready_returns_response(self):
        """Test /ready returns a response (may be 200 or 503 depending on services)."""
        response = client.get("/ready")
        
        # In CI without Redis, may return 503
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ready" in data
        assert "checks" in data
    
    def test_ready_checks_database(self):
        """Test /ready includes database check."""
        response = client.get("/ready")
        
        data = response.json()
        assert "database" in data["checks"]
    
    def test_info_returns_service_info(self):
        """Test /info returns service information."""
        response = client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "environment" in data
    
    def test_info_includes_api_version(self):
        """Test /info includes API version."""
        response = client.get("/info")
        
        data = response.json()
        assert data["api_version"] == "v1"
