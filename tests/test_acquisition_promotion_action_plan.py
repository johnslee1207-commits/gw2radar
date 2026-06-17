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
from gw2radar.acquisition.promotion_action_plan import (
    build_acquisition_promotion_action_plans,
    render_acquisition_promotion_action_plans_markdown,
)
from gw2radar.acquisition.repository import register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_promotion_action_plan_builds_checklist_for_queue_item() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-action-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
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
            item_id = f"promotion:source_needs_raw_evidence:{source.source_id}"
            bundle = build_acquisition_promotion_action_plans(session, item_id=item_id)
            markdown = render_acquisition_promotion_action_plans_markdown(bundle)

        assert bundle.schema_version == "gw2radar.acquisition_promotion_action_plan_bundle.v1"
        assert bundle.plan_count == 1
        plan = bundle.plans[0]
        assert plan.item_id == item_id
        assert plan.item_type == "source_needs_raw_evidence"
        assert "RawEvidence row linked to the acquisition source." in plan.expected_evidence
        assert "Do not enable a KnowledgeRule without reviewer confirmation." in plan.forbidden_actions
        assert "Acquisition Promotion Action Plans" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_action_plan_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-action-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/promotion-action-plans?limit=5")
        markdown = client.get("/api/v1/acquisition/promotion-action-plans/export?limit=5")
        bad = client.get("/api/v1/acquisition/promotion-action-plans/export?format=json")

        assert response.status_code == 200
        bundle = response.json()["data"]["bundle"]
        assert bundle["schema_version"] == "gw2radar.acquisition_promotion_action_plan_bundle.v1"
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Promotion Action Plans" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
