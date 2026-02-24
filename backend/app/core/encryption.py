from cryptography.fernet import Fernet

from app.config import get_settings


def _get_fernet() -> Fernet:
    settings = get_settings()
    if not settings.encryption_key:
        raise ValueError(
            "ENCRYPTION_KEY not set. Generate one with: "
            "python -c 'from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())'"
        )
    return Fernet(settings.encryption_key.encode())


def encrypt_value(plaintext: str) -> bytes:
    f = _get_fernet()
    return f.encrypt(plaintext.encode())


def decrypt_value(ciphertext: bytes) -> str:
    f = _get_fernet()
    return f.decrypt(ciphertext).decode()
