from pathlib import Path
from uuid import uuid4

from creator_test_helpers import import_returning_player_questions
from gw2radar.commercial.creator_intelligence import calculate_topic_trends
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_topic_trend_groups_signals_with_attributed_sources() -> None:
    temp_dir = Path(".test_tmp") / f"creator-topic-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            import_returning_player_questions(session)
            trends = calculate_topic_trends(session)

        trend = trends[0]
        assert trend.topic == "returner gearing"
        assert trend.signal_count == 3
        assert "https://example.com/forums/returner-gear" in trend.source_urls
        assert trend.confidence_note == "verified source present"
    finally:
        close_database()
