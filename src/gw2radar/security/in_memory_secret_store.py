from datetime import datetime, timezone

from gw2radar.security.crypto import fingerprint_api_key
from gw2radar.security.secret_store import SecretRecord, SecretStatus


class InMemorySecretStore:
    storage_backend = "memory_test"

    def __init__(self) -> None:
        self._records: dict[str, tuple[str, SecretRecord]] = {}

    def put_api_key(self, user_id: str, api_key: str, metadata: dict | None = None) -> SecretRecord:
        now = datetime.now(timezone.utc)
        record = SecretRecord(
            user_id=user_id,
            secret_id=f"{user_id}:gw2_api_key",
            key_fingerprint=fingerprint_api_key(api_key),
            created_at=now,
            updated_at=now,
            storage_backend=self.storage_backend,
            encrypted=False,
        )
        self._records[user_id] = (api_key, record)
        return record

    def get_api_key(self, user_id: str) -> str | None:
        entry = self._records.get(user_id)
        if entry is None:
            return None
        api_key, record = entry
        self._records[user_id] = (api_key, record.model_copy(update={"last_used_at": datetime.now(timezone.utc)}))
        return api_key

    def delete_api_key(self, user_id: str) -> bool:
        return self._records.pop(user_id, None) is not None

    def rotate_api_key(self, user_id: str, new_api_key: str) -> SecretRecord:
        return self.put_api_key(user_id, new_api_key)

    def get_status(self, user_id: str) -> SecretStatus:
        entry = self._records.get(user_id)
        if entry is None:
            return SecretStatus(user_id=user_id, has_api_key=False, storage_backend=self.storage_backend, encrypted=False)
        record = entry[1]
        return SecretStatus(
            user_id=user_id,
            has_api_key=True,
            key_fingerprint=record.key_fingerprint,
            created_at=record.created_at,
            last_used_at=record.last_used_at,
            storage_backend=record.storage_backend,
            encrypted=record.encrypted,
        )
