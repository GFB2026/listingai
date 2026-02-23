"""Tests for RedisPool initialization, client access, and close."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.redis import RedisPool


class TestRedisPool:
    def test_client_raises_before_init(self):
        pool = RedisPool()
        with pytest.raises(RuntimeError, match="Redis pool not initialized"):
            _ = pool.client

    @pytest.mark.asyncio
    async def test_initialize(self):
        pool = RedisPool()
        mock_redis = MagicMock()

        with patch("app.core.redis.aioredis.from_url", return_value=mock_redis):
            await pool.initialize()

        assert pool._pool is mock_redis
        assert pool.client is mock_redis

    @pytest.mark.asyncio
    async def test_close(self):
        pool = RedisPool()
        mock_redis = AsyncMock()
        pool._pool = mock_redis

        await pool.close()
        mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_noop_when_not_initialized(self):
        pool = RedisPool()
        # Should not raise
        await pool.close()
