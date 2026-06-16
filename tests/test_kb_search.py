from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain
from gw2radar.kb.kb_repository import deprecate_article, search_articles
from kb_test_helpers import create_sample_kb_article


def test_kb_search_matches_title_summary_body_and_links() -> None:
    temp_dir = Path(".test_tmp") / f"kb-search-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _, article = create_sample_kb_article(session)
            by_entity = search_articles(session, "mystic_clover", KnowledgeDomain.LEGENDARY)
            by_body = search_articles(session, "acquisition advice", KnowledgeDomain.LEGENDARY)
            deprecate_article(session, article.kb_id)
            hidden = search_articles(session, "Mystic Clover", KnowledgeDomain.LEGENDARY)
            included = search_articles(session, "Mystic Clover", KnowledgeDomain.LEGENDARY, include_deprecated=True)

        assert by_entity[0].kb_id == article.kb_id
        assert by_body[0].kb_id == article.kb_id
        assert hidden == []
        assert included[0].kb_id == article.kb_id
    finally:
        close_database()
