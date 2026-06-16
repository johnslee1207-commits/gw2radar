from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.models import SecretModel
from gw2radar.security.encrypted_database_secret_store import EncryptedDatabaseSecretStore
from gw2radar.security.encrypted_local_secret_store import EncryptedLocalSecretStore


def test_encrypted_local_secret_store_stores_encrypted_payload() -> None:
    temp_dir, engine, session_factory = _factory("local-secret")
    raw_key = "12345678-abcdef-secret-key"
    try:
        with session_factory() as session:
            store = EncryptedLocalSecretStore(session, encryption_secret="unit-test-secret")
            record = store.put_api_key("local-user", raw_key)
            model = session.scalars(select(SecretModel)).one()

            assert record.encrypted is True
            assert record.storage_backend == "encrypted_local"
            assert store.get_api_key("local-user") == raw_key
            assert raw_key not in str(model.encrypted_payload_json)
            assert model.encrypted_payload_json["algorithm"] == "fernet-sha256-derived-key"
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_encrypted_database_secret_store_delete_removes_usable_secret() -> None:
    temp_dir, engine, session_factory = _factory("db-secret")
    try:
        with session_factory() as session:
            store = EncryptedDatabaseSecretStore(session, encryption_secret="unit-test-secret")
            store.put_api_key("user-1", "12345678-abcdef-secret-key")
            assert store.delete_api_key("user-1") is True
            model = session.scalars(select(SecretModel)).one()

            assert store.get_api_key("user-1") is None
            assert model.deleted_at is not None
            assert model.encrypted_payload_json["ciphertext"] == ""
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _factory(name: str):
    temp_dir = Path(".test_tmp") / f"{name}-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'secret.db'}")
    init_db(engine)
    return temp_dir, engine, sessionmaker(bind=engine)
