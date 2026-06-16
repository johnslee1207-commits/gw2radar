from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.kb.kb_explanation import explain_actions_with_kb
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from pathlib import Path
from uuid import uuid4


def test_kb_explanation_matches_reviewed_rule_by_action_and_entity() -> None:
    temp_dir = Path(".test_tmp") / f"kb-explain-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        graph = build_mock_graph()
        actions = generate_actions(graph, "gw2:goal:aurora")
        with db_session.SessionLocal() as session:
            rule = create_rule(
                session,
                KnowledgeRuleInput(
                    name="Reserve legendary materials",
                    domain=KnowledgeDomain.LEGENDARY,
                    condition="article_links_any_entity:gw2:item:mystic_clover",
                    recommendation="Reserve active legendary materials before surplus decisions.",
                    action_type="reserve_for_goal",
                    priority_delta=0.2,
                    explanation_template="Reviewed KB policy protects active legendary requirements.",
                    confidence=0.85,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                    enabled=True,
                ),
            )
        explanations = explain_actions_with_kb(actions, [rule])
        matched = [item for items in explanations.values() for item in items]

        assert len(matched) == 1
        assert matched[0].rule_name == "Reserve legendary materials"
        assert matched[0].action_id.endswith("gw2:item:mystic_clover")
    finally:
        close_database()
