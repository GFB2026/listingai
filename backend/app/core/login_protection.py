import redis.exceptions as redis_exceptions
import structlog
from fastapi import HTTPException, status

from app.core.redis import get_redis

logger = structlog.get_logger()

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_SECONDS = 900  # 15 minutes


async def check_login_allowed(email: str) -> None:
    """Check if the account is locked out due to too many failed login attempts."""
    try:
        redis = await get_redis()
        lockout_key = f"login_lockout:{email}"
        locked = await redis.get(lockout_key)
        if locked:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Please try again later.",
            )
    except HTTPException:
        raise
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        # Fail open if Redis is down — still allow login attempt
        await logger.awarning("login_protection_redis_unavailable", email=email, exc_info=True)


async def record_failed_login(email: str) -> None:
    """Record a failed login attempt. Lock the account after MAX_FAILED_ATTEMPTS."""
    try:
        redis = await get_redis()
        counter_key = f"login_fails:{email}"

        count = await redis.incr(counter_key)
        if count == 1:
            await redis.expire(counter_key, LOCKOUT_WINDOW_SECONDS)

        if count >= MAX_FAILED_ATTEMPTS:
            lockout_key = f"login_lockout:{email}"
            await redis.set(lockout_key, "1", ex=LOCKOUT_WINDOW_SECONDS)
            await logger.awarning("account_locked", email=email, attempts=count)
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        await logger.awarning("login_protection_record_unavailable", email=email, exc_info=True)


async def clear_failed_logins(email: str) -> None:
    """Clear failed login counter on successful login."""
    try:
        redis = await get_redis()
        await redis.delete(f"login_fails:{email}", f"login_lockout:{email}")
    except (redis_exceptions.RedisError, ConnectionError, OSError, RuntimeError):
        await logger.awarning("login_protection_clear_unavailable", email=email, exc_info=True)
