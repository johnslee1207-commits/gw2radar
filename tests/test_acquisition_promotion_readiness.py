from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.models import (
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    GraphTarget,
    KbTarget,
)
from gw2radar.acquisition.promotion_readiness import (
    build_acquisition_promotion_readiness_report,
    render_acquisition_promotion_readiness_markdown,
)
from gw2radar.acquisition.repository import register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_promotion_readiness_blocks_sources_without_raw_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-readiness-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            register_source(
                session,
                AcquisitionSourceInput(
                    name="Official Patch PDFs",
                    source_type=AcquisitionSourceType.DOWNLOADED_PDF,
                    acquisition_mode=AcquisitionMode.LOCAL_FILE,
                    local_path="docs/knowledge_base/_sources/pdf/news",
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    review_required=True,
                ),
            )
            report = build_acquisition_promotion_readiness_report(session)
            markdown = render_acquisition_promotion_readiness_markdown(report)

        assert report.schema_version == "gw2radar.acquisition_promotion_readiness.v1"
        assert report.ready is False
        assert report.blocker_count >= 1
        assert "source_needs_raw_evidence" in report.queue_counts_by_type
        assert "Acquisition Promotion Readiness Gate" in markdown
        assert "Import raw evidence" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_readiness_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-readiness-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/promotion-readiness")
        markdown = client.get("/api/v1/acquisition/promotion-readiness/export")
        bad = client.get("/api/v1/acquisition/promotion-readiness/export?format=json")

        assert response.status_code == 200
        assert response.json()["data"]["report"]["schema_version"] == "gw2radar.acquisition_promotion_readiness.v1"
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Promotion Readiness Gate" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
