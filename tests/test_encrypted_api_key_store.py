from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.models import ApiKeySecretModel
from gw2radar.security.api_key_store import EncryptedApiKeyStore


def test_encrypted_api_key_store_round_trips_without_plaintext() -> None:
    temp_dir = Path(".test_tmp") / f"key-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'key.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    raw_key = "12345678-abcdef-secret-key"
    try:
        with session_factory() as session:
            store = EncryptedApiKeyStore(session, secret="unit-test-secret")
            status = store.set(raw_key)
            model = session.scalars(select(ApiKeySecretModel)).one()
            loaded = store.get()

            assert status.storage == "sqlite_fernet"
            assert status.masked_key == "1234...-key"
            assert loaded == raw_key
            assert raw_key not in model.encrypted_value
            assert model.masked_key == "1234...-key"

        with session_factory() as session:
            status = EncryptedApiKeyStore(session, secret="unit-test-secret").delete()
            assert status.is_configured is False
            assert session.scalars(select(ApiKeySecretModel)).first() is None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
