from datetime import datetime, timezone
from pathlib import Path
import shutil
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.refresh_queue_status import RefreshQueueStatus
from gw2radar.ingest.refresh_worker import RefreshWorker
from gw2radar.ingest.request_queue import QueuedRequest


class StaticClient:
    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        return Gw2ApiResponse(endpoint=endpoint, params=params or {}, payload={"ok": True})


def test_refresh_queue_persists_retry_metadata() -> None:
    temp_dir = Path(".test_tmp") / f"queue-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'queue.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            request = repo.enqueue(QueuedRequest(endpoint="/v2/items", params={"ids": "1"}))
            repo.mark_retry(request.request_id, retry_after_seconds=30, error="rate_limited_retrying")

        with session_factory() as session:
            delayed = RefreshQueueRepository(session).list_by_status(RefreshQueueStatus.DELAYED)

        assert len(delayed) == 1
        assert delayed[0].attempts == 1
        assert delayed[0].retry_after_seconds == 30
        assert delayed[0].last_error == "rate_limited_retrying"
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_refresh_worker_marks_due_request_succeeded() -> None:
    temp_dir = Path(".test_tmp") / f"worker-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'worker.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)
    try:
        with session_factory() as session:
            repo = RefreshQueueRepository(session)
            repo.enqueue(QueuedRequest(endpoint="/v2/items", params={"ids": "1"}))
            result = RefreshWorker(repo, Gw2ApiGateway(client=StaticClient())).process_next()
            succeeded = repo.list_by_status(RefreshQueueStatus.SUCCEEDED)

        assert result["status"] == "succeeded"
        assert len(succeeded) == 1
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
