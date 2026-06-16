from dataclasses import dataclass
from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from hashlib import sha256

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from gw2radar.config.settings import get_settings
from gw2radar.db.models import ApiKeySecretModel
from gw2radar.ingest.security import mask_api_key


@dataclass(frozen=True)
class ApiKeyStatus:
    is_configured: bool
    masked_key: str | None = None
    storage: str = "memory_only"


class InMemoryApiKeyStore:
    def __init__(self) -> None:
        self._api_key: str | None = None

    def set(self, api_key: str) -> ApiKeyStatus:
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty.")
        self._api_key = api_key.strip()
        return self.status()

    def get(self) -> str | None:
        return self._api_key

    def delete(self) -> ApiKeyStatus:
        self._api_key = None
        return self.status()

    def status(self) -> ApiKeyStatus:
        return ApiKeyStatus(
            is_configured=self._api_key is not None,
            masked_key=mask_api_key(self._api_key),
        )


api_key_store = InMemoryApiKeyStore()


class EncryptedApiKeyStore:
    SECRET_ID = "default"

    def __init__(self, session: Session, *, secret: str | None = None) -> None:
        self.session = session
        self.fernet = Fernet(_derive_fernet_key(secret or get_settings().api_key_encryption_secret))

    def set(self, api_key: str) -> ApiKeyStatus:
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty.")
        clean_key = api_key.strip()
        encrypted = self.fernet.encrypt(clean_key.encode("utf-8")).decode("utf-8")
        masked = mask_api_key(clean_key) or "***"
        now = datetime.now(timezone.utc)
        model = self.session.get(ApiKeySecretModel, self.SECRET_ID)
        if model is None:
            self.session.add(
                ApiKeySecretModel(
                    id=self.SECRET_ID,
                    encrypted_value=encrypted,
                    masked_key=masked,
                    storage="sqlite_fernet",
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            model.encrypted_value = encrypted
            model.masked_key = masked
            model.storage = "sqlite_fernet"
            model.updated_at = now
        self.session.commit()
        return self.status()

    def get(self) -> str | None:
        model = self.session.get(ApiKeySecretModel, self.SECRET_ID)
        if model is None:
            return None
        return self.fernet.decrypt(model.encrypted_value.encode("utf-8")).decode("utf-8")

    def delete(self) -> ApiKeyStatus:
        model = self.session.get(ApiKeySecretModel, self.SECRET_ID)
        if model is not None:
            self.session.delete(model)
            self.session.commit()
        return self.status()

    def status(self) -> ApiKeyStatus:
        model = self.session.get(ApiKeySecretModel, self.SECRET_ID)
        return ApiKeyStatus(
            is_configured=model is not None,
            masked_key=model.masked_key if model is not None else None,
            storage="sqlite_fernet",
        )


def _derive_fernet_key(secret: str) -> bytes:
    return urlsafe_b64encode(sha256(secret.encode("utf-8")).digest())
