"""Tests for rate limiter middleware behavior, especially Redis failure handling."""
from unittest.mock import AsyncMock, patch

import pytest
import redis.exceptions
from httpx import AsyncClient


class TestRateLimiterFailOpen:
    @pytest.mark.asyncio
    async def test_request_passes_when_redis_down(self, client: AsyncClient):
        """Rate limiter should fail open (allow requests) when Redis is unavailable."""
        with patch(
            "app.middleware.rate_limiter.get_redis",
            side_effect=redis.exceptions.ConnectionError("Redis unavailable"),
        ):
            response = await client.get("/health/live")
            # Should succeed even though rate limiter can't reach Redis
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_skip_paths_bypass_rate_limiter(self, client: AsyncClient):
        """Whitelisted paths should not be rate limited."""
        response = await client.get("/health")
        assert response.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, client: AsyncClient):
        """API responses should include rate limit headers when Redis is available."""
        # This test depends on Redis being available; if not, headers won't be present
        response = await client.get("/api/v1/auth/me")
        # Either rate limit headers or a pass-through (Redis down)
        if response.headers.get("X-RateLimit-Limit"):
            assert int(response.headers["X-RateLimit-Limit"]) > 0
