from datetime import datetime, timezone

from sqlalchemy.orm import Session

from gw2radar.db.models import SecretModel
from gw2radar.security.crypto import decrypt_secret, encrypt_secret, fingerprint_api_key
from gw2radar.security.secret_store import SecretRecord, SecretStatus


class EncryptedDatabaseSecretStore:
    storage_backend = "encrypted_database"
    secret_type = "gw2_api_key"

    def __init__(self, session: Session, *, encryption_secret: str | None = None) -> None:
        self.session = session
        self.encryption_secret = encryption_secret

    def put_api_key(self, user_id: str, api_key: str, metadata: dict | None = None) -> SecretRecord:
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty.")
        clean_key = api_key.strip()
        now = datetime.now(timezone.utc)
        secret_id = self._secret_id(user_id)
        payload = encrypt_secret(clean_key, encryption_secret=self.encryption_secret)
        fingerprint = fingerprint_api_key(clean_key, server_secret=self.encryption_secret)
        model = self.session.get(SecretModel, secret_id)
        if model is None:
            model = SecretModel(
                id=secret_id,
                user_id=user_id,
                secret_type=self.secret_type,
                key_fingerprint=fingerprint,
                encrypted_payload_json=payload.model_dump(mode="json"),
                storage_backend=self.storage_backend,
                created_at=now,
                updated_at=now,
            )
            self.session.add(model)
        else:
            model.key_fingerprint = fingerprint
            model.encrypted_payload_json = payload.model_dump(mode="json")
            model.storage_backend = self.storage_backend
            model.updated_at = now
            model.deleted_at = None
        self.session.commit()
        return self._record_from_model(model)

    def get_api_key(self, user_id: str) -> str | None:
        model = self.session.get(SecretModel, self._secret_id(user_id))
        if model is None or model.deleted_at is not None:
            return None
        model.last_used_at = datetime.now(timezone.utc)
        self.session.commit()
        return decrypt_secret(model.encrypted_payload_json, encryption_secret=self.encryption_secret)

    def delete_api_key(self, user_id: str) -> bool:
        model = self.session.get(SecretModel, self._secret_id(user_id))
        if model is None or model.deleted_at is not None:
            return False
        model.encrypted_payload_json = {"version": "deleted", "algorithm": "none", "ciphertext": "", "created_at": datetime.now(timezone.utc).isoformat()}
        model.deleted_at = datetime.now(timezone.utc)
        model.updated_at = model.deleted_at
        self.session.commit()
        return True

    def rotate_api_key(self, user_id: str, new_api_key: str) -> SecretRecord:
        return self.put_api_key(user_id, new_api_key)

    def get_status(self, user_id: str) -> SecretStatus:
        model = self.session.get(SecretModel, self._secret_id(user_id))
        if model is None or model.deleted_at is not None:
            return SecretStatus(user_id=user_id, has_api_key=False, storage_backend=self.storage_backend, encrypted=True)
        return SecretStatus(
            user_id=user_id,
            has_api_key=True,
            key_fingerprint=model.key_fingerprint,
            created_at=model.created_at,
            last_used_at=model.last_used_at,
            storage_backend=model.storage_backend,
            encrypted=True,
        )

    def _record_from_model(self, model: SecretModel) -> SecretRecord:
        return SecretRecord(
            user_id=model.user_id,
            secret_id=model.id,
            key_fingerprint=model.key_fingerprint,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_used_at=model.last_used_at,
            storage_backend=model.storage_backend,
            encrypted=True,
        )

    def _secret_id(self, user_id: str) -> str:
        return f"{user_id}:{self.secret_type}"
