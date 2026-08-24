import json

from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.token_encryption_key) if settings.token_encryption_key else None


def encrypt_tokens(tokens: dict) -> bytes:
    if _fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    return _fernet.encrypt(json.dumps(tokens).encode())


def decrypt_tokens(data: bytes) -> dict:
    if _fernet is None:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY is not set")
    return json.loads(_fernet.decrypt(data).decode())
