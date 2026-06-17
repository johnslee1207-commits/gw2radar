from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.models import (
    AcquisitionJobInput,
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    GraphTarget,
    KbTarget,
)
from gw2radar.acquisition.repository import create_job, lease_next_job, register_source
from gw2radar.acquisition.worker import AcquisitionWorker
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult


class FakeGateway:
    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="worker-request",
            payload={"id": 19721, "name": "Glob of Ectoplasm"},
            evidence_id="worker-evidence",
        )

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="worker-batch",
            payload=[{"id": item_id, "name": f"Item {item_id}"} for item_id in ids],
            evidence_id="worker-evidence-batch",
        )


def test_acquisition_lease_next_sets_processing_and_skips_active_lease() -> None:
    temp_dir = Path(".test_tmp") / f"acq-lease-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = _register_public_source(session)
            create_job(session, AcquisitionJobInput(source_id=source.source_id, params={"endpoint": "/v2/items"}))
            first = lease_next_job(session, worker_id="worker-a", lease_seconds=60)
            second = lease_next_job(session, worker_id="worker-b", lease_seconds=60)

        assert first is not None
        assert first.status == "processing"
        assert first.worker_id == "worker-a"
        assert first.attempts == 1
        assert second is None
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_worker_drains_official_public_job() -> None:
    temp_dir = Path(".test_tmp") / f"acq-worker-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = _register_public_source(session)
            create_job(
                session,
                AcquisitionJobInput(
                    source_id=source.source_id,
                    params={"endpoint": "/v2/items", "request_params": {"ids": [19721]}},
                ),
            )
            result = AcquisitionWorker(session, gateway_factory=FakeGateway).drain_one()

        assert result["status"] == "succeeded"
        assert result["gateway_status"] == "ok"
        assert result["evidence_created"] is True
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_worker_skips_non_executable_manual_job() -> None:
    temp_dir = Path(".test_tmp") / f"acq-worker-manual-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Manual source",
                    source_type=AcquisitionSourceType.MANUAL_NOTE,
                    acquisition_mode=AcquisitionMode.MANUAL,
                    allowed_use=AllowedUse.MANUAL_NOTE,
                    graph_target=GraphTarget.PERSONAL_INTELLIGENCE,
                    kb_target=KbTarget.NONE,
                ),
            )
            create_job(session, AcquisitionJobInput(source_id=source.source_id, params={"title": "Manual"}))
            result = AcquisitionWorker(session, gateway_factory=FakeGateway).drain_one()

        assert result["status"] == "skipped"
        assert result["error_code"] == "adapter_not_worker_executable"
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_drain_one_api_idle_and_private_missing_key() -> None:
    temp_dir = Path(".test_tmp") / f"acq-worker-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    raw_key = "12345678-abcdef-secret-key"
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)

        idle = client.post("/api/v1/acquisition/jobs/drain-one", json={"use_stored_api_key": False})
        source_response = client.post(
            "/api/v1/sources",
            json={
                "name": "Private account API",
                "source_type": "official_api_private",
                "acquisition_mode": "api",
                "base_url": "https://api.guildwars2.com",
                "allowed_use": "api_json",
                "graph_target": "private_player_state",
                "kb_target": "none",
                "review_required": False,
            },
        )
        source_id = source_response.json()["data"]["source"]["source_id"]
        client.post("/api/v1/acquisition/jobs", json={"source_id": source_id, "params": {"endpoint": "/v2/account"}})
        drained = client.post("/api/v1/acquisition/jobs/drain-one", json={"use_stored_api_key": False})

        assert idle.status_code == 200
        assert idle.json()["data"]["status"] == "idle"
        assert drained.status_code == 200
        assert drained.json()["data"]["status"] == "failed"
        assert raw_key not in str(drained.json())
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _register_public_source(session):
    return register_source(
        session,
        AcquisitionSourceInput(
            name="Official items API",
            source_type=AcquisitionSourceType.OFFICIAL_API_PUBLIC,
            acquisition_mode=AcquisitionMode.API,
            base_url="https://api.guildwars2.com",
            allowed_use=AllowedUse.API_JSON,
            graph_target=GraphTarget.PUBLIC_GAME,
            kb_target=KbTarget.OFFICIAL,
            review_required=False,
        ),
    )
