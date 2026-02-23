"""Tests for health check endpoints."""
import pytest
from httpx import AsyncClient


class TestHealthChecks:
    @pytest.mark.asyncio
    async def test_liveness(self, client: AsyncClient):
        response = await client.get("/health/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness(self, client: AsyncClient):
        response = await client.get("/health/ready")
        # May be 200 or 503 depending on Redis availability in test env
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_health_backward_compat(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code in (200, 503)
        data = response.json()
        assert "status" in data


class TestExceptionHandlers:
    @pytest.mark.asyncio
    async def test_404_returns_json(self, client: AsyncClient):
        response = await client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code in (404, 405)
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_validation_error_returns_422(self, client: AsyncClient):
        # Send invalid data to a validation endpoint
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": "bad"},  # Missing required fields
        )
        assert response.status_code == 422
        data = response.json()
        assert "error" in data or "detail" in data
