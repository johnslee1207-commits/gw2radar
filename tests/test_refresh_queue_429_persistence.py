from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.refresh_queue import RefreshQueueCreate, RefreshQueueStatus


def test_429_retry_metadata_persists_across_repository_reload() -> None:
    temp_dir = Path(".test_tmp") / f"rate-limit-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            queued = repo.enqueue(
                RefreshQueueCreate(
                    endpoint="/v2/account",
                    params_json={"ids": "1", "api_key": "12345678-abcdef-secret-key"},
                )
            )
            repo.mark_retry(
                queued.id,
                status_code=429,
                error_code="rate_limited_retrying",
                error_message="retry after official rate limit",
                next_attempt_at=retry_at,
            )

        with session_factory() as session:
            delayed = RefreshQueueRepository(session).list_by_status(
                RefreshQueueStatus.DELAYED,
                as_items=True,
            )[0]

        assert delayed.last_status_code == 429
        assert delayed.last_error_code == "rate_limited_retrying"
        assert delayed.next_attempt_at is not None
        assert "api_key" not in (delayed.params_json or {})
        assert "12345678-abcdef-secret-key" not in str(delayed.model_dump())
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
