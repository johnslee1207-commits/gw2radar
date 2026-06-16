from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.models import SecretModel
from gw2radar.security.encrypted_database_secret_store import EncryptedDatabaseSecretStore


def test_raw_api_key_does_not_appear_in_secret_db_row() -> None:
    temp_dir = Path(".test_tmp") / f"no-plaintext-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'secret.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    raw_key = "12345678-abcdef-secret-key"
    try:
        with session_factory() as session:
            EncryptedDatabaseSecretStore(session, encryption_secret="unit-test-secret").put_api_key("user-1", raw_key)
            model = session.scalars(select(SecretModel)).one()
            assert raw_key not in str(model.__dict__)
            assert raw_key not in str(model.encrypted_payload_json)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
