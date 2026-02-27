"""Tests for configuration validation and secret management."""
import os
from unittest.mock import patch

import pytest


class TestConfigValidation:
    def test_production_rejects_empty_secrets(self):
        """Production mode should raise ValueError when required secrets are empty."""
        from app.config import get_settings

        # Clear lru_cache
        get_settings.cache_clear()

        env = {
            "APP_ENV": "production",
            "APP_SECRET_KEY": "",
            "JWT_SECRET_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "ENCRYPTION_KEY": "",
            "S3_ACCESS_KEY": "",
            "S3_SECRET_KEY": "",
            "STRIPE_WEBHOOK_SECRET": "",
        }

        with patch.dict(os.environ, env, clear=False):
            with pytest.raises(ValueError, match="Production configuration errors"):
                # Force fresh settings
                get_settings.cache_clear()
                get_settings()

        get_settings.cache_clear()

    def test_development_auto_generates_secrets(self):
        """Development mode should auto-generate secrets when empty."""
        from app.config import get_settings

        get_settings.cache_clear()

        env = {
            "APP_ENV": "development",
            "APP_SECRET_KEY": "",
            "JWT_SECRET_KEY": "",
        }

        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.app_secret_key.startswith("dev-")
            assert settings.jwt_secret_key.startswith("dev-")
            assert len(settings.app_secret_key) > 20

        get_settings.cache_clear()

    def test_production_accepts_valid_secrets(self):
        """Production mode should accept properly set secrets."""
        from app.config import get_settings

        get_settings.cache_clear()

        env = {
            "APP_ENV": "production",
            "APP_SECRET_KEY": "real-secret-key-here",
            "JWT_SECRET_KEY": "real-jwt-secret-here",
            "ANTHROPIC_API_KEY": "sk-ant-real",
            "ENCRYPTION_KEY": "real-encryption-key",
            "S3_ACCESS_KEY": "real-access-key",
            "S3_SECRET_KEY": "real-secret-key",
            "STRIPE_SECRET_KEY": "sk_live_real",
            "STRIPE_PUBLISHABLE_KEY": "pk_live_real",
            "STRIPE_WEBHOOK_SECRET": "whsec_real",
            "SENDGRID_API_KEY": "SG.real-key",
            "SENDGRID_DEFAULT_FROM_EMAIL": "noreply@example.com",
        }

        with patch.dict(os.environ, env, clear=False):
            get_settings.cache_clear()
            settings = get_settings()
            assert settings.app_secret_key == "real-secret-key-here"

        get_settings.cache_clear()
