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
    RefreshMode,
    SourcePolicyInput,
)
from gw2radar.acquisition.readiness import build_acquisition_readiness_report, render_acquisition_readiness_markdown
from gw2radar.acquisition.repository import (
    create_job,
    mark_job_succeeded,
    mark_source_reviewed,
    register_source,
    upsert_policy,
)
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_acquisition_readiness_blocks_sources_without_policy() -> None:
    temp_dir = Path(".test_tmp") / f"acq-readiness-blocked-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            register_source(
                session,
                AcquisitionSourceInput(
                    name="Unreviewed wiki summary",
                    source_type=AcquisitionSourceType.GW2_WIKI,
                    acquisition_mode=AcquisitionMode.WEB_SUMMARY,
                    base_url="https://wiki.guildwars2.com/wiki/Daily",
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                ),
            )
            report = build_acquisition_readiness_report(session)

        assert report.ready is False
        assert any(blocker.reason == "policy_missing" for blocker in report.blockers)
        assert any(blocker.reason == "freshness_unknown" for blocker in report.blockers)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_readiness_passes_with_reviewed_policy_and_successful_job() -> None:
    temp_dir = Path(".test_tmp") / f"acq-readiness-ready-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Reviewed public API",
                    source_type=AcquisitionSourceType.OFFICIAL_API_PUBLIC,
                    acquisition_mode=AcquisitionMode.API,
                    base_url="https://api.guildwars2.com",
                    allowed_use=AllowedUse.API_JSON,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                ),
            )
            source = mark_source_reviewed(session, source.source_id)
            upsert_policy(
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
            job = create_job(
                session,
                AcquisitionJobInput(source_id=source.source_id, params={"endpoint": "/v2/items"}),
            )
            mark_job_succeeded(session, job.job_id)
            report = build_acquisition_readiness_report(session)
            markdown = render_acquisition_readiness_markdown(report)

        assert report.ready is True
        assert report.paid_report_source_count == 1
        assert report.strong_recommendation_source_count == 1
        assert "Ready: yes" in markdown
        assert "- succeeded: 1" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_readiness_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"acq-readiness-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)

        report = client.get("/api/v1/acquisition/readiness")
        export = client.get("/api/v1/acquisition/readiness/export")

        assert report.status_code == 200
        assert report.json()["data"]["report"]["source_count"] == 0
        assert export.status_code == 200
        assert "# Acquisition Readiness" in export.text
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
