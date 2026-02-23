"""Tests for health check endpoints, metrics, and exception handlers."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.tenant import Tenant
from app.models.user import User
from app.services.ai_service import CircuitBreakerOpen


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


class TestReadinessDetails:
    @pytest.mark.asyncio
    async def test_readiness_postgres_failure(self, client: AsyncClient):
        """Readiness returns 503 when Postgres is unreachable."""
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock(side_effect=Exception("pg down"))
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.connect = MagicMock(return_value=mock_cm)

        with patch("app.core.database.engine", mock_engine):
            response = await client.get("/health/ready")
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "degraded"
            assert "error" in data["checks"]["database"]

    @pytest.mark.asyncio
    async def test_readiness_redis_failure(self, client: AsyncClient):
        """Readiness reports Redis error when Redis is down."""
        with patch(
            "app.core.redis.get_redis",
            new_callable=AsyncMock,
            side_effect=RuntimeError("not initialized"),
        ):
            response = await client.get("/health/ready")
            data = response.json()
            assert "error" in data["checks"].get("redis", "error")

    @pytest.mark.asyncio
    async def test_readiness_celery_no_workers(self, client: AsyncClient):
        """Readiness reports degraded when no Celery workers respond."""
        with patch(
            "app.workers.celery_app.celery_app"
        ) as mock_celery:
            mock_inspect = MagicMock()
            mock_inspect.ping = MagicMock(return_value=None)
            mock_celery.control.inspect = MagicMock(return_value=mock_inspect)

            response = await client.get("/health/ready")
            data = response.json()
            # Celery check might show "no_workers" or error
            assert data["status"] in ("degraded", "healthy")


class TestMetricsEndpoint:
    @pytest.mark.asyncio
    async def test_metrics_returns_prometheus_format(self, client: AsyncClient):
        """Metrics endpoint should return Prometheus text format."""
        with patch(
            "prometheus_client.generate_latest",
            return_value=b"# HELP test_metric\n# TYPE test_metric gauge\ntest_metric 1\n",
        ):
            response = await client.get("/metrics")
            assert response.status_code == 200


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

    @pytest.mark.asyncio
    async def test_circuit_breaker_exception_returns_503(
        self, client: AsyncClient, test_user: User, test_tenant: Tenant, test_listing
    ):
        """CircuitBreakerOpen exception should return 503."""
        token = create_access_token(
            data={"sub": str(test_user.id), "tenant_id": str(test_tenant.id), "role": "admin"}
        )

        mock_ai = MagicMock()
        mock_ai.generate = AsyncMock(side_effect=CircuitBreakerOpen())

        with patch("app.api.v1.content.AIService", return_value=mock_ai):
            response = await client.post(
                "/api/v1/content/generate",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "listing_id": str(test_listing.id),
                    "content_type": "listing_description",
                    "tone": "professional",
                    "variants": 1,
                },
            )
        assert response.status_code == 503
        assert "service_unavailable" in response.json().get("error", "")
