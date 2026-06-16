from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_markdown_loader import load_markdown_directory


def test_kb_domain_seed_directory_has_minimum_domains_and_loads() -> None:
    expected_domains = {"official", "legendary", "returner", "build", "market", "guild", "creator"}
    kb_dir = Path("docs/knowledge_base")
    present = {path.name for path in kb_dir.iterdir() if path.is_dir()}

    assert expected_domains.issubset(present)

    temp_dir = Path(".test_tmp") / f"kb-seed-loader-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            articles = load_markdown_directory(session, kb_dir)

        domains = {article.domain.value for article in articles}
        assert expected_domains.issubset(domains)
        assert len(articles) >= len(expected_domains)
    finally:
        close_database()
