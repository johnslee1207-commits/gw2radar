from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_markdown_loader import load_markdown_directory


def test_kb_directory_loader_imports_markdown_articles_and_skips_registry_docs() -> None:
    temp_dir = Path(".test_tmp") / f"kb-dir-loader-{uuid4().hex}"
    kb_dir = temp_dir / "knowledge_base"
    (kb_dir / "returner").mkdir(parents=True, exist_ok=True)
    (kb_dir / "source_registry").mkdir(parents=True, exist_ok=True)
    (kb_dir / "source_registry" / "official_sources.md").write_text("# Registry doc without front matter", encoding="utf-8")
    (kb_dir / "returner" / "returner_note.md").write_text(
        "\n".join(
            [
                "---",
                "title: Returner note",
                "domain: returner",
                "content_type: summary",
                "summary: Returning players need concise recovery guidance.",
                "confidence: 0.7",
                "review_status: draft",
                "---",
                "Local summary only.",
            ]
        ),
        encoding="utf-8",
    )
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            articles = load_markdown_directory(session, kb_dir)

        assert len(articles) == 1
        assert articles[0].title == "Returner note"
    finally:
        close_database()
