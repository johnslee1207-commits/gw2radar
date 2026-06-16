from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule
from gw2radar.reports.markdown_report import generate_kb_backed_markdown_report


def test_kb_backed_report_appends_reviewed_explanation_section() -> None:
    temp_dir = Path(".test_tmp") / f"kb-report-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            rule = create_rule(
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
        markdown = generate_kb_backed_markdown_report(graph, "gw2:goal:aurora", [rule])

        assert "## Knowledge Base Explanations" in markdown
        assert "Reserve legendary materials" in markdown
        assert "KB explanations are applied only from reviewed and enabled rules" in markdown
    finally:
        close_database()
