from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeReviewStatus
from gw2radar.kb.kb_repository import deprecate_article, review_article
from kb_test_helpers import create_sample_kb_article


def test_kb_review_and_deprecate_status_transitions() -> None:
    temp_dir = Path(".test_tmp") / f"kb-review-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _, article = create_sample_kb_article(session)
            reviewed = review_article(session, article.kb_id)
            deprecated = deprecate_article(session, article.kb_id)

        assert reviewed.review_status == KnowledgeReviewStatus.REVIEWED
        assert reviewed.last_reviewed_at is not None
        assert deprecated.review_status == KnowledgeReviewStatus.DEPRECATED
    finally:
        close_database()
