import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.config.settings import get_settings
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule


def test_progression_decision_top_k_uses_reviewed_kb_and_preserves_manual_boundary() -> None:
    temp_dir = Path(".test_tmp") / f"progression-decision-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'decision.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        with db_session.SessionLocal() as session:
            create_rule(
                session,
                KnowledgeRuleInput(
                    name="Prioritize short daily route",
                    domain=KnowledgeDomain.LEGENDARY,
                    condition="article_links_any_entity:gw2:task:bitterfrost_daily",
                    recommendation="Prioritize short repeatable routes when they advance the active legendary goal.",
                    action_type="do_daily",
                    priority_delta=0.2,
                    explanation_template="Reviewed route policy favors short manual dailies for time-gated currency.",
                    evidence_refs=["kb:reviewed:daily-route"],
                    confidence=0.9,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                    enabled=True,
                ),
            )
            create_rule(
                session,
                KnowledgeRuleInput(
                    name="Disabled market draft",
                    domain=KnowledgeDomain.MARKET,
                    condition="article_links_any_entity:gw2:item:mystic_clover",
                    recommendation="Draft market note should not influence decisions.",
                    action_type="watch_price",
                    priority_delta=0.7,
                    explanation_template="Disabled draft note.",
                    confidence=0.4,
                    review_status=KnowledgeReviewStatus.DRAFT,
                    enabled=False,
                ),
            )

        response = client.post(
            "/api/v1/progression/decisions/top-k",
            json={"goal_id": "gw2:goal:aurora", "top_k": 3},
        )

        assert response.status_code == 200
        result = response.json()["data"]["decision_result"]
        assert result["schema_version"] == "gw2radar.progression_decision_result.v1"
        assert result["top_k"] == 3
        assert result["returned_candidate_count"] == 3
        assert "automatic trading" in result["deferred_capabilities"]
        assert all(candidate["no_auto_execution"] is True for candidate in result["candidates"])
        assert all("manual player review" in candidate["manual_action_boundary"] for candidate in result["candidates"])

        daily = next(candidate for candidate in result["candidates"] if candidate["action_type"] == "do_daily")
        assert daily["kb_score_delta"] == 0.2
        assert daily["final_score"] >= daily["base_score"]
        assert daily["final_score"] <= 1.0
        assert daily["kb_explanations"][0]["rule_name"] == "Prioritize short daily route"
        assert "kb:reviewed:daily-route" in daily["evidence_refs"]
        assert daily["recommendation_strength"] == "strong_review_candidate"

        combined = str(result).lower()
        assert "disabled market draft" not in combined
        assert "draft market note should not influence decisions" not in combined
        assert "secret-key" not in combined
        assert "guaranteed profit" not in combined
        assert "automatically buy" not in combined
        assert "automatically sell" not in combined
    finally:
        close_database()
        configure_database(get_settings().database_url)
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
