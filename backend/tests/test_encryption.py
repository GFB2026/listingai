"""Tests for encryption utilities."""
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet


class TestEncryption:
    def test_roundtrip(self):
        key = Fernet.generate_key().decode()
        mock_settings = MagicMock()
        mock_settings.encryption_key = key

        with patch("app.core.encryption.get_settings", return_value=mock_settings):
            from app.core.encryption import decrypt_value, encrypt_value

            plaintext = "my_secret_value"
            encrypted = encrypt_value(plaintext)
            assert isinstance(encrypted, bytes)
            assert encrypted != plaintext.encode()

            decrypted = decrypt_value(encrypted)
            assert decrypted == plaintext

    def test_roundtrip_special_chars(self):
        key = Fernet.generate_key().decode()
        mock_settings = MagicMock()
        mock_settings.encryption_key = key

        with patch("app.core.encryption.get_settings", return_value=mock_settings):
            from app.core.encryption import decrypt_value, encrypt_value

            plaintext = "p@$$w0rd!#%^&*()"
            encrypted = encrypt_value(plaintext)
            assert decrypt_value(encrypted) == plaintext

    def test_missing_key_raises(self):
        mock_settings = MagicMock()
        mock_settings.encryption_key = ""

        with patch("app.core.encryption.get_settings", return_value=mock_settings):
            from app.core.encryption import encrypt_value

            with pytest.raises(ValueError, match="ENCRYPTION_KEY not set"):
                encrypt_value("test")
