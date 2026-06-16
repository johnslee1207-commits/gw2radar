from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import SourceType
from gw2radar.kb.kb_repository import list_sources, register_source
from kb_test_helpers import official_source_input


def test_kb_source_registry_persists_allowed_use_and_policy() -> None:
    temp_dir = Path(".test_tmp") / f"kb-source-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            source = register_source(session, official_source_input())
            sources = list_sources(session)

        assert source.source_type == SourceType.OFFICIAL_API
        assert source.allowed_use == "api_json"
        assert source.crawl_policy == "api_only"
        assert sources[0].source_id == source.source_id
    finally:
        close_database()
