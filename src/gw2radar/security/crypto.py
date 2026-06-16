from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from hashlib import sha256

from cryptography.fernet import Fernet
from pydantic import BaseModel

from gw2radar.config.settings import get_settings


class EncryptedSecretPayload(BaseModel):
    version: str = "v1"
    algorithm: str = "fernet-sha256-derived-key"
    ciphertext: str
    nonce: str | None = None
    created_at: datetime


def encrypt_secret(secret_value: str, *, encryption_secret: str | None = None) -> EncryptedSecretPayload:
    fernet = Fernet(_derive_fernet_key(encryption_secret or get_settings().api_key_encryption_secret))
    return EncryptedSecretPayload(
        ciphertext=fernet.encrypt(secret_value.encode("utf-8")).decode("utf-8"),
        created_at=datetime.now(timezone.utc),
    )


def decrypt_secret(payload: EncryptedSecretPayload | dict, *, encryption_secret: str | None = None) -> str:
    parsed = payload if isinstance(payload, EncryptedSecretPayload) else EncryptedSecretPayload.model_validate(payload)
    fernet = Fernet(_derive_fernet_key(encryption_secret or get_settings().api_key_encryption_secret))
    return fernet.decrypt(parsed.ciphertext.encode("utf-8")).decode("utf-8")


def fingerprint_api_key(api_key: str, *, server_secret: str | None = None) -> str:
    secret = server_secret or get_settings().api_key_encryption_secret
    return sha256(f"{api_key}:{secret}".encode("utf-8")).hexdigest()[:8]


def _derive_fernet_key(secret: str) -> bytes:
    return urlsafe_b64encode(sha256(secret.encode("utf-8")).digest())
