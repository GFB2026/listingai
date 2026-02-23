"""Tests for security utilities and token blacklist behavior."""
from unittest.mock import AsyncMock, patch

import pytest

from app.core.security import (
    generate_api_key,
    verify_api_key,
)


class TestAPIKeys:
    def test_generate_api_key(self):
        full_key, prefix, key_hash = generate_api_key()
        assert full_key.startswith("lai_")
        assert prefix.startswith("lai_")
        assert len(key_hash) == 64  # SHA-256 hex digest

    def test_verify_api_key(self):
        full_key, prefix, key_hash = generate_api_key()
        assert verify_api_key(full_key, key_hash)
        assert not verify_api_key("wrong_key", key_hash)


class TestTokenBlacklist:
    @pytest.mark.asyncio
    async def test_blacklist_token(self):
        from app.core.token_blacklist import blacklist_token, is_token_blacklisted

        # When Redis is available, token should be blacklisted
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1")

        with patch("app.core.token_blacklist.get_redis", return_value=mock_redis):
            await blacklist_token("test-jti", 3600)
            mock_redis.set.assert_called_once()

            result = await is_token_blacklisted("test-jti")
            assert result is True

    @pytest.mark.asyncio
    async def test_blacklist_not_found(self):
        from app.core.token_blacklist import is_token_blacklisted

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.token_blacklist.get_redis", return_value=mock_redis):
            result = await is_token_blacklisted("nonexistent-jti")
            assert result is False

    @pytest.mark.asyncio
    async def test_blacklist_redis_down_fails_open(self):
        """When Redis is unavailable, is_token_blacklisted should return False (fail open)."""
        import redis.exceptions

        from app.core.token_blacklist import is_token_blacklisted

        with patch(
            "app.core.token_blacklist.get_redis",
            side_effect=redis.exceptions.ConnectionError("Redis down"),
        ):
            result = await is_token_blacklisted("some-jti")
            assert result is False


class TestLoginProtection:
    @pytest.mark.asyncio
    async def test_check_login_allowed_when_not_locked(self):
        from app.core.login_protection import check_login_allowed

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        with patch("app.core.login_protection.get_redis", return_value=mock_redis):
            # Should not raise
            await check_login_allowed("user@example.com")

    @pytest.mark.asyncio
    async def test_check_login_locked(self):
        from fastapi import HTTPException

        from app.core.login_protection import check_login_allowed

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="1")

        with patch("app.core.login_protection.get_redis", return_value=mock_redis):
            with pytest.raises(HTTPException) as exc_info:
                await check_login_allowed("locked@example.com")
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_login_protection_redis_down_fails_open(self):
        import redis.exceptions

        from app.core.login_protection import check_login_allowed

        with patch(
            "app.core.login_protection.get_redis",
            side_effect=redis.exceptions.ConnectionError("Redis down"),
        ):
            # Should not raise — fail open
            await check_login_allowed("user@example.com")

    @pytest.mark.asyncio
    async def test_record_failed_login_increments(self):
        from app.core.login_protection import record_failed_login

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=3)
        mock_redis.expire = AsyncMock()

        with patch("app.core.login_protection.get_redis", return_value=mock_redis):
            await record_failed_login("user@example.com")
            mock_redis.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_failed_login_locks_at_threshold(self):
        from app.core.login_protection import MAX_FAILED_ATTEMPTS, record_failed_login

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=MAX_FAILED_ATTEMPTS)
        mock_redis.expire = AsyncMock()
        mock_redis.set = AsyncMock()

        with patch("app.core.login_protection.get_redis", return_value=mock_redis):
            await record_failed_login("user@example.com")
            # Should call redis.set for the lockout key
            mock_redis.set.assert_called_once()
