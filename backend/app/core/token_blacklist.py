import time

import redis.exceptions as redis_exceptions
import structlog

from app.core.redis import get_redis

logger = structlog.get_logger()

BLACKLIST_PREFIX = "token_blacklist:"

# When Redis is down, reject tokens older than this (seconds).
# Tokens minted within this window are accepted (bounded fail-open).
FAIL_OPEN_MAX_AGE = 300  # 5 minutes


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


async def is_token_blacklisted(jti: str, iat: float | None = None) -> bool:
    """Check if a token's JTI has been blacklisted.

    Args:
        jti: JWT ID claim.
        iat: Issued-at timestamp (epoch seconds). Used for bounded fail-open
             when Redis is unavailable — tokens older than FAIL_OPEN_MAX_AGE
             are rejected.
    """
    try:
        redis = await get_redis()
        result = await redis.get(f"{BLACKLIST_PREFIX}{jti}")
        return result is not None
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        # Bounded fail-open: if we can't reach Redis and the token is older
        # than FAIL_OPEN_MAX_AGE, treat it as blacklisted. This limits the
        # replay window while avoiding a total lockout during Redis outages.
        if iat is not None:
            age = time.time() - iat
            if age > FAIL_OPEN_MAX_AGE:
                await logger.aerror(
                    "token_blacklist_fail_open_rejected",
                    jti=jti,
                    age_seconds=int(age),
                    max_age=FAIL_OPEN_MAX_AGE,
                    exc_info=True,
                )
                return True

        await logger.aerror("token_blacklist_check_failed", jti=jti, exc_info=True)
        return False
