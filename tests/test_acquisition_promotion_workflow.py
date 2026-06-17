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
    ContentType,
    GraphTarget,
    KbTarget,
    RawEvidenceInput,
)
from gw2radar.acquisition.promotion_workflow import (
    build_acquisition_promotion_workflow,
    render_acquisition_promotion_workflow_markdown,
)
from gw2radar.acquisition.repository import create_raw_evidence, register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_promotion_workflow_filters_queue_items_for_operator_view() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-workflow-{uuid4().hex}"
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
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Manual Patch Summary",
                    source_type=AcquisitionSourceType.MANUAL_NOTE,
                    acquisition_mode=AcquisitionMode.MANUAL,
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    review_required=True,
                ),
            )
            create_raw_evidence(
                session,
                RawEvidenceInput(
                    source_id=source.source_id,
                    content_type=ContentType.MANUAL_NOTE,
                    title="Manual patch evidence",
                    payload_hash="c" * 64,
                    summary="Summary-only patch evidence.",
                ),
            )
            workflow = build_acquisition_promotion_workflow(
                session,
                priority="P2",
                item_type="source_needs_kb_article",
                limit=1,
            )
            markdown = render_acquisition_promotion_workflow_markdown(workflow)

        assert workflow.schema_version == "gw2radar.acquisition_promotion_workflow.v1"
        assert workflow.queue_item_count == 3
        assert workflow.filtered_item_count == 1
        assert len(workflow.visible_items) == 1
        assert workflow.visible_items[0].item_type == "source_needs_kb_article"
        assert workflow.coverage_status_counts["uncovered"] == 1
        assert "Workflow is read-only" in markdown
        assert "filter_priority: `P2`" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_workflow_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-workflow-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/promotion-workflow?priority=P1&limit=5")
        markdown = client.get("/api/v1/acquisition/promotion-workflow/export?priority=P1&limit=5")
        bad = client.get("/api/v1/acquisition/promotion-workflow/export?format=json")

        assert response.status_code == 200
        workflow = response.json()["data"]["workflow"]
        assert workflow["schema_version"] == "gw2radar.acquisition_promotion_workflow.v1"
        assert workflow["filter"]["priority"] == "P1"
        assert workflow["filter"]["limit"] == 5
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Promotion Operator Workflow" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
