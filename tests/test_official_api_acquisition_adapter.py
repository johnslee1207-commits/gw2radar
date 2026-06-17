from pathlib import Path
import shutil
from types import SimpleNamespace
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
from gw2radar.acquisition.official_api_adapter import run_official_api_acquisition_job
from gw2radar.acquisition.repository import create_job, register_source
from gw2radar.api.main import app
from gw2radar.api.routes import acquisition as acquisition_route
from gw2radar.db.init_db import init_db
from gw2radar.db.models import RawEvidenceModel
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult


class FakeGateway:
    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fake-request",
            payload={"id": 1, "name": "Copper Ore"},
            evidence_id="gateway-evidence-1",
        )

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fake-batch",
            payload=[{"id": item_id, "name": f"Item {item_id}"} for item_id in ids],
            evidence_id="gateway-evidence-batch",
        )


def test_official_public_api_adapter_marks_job_succeeded_and_writes_metadata_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"official-api-acq-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
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
            job = create_job(
                session,
                AcquisitionJobInput(
                    source_id=source.source_id,
                    params={"endpoint": "/v2/items", "request_params": {"ids": [1, 2]}},
                ),
            )
            result = run_official_api_acquisition_job(session, job.job_id, gateway=FakeGateway())
            evidence = session.query(RawEvidenceModel).filter(RawEvidenceModel.source_id == source.source_id).one()

        assert result.job.status == "succeeded"
        assert result.gateway_status == "ok"
        assert result.evidence_created is True
        assert evidence.content_type == "api_json"
        assert evidence.payload_hash
        assert evidence.payload_ref is None
        assert evidence.metadata_json["endpoint"] == "/v2/items"
        assert evidence.metadata_json["payload_shape"] == {"type": "list", "count": 2}
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_private_official_api_adapter_fails_without_runtime_key() -> None:
    temp_dir = Path(".test_tmp") / f"official-api-private-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Private account API",
                    source_type=AcquisitionSourceType.OFFICIAL_API_PRIVATE,
                    acquisition_mode=AcquisitionMode.API,
                    base_url="https://api.guildwars2.com",
                    allowed_use=AllowedUse.API_JSON,
                    graph_target=GraphTarget.PRIVATE_PLAYER_STATE,
                    kb_target=KbTarget.NONE,
                    review_required=False,
                ),
            )
            job = create_job(
                session,
                AcquisitionJobInput(source_id=source.source_id, params={"endpoint": "/v2/account"}),
            )
            result = run_official_api_acquisition_job(session, job.job_id, gateway=FakeGateway())

        assert result.job.status == "failed"
        assert result.job.last_error_code == "missing_api_key"
        assert result.evidence_created is False
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_run_official_api_route_does_not_echo_runtime_api_key(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"official-api-route-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    raw_key = "12345678-abcdef-secret-key"
    try:
        seen = {}

        def fake_run(session, job_id, *, api_key=None):
            seen["api_key"] = api_key
            job = acquisition_route.get_job(session, job_id)
            return SimpleNamespace(
                job=job,
                gateway_status="ok",
                evidence_created=False,
                gateway_evidence_id=None,
            )

        monkeypatch.setattr(acquisition_route, "run_official_api_acquisition_job", fake_run)
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
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
        job_response = client.post(
            "/api/v1/acquisition/jobs",
            json={"source_id": source_id, "params": {"endpoint": "/v2/account"}},
        )
        job_id = job_response.json()["data"]["job"]["job_id"]
        run_response = client.post(
            f"/api/v1/acquisition/jobs/{job_id}/run-official-api",
            json={"api_key": raw_key},
        )

        assert run_response.status_code == 200
        assert seen["api_key"] == raw_key
        assert raw_key not in str(run_response.json())
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
