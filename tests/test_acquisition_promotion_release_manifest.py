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
from gw2radar.acquisition.promotion_release_manifest import (
    build_acquisition_promotion_release_manifest,
    render_acquisition_promotion_release_manifest_markdown,
)
from gw2radar.acquisition.repository import register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_promotion_release_manifest_links_operator_artifacts_and_evidence_chain() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-manifest-{uuid4().hex}"
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
            manifest = build_acquisition_promotion_release_manifest(session)
            markdown = render_acquisition_promotion_release_manifest_markdown(manifest)

        assert manifest.schema_version == "gw2radar.acquisition_promotion_release_manifest.v1"
        assert manifest.release_ready is False
        assert {artifact.artifact_id for artifact in manifest.artifacts} == {
            "promotion_readiness",
            "promotion_workflow",
            "promotion_action_plans",
        }
        assert "/api/v1/acquisition/promotion-action-plans" in manifest.evidence_chain
        assert any("read-only" in note for note in manifest.safety_boundary)
        assert "Acquisition Promotion Release Manifest" in markdown
        assert "promotion_workflow" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_release_manifest_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-manifest-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/promotion-release-manifest")
        markdown = client.get("/api/v1/acquisition/promotion-release-manifest/export")
        bad = client.get("/api/v1/acquisition/promotion-release-manifest/export?format=json")

        assert response.status_code == 200
        manifest = response.json()["data"]["manifest"]
        assert manifest["schema_version"] == "gw2radar.acquisition_promotion_release_manifest.v1"
        assert "promotion_workflow" in {artifact["artifact_id"] for artifact in manifest["artifacts"]}
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Promotion Release Manifest" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
