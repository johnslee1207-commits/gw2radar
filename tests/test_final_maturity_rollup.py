from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.final_maturity_rollup import build_final_maturity_rollup, render_final_maturity_rollup_markdown
from gw2radar.acquisition.models import (
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    GraphTarget,
    KbTarget,
)
from gw2radar.acquisition.repository import register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_final_maturity_rollup_summarizes_kb_acquisition_and_release_manifest() -> None:
    temp_dir = Path(".test_tmp") / f"final-rollup-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'rollup.db'}")
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
            rollup = build_final_maturity_rollup(session)
            markdown = render_final_maturity_rollup_markdown(rollup)

        assert rollup.schema_version == "gw2radar.final_maturity_rollup.v1"
        assert rollup.component_count == 3
        assert {component.component_id for component in rollup.components} == {
            "kb_semantic_spine",
            "acquisition_maturity",
            "promotion_release_manifest",
        }
        assert rollup.overall_score > 0
        assert rollup.release_ready is False
        assert "/api/v1/acquisition/promotion-release-manifest" in rollup.evidence_chain
        assert "Final MVP Maturity Rollup" in markdown
        assert "No generated recommendation may invent facts" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_final_maturity_rollup_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"final-rollup-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/final-maturity-rollup")
        markdown = client.get("/api/v1/acquisition/final-maturity-rollup/export")
        bad = client.get("/api/v1/acquisition/final-maturity-rollup/export?format=json")

        assert response.status_code == 200
        rollup = response.json()["data"]["rollup"]
        assert rollup["schema_version"] == "gw2radar.final_maturity_rollup.v1"
        assert rollup["component_count"] == 3
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Final MVP Maturity Rollup" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
