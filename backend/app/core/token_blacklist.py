import redis.exceptions as redis_exceptions
import structlog

from app.core.redis import get_redis

logger = structlog.get_logger()

BLACKLIST_PREFIX = "token_blacklist:"


async def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token's JTI to the blacklist with TTL matching its expiry."""
    try:
        redis = await get_redis()
        await redis.set(f"{BLACKLIST_PREFIX}{jti}", "1", ex=ttl_seconds)
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        # If we can't blacklist, log as error (not warning) — this is a security
        # concern since the token remains valid until its natural expiry.
        await logger.aerror(
            "token_blacklist_set_failed",
            jti=jti,
            ttl=ttl_seconds,
            exc_info=True,
        )


async def is_token_blacklisted(jti: str) -> bool:
    """Check if a token's JTI has been blacklisted."""
    try:
        redis = await get_redis()
        result = await redis.get(f"{BLACKLIST_PREFIX}{jti}")
        return result is not None
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        # If Redis is down, we can't verify blacklist status. Log as error
        # and return False (fail open) — the token is still time-limited by its exp claim.
        await logger.aerror("token_blacklist_check_failed", jti=jti, exc_info=True)
        return False
