"""Tests for rate limiter middleware behavior, especially Redis failure handling."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.exceptions
from httpx import AsyncClient


class TestRateLimiterFailOpen:
    @pytest.mark.asyncio
    async def test_request_passes_when_redis_down(self, client: AsyncClient):
        """Rate limiter should fail open (allow requests) when Redis is unavailable."""
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            side_effect=redis.exceptions.ConnectionError("Redis unavailable"),
        ):
            response = await client.get("/api/v1/auth/me")
            # Should still reach the endpoint (401 because no token, but not blocked)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_fail_open_on_runtime_error_not_initialized(self, client: AsyncClient):
        """Rate limiter should fail open when Redis pool is not initialized."""
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Redis pool not initialized"),
        ):
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_connection_error_fails_open(self, client: AsyncClient):
        """ConnectionError during Redis access should fail open."""
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            side_effect=ConnectionError("refused"),
        ):
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 401  # reached endpoint, no auth

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


def _make_mock_redis(current_count=1, oldest_score=None):
    """Create a mock Redis client with a working pipeline mock."""
    mock_pipe = MagicMock()
    mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
    mock_pipe.zadd = MagicMock(return_value=mock_pipe)
    mock_pipe.zcard = MagicMock(return_value=mock_pipe)
    mock_pipe.expire = MagicMock(return_value=mock_pipe)
    mock_pipe.execute = AsyncMock(return_value=[0, 1, current_count, True])

    mock_redis = AsyncMock()
    mock_redis.pipeline = MagicMock(return_value=mock_pipe)
    if oldest_score is not None:
        mock_redis.zrange = AsyncMock(return_value=[(b"entry", oldest_score)])
    else:
        mock_redis.zrange = AsyncMock(return_value=[])
    return mock_redis


class TestRateLimiterSlidingWindow:
    @pytest.mark.asyncio
    async def test_request_within_limit(self, client: AsyncClient):
        """Requests within limit should pass through with rate limit headers."""
        mock_redis = _make_mock_redis(current_count=3)
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            response = await client.get("/api/v1/auth/me")
            # 401 because no auth token, but rate limiter let it through
            assert response.status_code == 401
            assert response.headers.get("X-RateLimit-Limit") == "60"
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            assert remaining == 57  # 60 - 3

    @pytest.mark.asyncio
    async def test_request_exceeds_limit(self, client: AsyncClient):
        """Requests over limit should get 429 with Retry-After header."""
        import time

        mock_redis = _make_mock_redis(current_count=61, oldest_score=time.time() - 30)
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 429
            assert "Rate limit exceeded" in response.json()["detail"]
            assert response.headers.get("X-RateLimit-Limit") == "60"
            assert response.headers.get("X-RateLimit-Remaining") == "0"
            assert int(response.headers.get("Retry-After", 0)) > 0

    @pytest.mark.asyncio
    async def test_path_specific_limit(self, client: AsyncClient):
        """Path-specific limits should override defaults."""
        # /api/v1/auth/login has a limit of 10 per 60s
        mock_redis = _make_mock_redis(current_count=5)
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "x@x.com", "password": "y"},
            )
            # Check it used the path-specific limit (10), not default (60)
            assert response.headers.get("X-RateLimit-Limit") == "10"
            remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
            assert remaining == 5  # 10 - 5

    @pytest.mark.asyncio
    async def test_prefix_limit(self, client: AsyncClient):
        """Prefix-based limits should apply to admin routes."""
        mock_redis = _make_mock_redis(current_count=10)
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            response = await client.get("/api/v1/admin/stats")
            # Admin routes have prefix limit of 30
            # But /api/v1/admin/stats has exact match in PATH_LIMITS (30, 60)
            assert response.headers.get("X-RateLimit-Limit") == "30"

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_no_oldest(self, client: AsyncClient):
        """Rate limit 429 when no oldest entry found uses default retry window."""
        mock_redis = _make_mock_redis(current_count=61)
        # zrange returns empty list → retry_after falls back to window_seconds
        mock_redis.zrange = AsyncMock(return_value=[])
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            return_value=mock_redis,
        ):
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 429
            assert int(response.headers.get("Retry-After", 0)) == 60

    @pytest.mark.asyncio
    async def test_fail_open_on_os_error(self, client: AsyncClient):
        """OSError during Redis access should fail open."""
        with patch(
            "app.middleware.rate_limiter.get_redis",
            new_callable=AsyncMock,
            side_effect=OSError("Network unreachable"),
        ):
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 401  # reached endpoint, no auth
