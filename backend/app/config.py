from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_env: str = "development"
    app_debug: bool = True
    app_secret_key: str = "change-me-to-a-random-secret-key"
    app_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://listingai:listingai_dev@localhost:5432/listingai"
    database_url_sync: str = "postgresql://listingai:listingai_dev@localhost:5432/listingai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"

    # Anthropic
    anthropic_api_key: str = ""

    # JWT
    jwt_secret_key: str = "change-me-jwt-secret"
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
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "listingai-media"
    s3_region: str = "us-east-1"

    # MLS
    mls_default_base_url: str = "https://api-trestle.corelogic.com"
    mls_sync_interval_minutes: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
