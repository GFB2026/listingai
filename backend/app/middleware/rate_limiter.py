import time

from fastapi import HTTPException, Request

from app.core.redis import get_redis


async def check_rate_limit(
    request: Request,
    key_prefix: str = "rl",
    max_requests: int = 60,
    window_seconds: int = 60,
) -> None:
    """Redis-based sliding window rate limiter."""
    redis = await get_redis()

    # Build key from client IP or user ID
    client_id = request.client.host if request.client else "unknown"
    key = f"{key_prefix}:{client_id}:{int(time.time()) // window_seconds}"

    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)

    if current > max_requests:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s.",
        )
