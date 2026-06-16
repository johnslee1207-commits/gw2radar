from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule, list_rules


def test_kb_rule_requires_review_for_high_priority_delta() -> None:
    with pytest.raises(ValueError, match="Unreviewed KB rules"):
        KnowledgeRuleInput(
            name="Returner mobility first",
            domain=KnowledgeDomain.RETURNER,
            condition="travel_readiness_score < 0.5",
            recommendation="Prioritize mobility recovery before advanced goals.",
            action_type="complete_achievement",
            priority_delta=0.9,
            explanation_template="Recover basic movement first.",
            review_status=KnowledgeReviewStatus.DRAFT,
        )


def test_kb_rule_persists_reviewed_rule() -> None:
    temp_dir = Path(".test_tmp") / f"kb-rule-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            rule = create_rule(
                session,
                KnowledgeRuleInput(
                    name="Returner mobility first",
                    domain=KnowledgeDomain.RETURNER,
                    condition="travel_readiness_score < 0.5",
                    recommendation="Prioritize mobility recovery before advanced goals.",
                    action_type="complete_achievement",
                    priority_delta=0.9,
                    explanation_template="Recover basic movement first.",
                    review_status=KnowledgeReviewStatus.REVIEWED,
                ),
            )
            rules = list_rules(session, KnowledgeDomain.RETURNER)

        assert rule.rule_id == rules[0].rule_id
        assert rules[0].enabled is True
    finally:
        close_database()
