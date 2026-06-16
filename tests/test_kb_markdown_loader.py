from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_markdown_loader import load_markdown_article
from gw2radar.kb.kb_repository import register_source
from kb_test_helpers import official_source_input


def test_kb_markdown_loader_imports_front_matter_article() -> None:
    temp_dir = Path(".test_tmp") / f"kb-loader-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            source = register_source(session, official_source_input())
            md_path = temp_dir / "mystic_clover.md"
            md_path.write_text(
                "\n".join(
                    [
                        "---",
                        "title: Mystic Clover planning note",
                        "domain: legendary",
                        "content_type: summary",
                        "summary: Mystic Clover planning needs reviewed source-linked explanation.",
                        f"source_refs: {source.source_id}",
                        "linked_entities: gw2:item:mystic_clover",
                        "linked_actions: do_daily",
                        "confidence: 0.8",
                        "review_status: draft",
                        "---",
                        "Use concise local notes and source links only.",
                    ]
                ),
                encoding="utf-8",
            )
            article = load_markdown_article(session, md_path)

        assert article.title == "Mystic Clover planning note"
        assert article.source_refs == [source.source_id]
        assert article.linked_entities == ["gw2:item:mystic_clover"]
    finally:
        close_database()


def test_kb_markdown_loader_rejects_non_markdown_files() -> None:
    temp_dir = Path(".test_tmp") / f"kb-loader-bad-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    path = temp_dir / "unsafe.txt"
    path.write_text("not markdown", encoding="utf-8")

    with pytest.raises(ValueError, match="Markdown"):
        with db_session.SessionLocal() as session:
            load_markdown_article(session, path)
