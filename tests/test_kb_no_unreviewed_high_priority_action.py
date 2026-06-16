import pytest

from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput


def test_unreviewed_kb_rule_cannot_drive_high_priority_action() -> None:
    with pytest.raises(ValueError, match="Unreviewed KB rules"):
        KnowledgeRuleInput(
            name="Unsafe high priority market rule",
            domain=KnowledgeDomain.MARKET,
            condition="material appears expensive",
            recommendation="Escalate action priority from an unreviewed note.",
            action_type="watch_price",
            priority_delta=0.8,
            explanation_template="Unreviewed market rule.",
            review_status=KnowledgeReviewStatus.DRAFT,
        )
