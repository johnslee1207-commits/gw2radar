from pathlib import Path
from uuid import uuid4

from creator_test_helpers import import_returning_player_questions
from gw2radar.commercial.creator_intelligence import build_creator_report, render_creator_report
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_source_attribution_is_preserved_in_report() -> None:
    temp_dir = Path(".test_tmp") / f"creator-source-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            import_returning_player_questions(session)
            markdown = render_creator_report(build_creator_report(session))

        assert "## Source Attribution" in markdown
        assert "https://example.com/forums/returner-gear" in markdown
        assert "https://example.com/r/guildwars2/returner-build" in markdown
        assert "https://wiki.guildwars2.com/wiki/Equipment_acquisition" in markdown
    finally:
        close_database()
