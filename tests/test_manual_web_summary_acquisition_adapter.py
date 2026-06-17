from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.manual_adapter import (
    ManualNoteImportInput,
    WebSummaryImportInput,
    ingest_manual_note,
    ingest_web_summary,
)
from gw2radar.acquisition.repository import get_source, list_jobs
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.models import RawEvidenceModel
from gw2radar.db.session import close_database, configure_database


def test_manual_note_import_writes_summary_only_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"manual-note-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            result = ingest_manual_note(
                session,
                ManualNoteImportInput(
                    title="Returner checklist note",
                    summary="Summary: returning players should verify unlocked mounts before planning travel-heavy goals.",
                    kb_target="returner",
                    reviewer="test_reviewer",
                ),
            )
            source = get_source(session, result.source_id)
            evidence = session.query(RawEvidenceModel).filter(RawEvidenceModel.source_id == result.source_id).one()
            jobs = list_jobs(session, source_id=result.source_id)

        assert source is not None
        assert source.source_type == "manual_note"
        assert evidence.content_type == "manual_note"
        assert evidence.summary.startswith("Summary:")
        assert evidence.payload_ref is None
        assert evidence.metadata_json["reviewer"] == "test_reviewer"
        assert jobs[0].status == "succeeded"
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_web_summary_import_keeps_reference_and_attribution_without_full_text() -> None:
    temp_dir = Path(".test_tmp") / f"web-summary-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            result = ingest_web_summary(
                session,
                WebSummaryImportInput(
                    title="Wiki summary for daily achievements",
                    source_url="https://wiki.guildwars2.com/wiki/Daily",
                    source_type="gw2_wiki",
                    kb_target="official",
                    attribution="Guild Wars 2 Wiki page reference; summary written manually.",
                    summary="Daily achievements rotate and should be treated as time-sensitive guidance.",
                ),
            )
            evidence = session.query(RawEvidenceModel).filter(RawEvidenceModel.source_id == result.source_id).one()

        assert result.source_type == "gw2_wiki"
        assert evidence.source_url == "https://wiki.guildwars2.com/wiki/Daily"
        assert evidence.payload_ref is None
        assert evidence.metadata_json["summary_only"] is True
        assert evidence.metadata_json["attribution"].startswith("Guild Wars 2 Wiki")
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_manual_adapter_rejects_private_data_markers() -> None:
    with pytest.raises(ValueError, match="Private player data"):
        ManualNoteImportInput(
            title="Unsafe note",
            summary="This contains private inventory details and should not enter public KB evidence.",
        )


def test_manual_and_web_summary_api_imports() -> None:
    temp_dir = Path(".test_tmp") / f"manual-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)

        manual = client.post(
            "/api/v1/acquisition/manual-note/import",
            json={
                "title": "Operator release note",
                "summary": "Manual note: release operator should check freshness gates before enabling rules.",
                "kb_target": "official",
                "reviewer": "api_test",
            },
        )
        web = client.post(
            "/api/v1/acquisition/web-summary/import",
            json={
                "title": "Build page summary",
                "source_url": "https://example.com/build/guardian",
                "summary": "This public build page summary is manually authored and attribution-bound.",
                "source_type": "public_build_site",
                "kb_target": "build",
                "attribution": "Example build page reference; no copied full text.",
                "reviewer": "api_test",
            },
        )

        assert manual.status_code == 200
        assert manual.json()["data"]["result"]["source_type"] == "manual_note"
        assert web.status_code == 200
        assert web.json()["data"]["result"]["source_type"] == "public_build_site"
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
