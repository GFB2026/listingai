import time
import uuid

import structlog
from prometheus_client import Counter, Histogram, Gauge
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being processed",
    ["method"],
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        structlog.contextvars.bind_contextvars(request_id=request_id)

        REQUESTS_IN_PROGRESS.labels(method=request.method).inc()
        try:
            response = await call_next(request)
        finally:
            REQUESTS_IN_PROGRESS.labels(method=request.method).dec()

        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)

        # Normalize path to avoid high-cardinality label explosion
        path = request.url.path
        if path.startswith("/api/v1/"):
            parts = path.split("/")
            # Replace UUIDs with :id placeholder
            normalized = "/".join(
                ":id" if len(p) == 36 and "-" in p else p for p in parts
            )
        else:
            normalized = path

        REQUEST_COUNT.labels(
            method=request.method, path=normalized, status=response.status_code
        ).inc()
        REQUEST_DURATION.labels(method=request.method, path=normalized).observe(duration)

        await logger.ainfo(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )

        response.headers["X-Request-ID"] = request_id
        return response
