from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import (
    KnowledgeArticleInput,
    KnowledgeContentType,
    KnowledgeDomain,
    KnowledgeReviewStatus,
)
from gw2radar.kb.kb_repository import create_article
from gw2radar.kb.kb_rule_distiller import distill_rule_from_article


def reviewed_rule_article() -> KnowledgeArticleInput:
    return KnowledgeArticleInput(
        title="Do not sell legendary materials",
        domain=KnowledgeDomain.LEGENDARY,
        content_type=KnowledgeContentType.RULE,
        summary="Reserve active legendary goal materials before sell decisions.",
        body_markdown="Use this explanation in reports when active goals require the material.",
        linked_entities=["gw2:item:mystic_clover"],
        linked_actions=["hold"],
        confidence=0.85,
        review_status=KnowledgeReviewStatus.REVIEWED,
    )


def test_kb_rule_distiller_creates_rule_from_reviewed_rule_article() -> None:
    temp_dir = Path(".test_tmp") / f"kb-distill-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            article = create_article(session, reviewed_rule_article())
            rule = distill_rule_from_article(session, article)

        assert rule.name == "Do not sell legendary materials"
        assert rule.action_type == "hold"
        assert rule.review_status == KnowledgeReviewStatus.REVIEWED
        assert rule.priority_delta == 0.2
    finally:
        close_database()


def test_kb_rule_distiller_rejects_unreviewed_rule_article() -> None:
    temp_dir = Path(".test_tmp") / f"kb-distill-draft-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        draft = reviewed_rule_article().model_copy(update={"review_status": KnowledgeReviewStatus.DRAFT})
        with db_session.SessionLocal() as session:
            article = create_article(session, draft)
            with pytest.raises(ValueError, match="Only reviewed"):
                distill_rule_from_article(session, article)
    finally:
        close_database()
