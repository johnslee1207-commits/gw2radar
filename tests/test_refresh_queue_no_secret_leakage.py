from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.models import RefreshQueueModel
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.refresh_queue import RefreshQueueCreate


def test_queue_sanitizes_secret_and_proxy_metadata() -> None:
    temp_dir = Path(".test_tmp") / f"sanitize-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    try:
        with session_factory() as session:
            item = RefreshQueueRepository(session).enqueue(
                RefreshQueueCreate(
                    endpoint="/v2/account",
                    params_json={
                        "ids": "1,2",
                        "api_key": "12345678-abcdef-secret-key",
                        "Authorization": "Bearer 12345678-abcdef-secret-key",
                        "proxy_url": "http://127.0.0.1:8080",
                        "nested": {"access_token": "secret-token", "safe": "value"},
                    },
                )
            )
            model = session.scalars(select(RefreshQueueModel).where(RefreshQueueModel.request_id == item.id)).one()

        serialized = str(model.params_json)
        assert model.params_hash is not None
        assert "ids" in model.params_json
        assert "safe" in model.params_json["nested"]
        assert "api_key" not in model.params_json
        assert "Authorization" not in model.params_json
        assert "proxy_url" not in model.params_json
        assert "access_token" not in model.params_json["nested"]
        assert "12345678-abcdef-secret-key" not in serialized
        assert "secret-token" not in serialized
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_queue_schema_has_no_proxy_or_ip_rotation_fields() -> None:
    temp_dir = Path(".test_tmp") / f"columns-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    try:
        init_db(engine)
        columns = {column["name"].lower() for column in inspect(engine).get_columns("refresh_queue")}
        assert "proxy_url" not in columns
        assert "proxy" not in columns
        assert "outbound_ip" not in columns
        assert "ip_rotation" not in columns
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
