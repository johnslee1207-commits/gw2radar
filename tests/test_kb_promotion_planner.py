from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.kb.kb_domain_rule_packs import DomainRulePackId
from gw2radar.kb.kb_models import (
    KnowledgeArticleInput,
    KnowledgeContentType,
    KnowledgeDomain,
    KnowledgeReviewStatus,
)
from gw2radar.kb.kb_promotion_planner import (
    build_kb_promotion_plan,
    render_kb_promotion_plan_csv,
    render_kb_promotion_plan_markdown,
)
from gw2radar.kb.kb_repository import create_article, list_articles


def test_kb_promotion_plan_previews_distillable_rules_and_blockers() -> None:
    temp_dir = Path(".test_tmp") / f"kb-promotion-plan-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            create_article(session, _reviewed_rule_article())
            create_article(
                session,
                _reviewed_rule_article().model_copy(
                    update={
                        "title": "Broken action rule",
                        "linked_actions": ["not_an_action"],
                    }
                ),
            )
            articles = list_articles(session, KnowledgeDomain.LEGENDARY)

        plan = build_kb_promotion_plan(
            articles,
            build_mock_graph(),
            domain=KnowledgeDomain.LEGENDARY,
            include_rule_packs=False,
        )
        markdown = render_kb_promotion_plan_markdown(plan)
        csv_text = render_kb_promotion_plan_csv(plan)

        assert plan.schema_version == "gw2radar.kb_promotion_plan.v1"
        assert plan.article_count == 2
        assert plan.distillable_article_count == 1
        assert plan.blocked_article_count == 1
        distillable = next(article for article in plan.articles if article.distillable)
        assert distillable.rule_preview is not None
        assert distillable.rule_preview.enabled is False
        assert any("Invalid linked actions" in blocker for blocker in plan.blockers)
        assert "# KB Promotion Plan" in markdown
        assert "article," in csv_text
    finally:
        close_database()


def test_kb_promotion_plan_api_exports_json_markdown_and_csv() -> None:
    temp_dir = Path(".test_tmp") / f"kb-promotion-plan-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            create_article(session, _reviewed_rule_article())

        response = client.get("/api/v1/kb/promotion-plan?domain=legendary")
        markdown = client.get("/api/v1/kb/promotion-plan/export?domain=legendary")
        csv_response = client.get("/api/v1/kb/promotion-plan/export?domain=legendary&format=csv")
        bad = client.get("/api/v1/kb/promotion-plan/export?format=json")

        assert response.status_code == 200
        plan = response.json()["data"]["plan"]
        assert plan["distillable_article_count"] == 1
        assert plan["rule_packs"] == []
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "KB Promotion Plan" in markdown.text
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"].startswith("text/csv")
        assert "kind,id,title,domain,ready,blockers" in csv_response.text
        assert bad.status_code == 400
    finally:
        close_database()
        state.reset_cached_graph()


def test_kb_promotion_plan_includes_rule_pack_previews() -> None:
    plan = build_kb_promotion_plan([], build_mock_graph(), include_rule_packs=True)

    assert plan.rule_pack_count == len(DomainRulePackId)
    assert plan.importable_rule_pack_count == len(DomainRulePackId)
    assert any(pack.pack_id == "build_upgrade_effects" for pack in plan.rule_packs)
    assert any(pack.pack_id == "market_retention" for pack in plan.rule_packs)
    assert any(pack.pack_id == "guild_privacy_readiness" for pack in plan.rule_packs)
    assert any(pack.pack_id == "creator_signal_safety" for pack in plan.rule_packs)


def _reviewed_rule_article() -> KnowledgeArticleInput:
    return KnowledgeArticleInput(
        title="Legendary hold promotion rule",
        domain=KnowledgeDomain.LEGENDARY,
        content_type=KnowledgeContentType.RULE,
        summary="Hold active legendary goal materials before surplus decisions.",
        body_markdown="Use this rule when active goals require the linked material.",
        linked_entities=["gw2:item:mystic_clover"],
        linked_actions=["hold"],
        confidence=0.85,
        review_status=KnowledgeReviewStatus.REVIEWED,
    )
