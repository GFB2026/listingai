import time

import redis.exceptions as redis_exceptions
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.redis import get_redis

logger = structlog.get_logger()

# Paths to skip rate limiting
SKIP_PATHS = {"/health", "/health/live", "/health/ready", "/metrics", "/docs", "/redoc", "/openapi.json"}

# Per-path overrides: (max_requests, window_seconds)
PATH_LIMITS = {
    "/api/v1/auth/login": (10, 60),
    "/api/v1/auth/register": (5, 60),
    "/api/v1/auth/refresh": (20, 60),
    "/api/v1/media/upload": (20, 60),
    "/api/v1/admin/stats": (30, 60),
    "/api/v1/content/generate": (5, 60),    # expensive Claude API calls
    "/api/v1/content/batch": (2, 300),      # batch jobs — max 2 per 5 min
}

# Prefix-based limits for route groups: (prefix, max_requests, window_seconds)
PREFIX_LIMITS = [
    ("/api/v1/admin/", 30, 60),
]

# Default limits
DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip rate limiting for whitelisted paths
        if path in SKIP_PATHS:
            return await call_next(request)

        # Determine limits: exact match first, then prefix, then default
        if path in PATH_LIMITS:
            max_requests, window_seconds = PATH_LIMITS[path]
        else:
            max_requests, window_seconds = DEFAULT_MAX_REQUESTS, DEFAULT_WINDOW_SECONDS
            for prefix, prefix_max, prefix_window in PREFIX_LIMITS:
                if path.startswith(prefix):
                    max_requests, window_seconds = prefix_max, prefix_window
                    break

        client_ip = request.client.host if request.client else "unknown"

        try:
            redis = await get_redis()
            now = time.time()
            key = f"rl:{client_ip}:{path}"

            # Sliding window using Redis sorted set
            pipe = redis.pipeline()
            # Remove entries outside the window
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            # Add current request
            pipe.zadd(key, {f"{now}": now})
            # Count requests in window
            pipe.zcard(key)
            # Set expiry on the key
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            current_count = results[2]
            remaining = max(0, max_requests - current_count)

            if current_count > max_requests:
                # Find oldest entry to calculate retry-after
                oldest = await redis.zrange(key, 0, 0, withscores=True)
                retry_after = int(window_seconds - (now - oldest[0][1])) if oldest else window_seconds

                response = JSONResponse(
                    status_code=429,
                    content={"detail": f"Rate limit exceeded. Max {max_requests} requests per {window_seconds}s."},
                )
                response.headers["X-RateLimit-Limit"] = str(max_requests)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["Retry-After"] = str(max(1, retry_after))
                return response

            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(max_requests)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response

        except (redis_exceptions.RedisError, ConnectionError, OSError):
            # Fail open — if Redis is unavailable, allow the request through
            await logger.awarning("rate_limiter_redis_unavailable", path=path, client_ip=client_ip, exc_info=True)
            return await call_next(request)
        except RuntimeError as exc:
            # Redis pool not initialized (app startup race)
            if "not initialized" in str(exc):
                return await call_next(request)
            raise
