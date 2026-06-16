from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule
from gw2radar.kb.kb_report_quality import score_kb_report_quality
from gw2radar.reports.markdown_report import generate_kb_backed_markdown_report


def test_kb_report_quality_scores_explanation_coverage() -> None:
    temp_dir = Path(".test_tmp") / f"kb-quality-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        graph = build_mock_graph()
        actions = generate_actions(graph, "gw2:goal:aurora")
        with db_session.SessionLocal() as session:
            rule = _create_reserve_rule(session, KnowledgeReviewStatus.REVIEWED)

        quality = score_kb_report_quality(actions, [rule])
        markdown = generate_kb_backed_markdown_report(graph, "gw2:goal:aurora", [rule])

        assert quality.total_actions == len(actions)
        assert quality.explained_actions == 1
        assert quality.matched_rule_count == 1
        assert quality.quality_label in {"moderate", "needs_review"}
        assert "Some recommendations have no reviewed KB explanation." in quality.warnings
        assert "## Knowledge Base Quality" in markdown
        assert "Explanation coverage:" in markdown
    finally:
        close_database()


def test_kb_report_quality_api_returns_quality_summary() -> None:
    temp_dir = Path(".test_tmp") / f"kb-quality-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            _create_reserve_rule(session, KnowledgeReviewStatus.REVIEWED)

        response = client.get("/api/v1/kb/goals/gw2:goal:aurora/report-quality")

        assert response.status_code == 200
        quality = response.json()["data"]["quality"]
        assert quality["total_actions"] > 0
        assert quality["explained_actions"] == 1
        assert quality["matched_rule_count"] == 1
    finally:
        close_database()
        state.reset_cached_graph()


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
