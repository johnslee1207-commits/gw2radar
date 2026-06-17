from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.maturity import build_acquisition_maturity_report, render_acquisition_maturity_markdown
from gw2radar.acquisition.seed_packs import import_acquisition_seed_pack
from gw2radar.db.init_db import init_db
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database


def test_acquisition_maturity_report_identifies_empty_registry_gaps() -> None:
    temp_dir = Path(".test_tmp") / f"acq-maturity-empty-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            report = build_acquisition_maturity_report(session)
            markdown = render_acquisition_maturity_markdown(report)

        assert report.schema_version == "gw2radar.acquisition_maturity.v1"
        assert report.maturity_label == "early"
        assert report.source_count == 0
        assert any(dimension.dimension_id == "seed_coverage" for dimension in report.dimensions)
        assert "Import the MVP acquisition seed pack." in report.next_priorities
        assert "# Acquisition Maturity And Coverage" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_maturity_improves_after_seed_pack_import() -> None:
    temp_dir = Path(".test_tmp") / f"acq-maturity-seed-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            before = build_acquisition_maturity_report(session)
            import_acquisition_seed_pack(session, "mvp_baseline", confirmed=True)
            after = build_acquisition_maturity_report(session)

        assert after.source_count == 8
        assert after.overall_score > before.overall_score
        assert _dimension(after, "seed_coverage").score == 1.0
        assert _dimension(after, "policy_coverage").score == 1.0
        assert "Add SourcePolicy records" not in " ".join(after.next_priorities)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_maturity_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"acq-maturity-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/maturity")
        markdown = client.get("/api/v1/acquisition/maturity/export")
        bad = client.get("/api/v1/acquisition/maturity/export?format=json")

        assert response.status_code == 200
        assert response.json()["data"]["report"]["schema_version"] == "gw2radar.acquisition_maturity.v1"
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Maturity" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _dimension(report, dimension_id: str):
    return next(dimension for dimension in report.dimensions if dimension.dimension_id == dimension_id)
