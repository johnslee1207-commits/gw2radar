from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class SecretRecord(BaseModel):
    user_id: str
    secret_id: str
    key_fingerprint: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    storage_backend: str
    encrypted: bool


class SecretStatus(BaseModel):
    user_id: str
    has_api_key: bool
    key_fingerprint: str | None = None
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    storage_backend: str
    encrypted: bool


class SecretStore(Protocol):
    def put_api_key(self, user_id: str, api_key: str, metadata: dict | None = None) -> SecretRecord:
        ...

    def get_api_key(self, user_id: str) -> str | None:
        ...

    def delete_api_key(self, user_id: str) -> bool:
        ...

    def rotate_api_key(self, user_id: str, new_api_key: str) -> SecretRecord:
        ...

    def get_status(self, user_id: str) -> SecretStatus:
        ...
