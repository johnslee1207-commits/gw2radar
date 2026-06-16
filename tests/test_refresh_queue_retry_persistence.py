from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.refresh_queue import RefreshQueueCreate, RefreshQueueStatus


def test_retry_metadata_survives_repository_reload() -> None:
    temp_dir = Path(".test_tmp") / f"retry-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=90)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            queued = repo.enqueue(RefreshQueueCreate(endpoint="/v2/items", params_json={"ids": "1"}))
            repo.mark_retry(
                queued.id,
                status_code=503,
                error_code="temporary_unavailable",
                error_message="temporary unavailable",
                next_attempt_at=next_attempt_at,
            )

        with session_factory() as session:
            delayed = RefreshQueueRepository(session).list_by_status(
                RefreshQueueStatus.DELAYED,
                as_items=True,
            )

        assert len(delayed) == 1
        assert delayed[0].attempt_count == 1
        assert delayed[0].last_status_code == 503
        assert delayed[0].last_error_code == "temporary_unavailable"
        assert delayed[0].last_error_message == "temporary unavailable"
        assert delayed[0].next_attempt_at is not None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
