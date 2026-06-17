from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.local_pdf_adapter import ingest_pdf_inventory_as_acquisition_sources
from gw2radar.acquisition.repository import list_jobs, list_sources
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb_pdf.pdf_inventory import build_inventory


def test_local_pdf_adapter_registers_sources_evidence_and_jobs_idempotently() -> None:
    repo_root = Path(".test_tmp") / f"local-pdf-acq-{uuid4().hex}"
    source_root = repo_root / "docs" / "knowledge_base" / "_sources" / "pdf"
    (source_root / "patch_notes" / "2026").mkdir(parents=True)
    (source_root / "official_api" / "endpoints").mkdir(parents=True)
    (source_root / "patch_notes" / "2026" / "Game Update Notes_ June 2, 2026 - Game Update Notes.pdf").write_bytes(
        b"%PDF fake patch"
    )
    (source_root / "official_api" / "endpoints" / "API_2_account - Guild Wars 2 Wiki (GW2W).pdf").write_bytes(
        b"%PDF fake account"
    )
    engine = create_engine(f"sqlite:///{repo_root / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        records = build_inventory(repo_root, source_root)
        with session_factory() as session:
            first = ingest_pdf_inventory_as_acquisition_sources(session, records, requested_by="test")
            second = ingest_pdf_inventory_as_acquisition_sources(session, records, requested_by="test")
            sources = list_sources(session)
            jobs = list_jobs(session)

        assert first.source_count == 2
        assert first.new_source_count == 2
        assert first.new_evidence_count == 2
        assert first.job_count == 2
        assert second.new_source_count == 0
        assert second.new_evidence_count == 0
        assert second.job_count == 2
        assert {source.source_type for source in sources} == {"downloaded_pdf", "official_patch_note"}
        assert all(job.status == "succeeded" for job in jobs)
        assert len(jobs) == 4
    finally:
        engine.dispose()
        shutil.rmtree(repo_root, ignore_errors=True)


def test_local_pdf_import_api_uses_inventory_records() -> None:
    repo_root = Path(".test_tmp") / f"local-pdf-api-{uuid4().hex}"
    source_root = repo_root / "docs" / "knowledge_base" / "_sources" / "pdf" / "official_news"
    source_root.mkdir(parents=True)
    (source_root / "News_ Guild Wars 2 Homesteads Preview.pdf").write_bytes(b"%PDF fake news")
    try:
        configure_database(f"sqlite:///{repo_root / 'api.db'}")
        init_db()
        response = TestClient(app).post(
            "/api/v1/acquisition/local-pdf/import",
            json={
                "repo_root": str(repo_root),
                "source_root": "docs/knowledge_base/_sources/pdf",
                "requested_by": "test",
            },
        )

        assert response.status_code == 200
        result = response.json()["data"]["result"]
        assert result["source_count"] == 1
        assert result["new_source_count"] == 1
        assert result["new_raw_evidence_count"] == 1
        assert result["acquisition_job_count"] == 1
    finally:
        close_database()
        shutil.rmtree(repo_root, ignore_errors=True)
