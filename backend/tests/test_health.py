"""
Health Endpoint Tests

Tests for /health, /ready, /metrics, /info endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client: AsyncClient):
        """Test /health returns status ok."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert data["service"] == "chainshield"
    
    @pytest.mark.asyncio
    async def test_ready_returns_status(self, client: AsyncClient):
        """Test /ready returns readiness status."""
        response = await client.get("/ready")
        
        # May return 200 or 503 depending on DB status
        assert response.status_code in [200, 503]
        data = response.json()
        assert "ready" in data
        assert "checks" in data
    
    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, client: AsyncClient):
        """Test /metrics returns Prometheus format."""
        response = await client.get("/metrics")
        
        assert response.status_code == 200
        content = response.text
        # Prometheus format includes HELP and TYPE comments
        assert "chainshield" in content
    
    @pytest.mark.asyncio
    async def test_info_returns_app_info(self, client: AsyncClient):
        """Test /info returns application information."""
        response = await client.get("/info")
        
        assert response.status_code == 200
        data = response.json()
        assert "app" in data
        assert "version" in data
        assert "environment" in data
