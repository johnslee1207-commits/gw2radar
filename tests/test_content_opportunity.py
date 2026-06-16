from pathlib import Path
from uuid import uuid4

from creator_test_helpers import import_returning_player_questions
from gw2radar.commercial.creator_intelligence import find_content_opportunities
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_content_opportunity_keeps_sources_and_supporting_signal_ids() -> None:
    temp_dir = Path(".test_tmp") / f"creator-opportunity-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            import_returning_player_questions(session)
            opportunities = find_content_opportunities(session)

        opportunity = opportunities[0]
        assert opportunity.topic == "returner gearing"
        assert opportunity.recommended_format == "beginner guide"
        assert "https://wiki.guildwars2.com/wiki/Equipment_acquisition" in opportunity.source_urls
        assert len(opportunity.supporting_signal_ids) == 3
    finally:
        close_database()
