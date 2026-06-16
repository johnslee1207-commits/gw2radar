from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.refresh_queue import (
    RefreshQueueCreate,
    RefreshQueuePriority,
    RefreshQueueStatus,
    RefreshTaskType,
)


def test_refresh_queue_model_has_post_mvp_columns() -> None:
    temp_dir = Path(".test_tmp") / f"queue-model-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    try:
        init_db(engine)
        columns = {column["name"] for column in inspect(engine).get_columns("refresh_queue")}

        assert {
            "request_id",
            "task_type",
            "priority",
            "status",
            "endpoint",
            "method",
            "params_hash",
            "params_json",
            "account_id",
            "feature_scope",
            "attempts",
            "max_attempts",
            "next_attempt_at",
            "leased_until",
            "worker_id",
            "last_status_code",
            "last_error_code",
            "last_error",
            "completed_at",
        }.issubset(columns)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_enqueue_creates_queued_task_item() -> None:
    temp_dir = Path(".test_tmp") / f"queue-item-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    try:
        with session_factory() as session:
            item = RefreshQueueRepository(session).enqueue(
                RefreshQueueCreate(
                    task_type=RefreshTaskType.ACCOUNT_SNAPSHOT_SYNC,
                    priority=RefreshQueuePriority.P1_ACCOUNT_SNAPSHOT,
                    endpoint="/v2/account",
                    account_id="gw2:account:Test.1234",
                )
            )

        assert item.status is RefreshQueueStatus.QUEUED
        assert item.task_type is RefreshTaskType.ACCOUNT_SNAPSHOT_SYNC
        assert item.priority is RefreshQueuePriority.P1_ACCOUNT_SNAPSHOT
        assert item.method == "GET"
        assert item.params_hash is not None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
