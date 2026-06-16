from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeChunkInput
from gw2radar.kb.kb_repository import create_chunk
from kb_test_helpers import create_sample_kb_article


def test_kb_chunk_preserves_entity_action_and_source_links() -> None:
    temp_dir = Path(".test_tmp") / f"kb-chunk-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            source, article = create_sample_kb_article(session)
            chunk = create_chunk(
                session,
                KnowledgeChunkInput(
                    kb_id=article.kb_id,
                    text="Mystic Clover planning should link to entity and daily action guidance.",
                    token_count=10,
                    linked_entities=["gw2:item:mystic_clover"],
                    linked_actions=["do_daily"],
                    source_refs=[source.source_id],
                    confidence=0.8,
                ),
            )

        assert chunk.linked_entities == ["gw2:item:mystic_clover"]
        assert chunk.linked_actions == ["do_daily"]
        assert chunk.source_refs == [source.source_id]
    finally:
        close_database()
