import logging
import re
import secrets
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_VALID_LOG_LEVELS = {"debug", "info", "warning", "error", "critical"}
_VALID_ENVS = {"development", "testing", "staging", "production"}
_VALID_JWT_ALGORITHMS = {"HS256", "HS384", "HS512"}


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
    claude_model_default: str = "claude-sonnet-4-5-20250929"
    claude_model_short: str = "claude-haiku-4-5-20251001"

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

    # SendGrid (email delivery)
    sendgrid_api_key: str = ""
    sendgrid_default_from_email: str = "noreply@listingai.com"
    sendgrid_default_from_name: str = "ListingAI"

    # MLS
    mls_default_base_url: str = "https://api-trestle.corelogic.com"
    mls_bridge_base_url: str = "https://api.bridgedataoutput.com"
    mls_sync_interval_minutes: int = 30

    # Tuning
    log_level: str = "info"
    max_upload_file_size: int = 10 * 1024 * 1024  # 10 MB
    database_pool_size: int = 20
    database_max_overflow: int = 10

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── Validators ──────────────────────────────────────────────────

    @field_validator("app_env")
    @classmethod
    def check_app_env(cls, v: str) -> str:
        if v not in _VALID_ENVS:
            raise ValueError(f"app_env must be one of {_VALID_ENVS}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def check_log_level(cls, v: str) -> str:
        if v.lower() not in _VALID_LOG_LEVELS:
            raise ValueError(f"log_level must be one of {_VALID_LOG_LEVELS}, got '{v}'")
        return v.lower()

    @field_validator("app_url", "frontend_url", "s3_endpoint_url", "mls_default_base_url", "mls_bridge_base_url")
    @classmethod
    def check_url_format(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError(f"URL must start with http:// or https://, got '{v}'")
        return v.rstrip("/")

    @field_validator("database_url")
    @classmethod
    def check_database_url(cls, v: str) -> str:
        if v and not v.startswith("postgresql"):
            raise ValueError(f"database_url must start with 'postgresql', got '{v[:30]}...'")
        return v

    @field_validator("database_url_sync")
    @classmethod
    def check_database_url_sync(cls, v: str) -> str:
        if v and not v.startswith("postgresql"):
            raise ValueError(f"database_url_sync must start with 'postgresql', got '{v[:30]}...'")
        return v

    @field_validator("redis_url", "celery_broker_url")
    @classmethod
    def check_redis_url(cls, v: str) -> str:
        if v and not v.startswith("redis"):
            raise ValueError(
                f"Redis URL must start with 'redis://' or"
                f" 'rediss://', got '{v[:30]}...'"
            )
        return v

    @field_validator("sendgrid_default_from_email")
    @classmethod
    def check_email_format(cls, v: str) -> str:
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError(f"Invalid email format: '{v}'")
        return v

    @field_validator("sentry_traces_sample_rate")
    @classmethod
    def check_sample_rate(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"sentry_traces_sample_rate must be 0.0-1.0, got {v}")
        return v

    @field_validator("jwt_algorithm")
    @classmethod
    def check_jwt_algorithm(cls, v: str) -> str:
        if v not in _VALID_JWT_ALGORITHMS:
            raise ValueError(f"jwt_algorithm must be one of {_VALID_JWT_ALGORITHMS}, got '{v}'")
        return v

    @field_validator("database_pool_size", "database_max_overflow")
    @classmethod
    def check_pool_size(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"Pool size must be >= 1, got {v}")
        return v

    @field_validator("mls_sync_interval_minutes")
    @classmethod
    def check_sync_interval(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"mls_sync_interval_minutes must be >= 1, got {v}")
        return v


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
        if not settings.sendgrid_api_key:
            errors.append("SENDGRID_API_KEY must be set")
        if not settings.sendgrid_default_from_email:
            errors.append("SENDGRID_DEFAULT_FROM_EMAIL must be set")
        if errors:
            raise ValueError(
                "Production configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
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
            settings.s3_secret_key = "minioadmin"  # noqa: S105

    return settings
