from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule


def test_kb_action_explanation_and_report_api() -> None:
    temp_dir = Path(".test_tmp") / f"kb-explain-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        client.post("/mock/load")
        with db_session.SessionLocal() as session:
            create_rule(
                session,
                KnowledgeRuleInput(
                    name="Reserve legendary materials",
                    domain=KnowledgeDomain.LEGENDARY,
                    condition="article_links_any_entity:gw2:item:mystic_clover",
                    recommendation="Reserve active legendary materials before surplus decisions.",
                    action_type="reserve_for_goal",
                    explanation_template="Reviewed KB policy protects active legendary requirements.",
                    confidence=0.85,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                ),
            )

        explanations = client.get("/api/v1/kb/goals/gw2:goal:aurora/action-explanations")
        report = client.get("/reports/gw2:goal:aurora/markdown/kb")

        assert explanations.status_code == 200
        flattened = [
            item
            for items in explanations.json()["data"]["explanations"].values()
            for item in items
        ]
        assert flattened[0]["rule_name"] == "Reserve legendary materials"
        assert report.status_code == 200
        assert "Knowledge Base Explanations" in report.text
    finally:
        close_database()
        state.reset_cached_graph()
