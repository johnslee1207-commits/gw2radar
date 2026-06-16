import json
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.report_engine import (
    ReportExportFormat,
    create_report_entitlement,
    ensure_default_report_products,
    generate_report_job,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule


def test_kb_backed_paid_report_artifact_manifest_marks_reviewed_rules() -> None:
    temp_dir = Path(".test_tmp") / f"kb-paid-report-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            reviewed_rule = _create_reserve_rule(session, KnowledgeReviewStatus.REVIEWED)
            draft_rule = _create_reserve_rule(session, KnowledgeReviewStatus.DRAFT)
            job = generate_report_job(
                session,
                build_mock_graph(),
                user_id="local-user",
                product_id="legendary_gap_report",
                goal_id="gw2:goal:aurora",
                export_format=ReportExportFormat.MARKDOWN,
                output_root=temp_dir / "outputs",
                knowledge_backed=True,
                knowledge_rules=[reviewed_rule, draft_rule],
            )

        artifact = Path(str(job.artifact_path)).read_text(encoding="utf-8")
        manifest = json.loads(Path(str(job.manifest_path)).read_text(encoding="utf-8"))

        assert job.status == "succeeded"
        assert "Knowledge-backed explanations: true" in artifact
        assert "## Knowledge Base Explanations" in artifact
        assert "Reserve active legendary materials" in artifact
        assert manifest["knowledge_base"] == {
            "boundary": "reviewed_enabled_rules_only",
            "enabled": True,
            "reviewed_rule_count": 1,
        }
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_kb_backed_paid_report_api_generates_entitled_artifact() -> None:
    temp_dir = Path(".test_tmp") / f"kb-paid-report-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        locked = client.post(
            "/api/v1/reports/generate",
            json={
                "product_id": "legendary_gap_report",
                "goal_id": "gw2:goal:aurora",
                "knowledge_backed": True,
            },
        )
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            _create_reserve_rule(session, KnowledgeReviewStatus.REVIEWED)

        generated = client.post(
            "/api/v1/reports/generate",
            json={
                "product_id": "legendary_gap_report",
                "goal_id": "gw2:goal:aurora",
                "knowledge_backed": True,
            },
        )
        assert generated.status_code == 200
        job = generated.json()["data"]["job"]
        artifact_name = Path(job["artifact_path"]).name
        artifact = client.get(f"/api/v1/reports/artifacts/{artifact_name}")

        assert job["status"] == "succeeded"
        assert artifact.status_code == 200
        assert "Knowledge-backed explanations: true" in artifact.text
        assert "Reserve active legendary materials" in artifact.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)


def _create_reserve_rule(session, review_status: KnowledgeReviewStatus):
    return create_rule(
        session,
        KnowledgeRuleInput(
            name=f"{review_status.value.title()} reserve legendary materials",
            domain=KnowledgeDomain.LEGENDARY,
            condition="article_links_any_entity:gw2:item:mystic_clover",
            recommendation="Reserve active legendary materials before surplus decisions.",
            action_type="reserve_for_goal",
            explanation_template="Reviewed KB policy protects active legendary requirements.",
            confidence=0.85,
            review_status=review_status,
        ),
    )
