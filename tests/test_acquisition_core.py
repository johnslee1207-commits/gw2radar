from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.models import (
    AcquisitionJobInput,
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    GraphTarget,
    KbTarget,
    RefreshMode,
    SourcePolicyInput,
)
from gw2radar.acquisition.repository import (
    create_job,
    get_source_health,
    mark_job_succeeded,
    mark_source_reviewed,
    register_source,
    upsert_policy,
)
from gw2radar.db.init_db import init_db


def test_acquisition_source_policy_job_and_health_flow() -> None:
    temp_dir = Path(".test_tmp") / f"acq-core-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acquisition.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Official GW2 Public API",
                    source_type=AcquisitionSourceType.OFFICIAL_API_PUBLIC,
                    acquisition_mode=AcquisitionMode.API,
                    base_url="https://api.guildwars2.com/",
                    allowed_use=AllowedUse.API_JSON,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    trust_level=0.95,
                ),
            )
            source = mark_source_reviewed(session, source.source_id)
            policy = upsert_policy(
                session,
                source.source_id,
                SourcePolicyInput(
                    allowed_use=AllowedUse.API_JSON,
                    refresh_mode=RefreshMode.SCHEDULED,
                    refresh_interval_seconds=3600,
                    can_drive_paid_report=True,
                    can_drive_strong_recommendation=True,
                ),
            )
            job = create_job(session, AcquisitionJobInput(source_id=source.source_id, params={"ids": "1,2"}))
            job = mark_job_succeeded(session, job.job_id)
            health = get_source_health(session, source.source_id)

        assert source.review_status == "reviewed"
        assert policy.refresh_mode == "scheduled"
        assert job.status == "succeeded"
        assert health.freshness_status == "fresh"
        assert health.action_eligibility.can_drive_strong_recommendation is True
        assert health.action_eligibility.can_drive_paid_report is True
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_rejects_secret_and_proxy_job_params() -> None:
    with pytest.raises(ValueError, match="sensitive or proxy"):
        AcquisitionJobInput(
            source_id="acq_source_test",
            params={"api_key": "secret", "nested": {"proxy_url": "http://127.0.0.1:8080"}},
        )


def test_private_official_api_must_target_private_graph() -> None:
    with pytest.raises(ValueError, match="private player state"):
        AcquisitionSourceInput(
            name="Private account endpoint",
            source_type=AcquisitionSourceType.OFFICIAL_API_PRIVATE,
            acquisition_mode=AcquisitionMode.API,
            base_url="https://api.guildwars2.com/",
            allowed_use=AllowedUse.API_JSON,
            graph_target=GraphTarget.PUBLIC_GAME,
            kb_target=KbTarget.NONE,
        )


def test_acquisition_schema_has_no_proxy_rotation_fields() -> None:
    temp_dir = Path(".test_tmp") / f"acq-schema-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acquisition.db'}")
    try:
        init_db(engine)
        for table in ["acquisition_sources", "source_policies", "acquisition_jobs", "raw_evidence"]:
            columns = {column["name"].lower() for column in inspect(engine).get_columns(table)}
            assert "proxy_url" not in columns
            assert "proxy" not in columns
            assert "outbound_ip" not in columns
            assert "ip_rotation" not in columns
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
