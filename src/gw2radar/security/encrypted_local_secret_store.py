from sqlalchemy.orm import Session

from gw2radar.security.encrypted_database_secret_store import EncryptedDatabaseSecretStore


class EncryptedLocalSecretStore(EncryptedDatabaseSecretStore):
    storage_backend = "encrypted_local"

    def __init__(self, session: Session, *, encryption_secret: str | None = None) -> None:
        super().__init__(session, encryption_secret=encryption_secret)
