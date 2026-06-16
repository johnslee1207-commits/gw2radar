from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.refresh_queue import RefreshQueueCreate, RefreshQueueStatus


def _session_factory(name: str):
    temp_dir = Path(".test_tmp") / f"{name}-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    return temp_dir, engine, sessionmaker(bind=engine)


def test_lease_next_moves_queued_to_processing_and_mark_done_succeeds() -> None:
    temp_dir, engine, session_factory = _session_factory("lease")
    now = datetime.now(timezone.utc)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            queued = repo.enqueue(RefreshQueueCreate(endpoint="/v2/items", params_json={"ids": "1"}))
            leased = repo.lease_next("worker-a", now, lease_seconds=45)
            done = repo.mark_done(queued.id)

        assert leased is not None
        assert leased.id == queued.id
        assert leased.status is RefreshQueueStatus.PROCESSING
        assert leased.worker_id == "worker-a"
        assert leased.leased_until is not None
        assert done.status is RefreshQueueStatus.SUCCEEDED
        assert done.completed_at is not None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delayed_task_becomes_available_after_next_attempt_at() -> None:
    temp_dir, engine, session_factory = _session_factory("delayed")
    now = datetime.now(timezone.utc)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            queued = repo.enqueue(RefreshQueueCreate(endpoint="/v2/items", params_json={"ids": "1"}))
            repo.lease_next("worker-a", now)
            repo.mark_retry(
                queued.id,
                status_code=503,
                error_code="temporary_failure",
                error_message="temporary failure",
                next_attempt_at=now + timedelta(minutes=5),
            )

            assert repo.lease_next("worker-b", now + timedelta(minutes=1)) is None
            ready = repo.lease_next("worker-b", now + timedelta(minutes=6))

        assert ready is not None
        assert ready.id == queued.id
        assert ready.status is RefreshQueueStatus.PROCESSING
        assert ready.worker_id == "worker-b"
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mark_failed_records_terminal_failure() -> None:
    temp_dir, engine, session_factory = _session_factory("failed")
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            queued = repo.enqueue(RefreshQueueCreate(endpoint="/v2/items"))
            failed = repo.mark_failed(
                queued.id,
                status_code=500,
                error_code="server_error",
                error_message="server failed",
            )

        assert failed.status is RefreshQueueStatus.FAILED
        assert failed.last_status_code == 500
        assert failed.last_error_code == "server_error"
        assert failed.last_error_message == "server failed"
        assert failed.completed_at is not None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
