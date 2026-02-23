import asyncio
import logging
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.api.router import api_router
from app.core.logging_config import configure_logging
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    from app.core.database import engine
    from app.core.redis import redis_pool

    await redis_pool.initialize()
    yield
    # Shutdown
    await redis_pool.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()

    # Configure structured logging before anything else
    configure_logging(settings.app_env, settings.app_debug)

    # Initialize Sentry (no-op if DSN is empty)
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,
        )

    app = FastAPI(
        title="ListingAI",
        description="AI-Powered Real Estate Content Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — explicit methods and headers
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With", "X-Request-ID", "X-CSRF-Token"],
        expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
    )

    # Middleware stack (order matters — outermost first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(CSRFMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health/live")
    async def liveness_check():
        """Liveness probe — always returns 200 if the process is running."""
        return {"status": "alive"}

    @app.get("/health/ready")
    async def readiness_check():
        """Readiness probe — checks Postgres + Redis connectivity."""
        checks = {}
        overall_healthy = True

        # Check PostgreSQL
        try:
            from app.core.database import engine
            from sqlalchemy import text
            async with asyncio.timeout(5):
                async with engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            overall_healthy = False

        # Check Redis
        try:
            from app.core.redis import get_redis
            async with asyncio.timeout(5):
                redis = await get_redis()
                await redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {str(e)}"
            overall_healthy = False

        # Check Celery broker connectivity
        try:
            from app.workers.celery_app import celery_app as _celery
            async with asyncio.timeout(5):
                inspect = _celery.control.inspect(timeout=3)
                result = await asyncio.to_thread(inspect.ping)
            checks["celery"] = "ok" if result else "no_workers"
            if not result:
                overall_healthy = False
        except Exception as e:
            checks["celery"] = f"error: {str(e)}"
            overall_healthy = False

        status_str = "healthy" if overall_healthy else "degraded"
        status_code = 200 if overall_healthy else 503

        return JSONResponse(
            status_code=status_code,
            content={
                "status": status_str,
                "version": "0.1.0",
                "checks": checks,
            },
        )

    @app.get("/health")
    async def health_check():
        """Backward-compatible health check — delegates to readiness."""
        return await readiness_check()

    @app.get("/metrics")
    async def metrics():
        """Prometheus metrics endpoint."""
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from starlette.responses import Response as StarletteResponse
        return StarletteResponse(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    # --- Exception handlers ---

    from app.services.ai_service import CircuitBreakerOpen

    @app.exception_handler(CircuitBreakerOpen)
    async def circuit_breaker_handler(request: Request, exc: CircuitBreakerOpen):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "service_unavailable",
                "detail": str(exc),
                "request_id": request.headers.get("x-request-id"),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # Sanitize Pydantic v2 errors: ctx may contain non-serializable objects
        errors = []
        for err in exc.errors():
            clean = {**err}
            if "ctx" in clean:
                clean["ctx"] = {k: str(v) for k, v in clean["ctx"].items()}
            errors.append(clean)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "detail": errors,
                "request_id": request.headers.get("x-request-id"),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": "http_error",
                "detail": exc.detail,
                "request_id": request.headers.get("x-request-id"),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        sentry_sdk.capture_exception(exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "detail": "An unexpected error occurred.",
                "request_id": request.headers.get("x-request-id"),
            },
        )

    return app


app = create_app()
