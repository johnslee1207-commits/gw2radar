from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain
from gw2radar.kb.kb_repository import create_article, get_article, list_articles
from kb_test_helpers import create_sample_kb_article, legendary_article_input


def test_kb_repository_creates_and_lists_articles_by_domain() -> None:
    temp_dir = Path(".test_tmp") / f"kb-repo-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            source, article = create_sample_kb_article(session)
            loaded = get_article(session, article.kb_id)
            articles = list_articles(session, KnowledgeDomain.LEGENDARY)

        assert source.source_id in article.source_refs
        assert loaded is not None
        assert loaded.kb_id == article.kb_id
        assert articles[0].title == "Mystic Clover source summary"
    finally:
        close_database()


def test_kb_repository_rejects_unknown_source_refs() -> None:
    temp_dir = Path(".test_tmp") / f"kb-missing-source-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            with pytest.raises(ValueError, match="Knowledge source not found"):
                create_article(session, legendary_article_input("missing-source"))
    finally:
        close_database()
