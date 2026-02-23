import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_debug: bool = False
    app_secret_key: str = ""
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Sentry
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    # Database
    database_url: str = "postgresql+asyncpg://listingai:listingai_dev@localhost:5432/listingai"
    database_url_sync: str = "postgresql://listingai:listingai_dev@localhost:5432/listingai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Anthropic
    anthropic_api_key: str = ""

    # JWT
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # Encryption
    encryption_key: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id_starter: str = ""
    stripe_price_id_professional: str = ""
    stripe_price_id_enterprise: str = ""

    # S3 / MinIO
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket_name: str = "listingai-media"
    s3_region: str = "us-east-1"

    # MLS
    mls_default_base_url: str = "https://api-trestle.corelogic.com"
    mls_sync_interval_minutes: int = 30

    # Tuning
    log_level: str = "info"
    max_upload_file_size: int = 10 * 1024 * 1024  # 10 MB
    database_pool_size: int = 20
    database_max_overflow: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()

    if settings.app_env in ("production", "staging"):
        errors = []
        if not settings.app_secret_key:
            errors.append("APP_SECRET_KEY must be set")
        if not settings.jwt_secret_key:
            errors.append("JWT_SECRET_KEY must be set")
        if not settings.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY must be set")
        if not settings.encryption_key:
            errors.append("ENCRYPTION_KEY must be set")
        if not settings.s3_access_key:
            errors.append("S3_ACCESS_KEY must be set")
        if not settings.s3_secret_key:
            errors.append("S3_SECRET_KEY must be set")
        if not settings.stripe_webhook_secret:
            errors.append("STRIPE_WEBHOOK_SECRET must be set")
        if not settings.stripe_secret_key:
            errors.append("STRIPE_SECRET_KEY must be set")
        if not settings.stripe_publishable_key:
            errors.append("STRIPE_PUBLISHABLE_KEY must be set")
        if errors:
            raise ValueError(
                f"Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            )
    elif settings.app_env in ("development", "testing"):
        # Auto-generate ephemeral secrets for development/testing so no
        # hardcoded values ever exist in the codebase.
        if not settings.app_secret_key:
            settings.app_secret_key = f"dev-{secrets.token_urlsafe(32)}"
        if not settings.jwt_secret_key:
            settings.jwt_secret_key = f"dev-{secrets.token_urlsafe(32)}"
        if not settings.s3_access_key:
            settings.s3_access_key = "minioadmin"
        if not settings.s3_secret_key:
            settings.s3_secret_key = "minioadmin"

    return settings
