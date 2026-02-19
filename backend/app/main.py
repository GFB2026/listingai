from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.router import api_router
from app.middleware.request_logging import RequestLoggingMiddleware


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


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="ListingAI",
        description="AI-Powered Real Estate Content Engine",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Routes
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.1.0"}

    return app


app = create_app()
