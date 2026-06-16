from pathlib import Path
from uuid import uuid4

from creator_test_helpers import import_returning_player_questions
from gw2radar.commercial.creator_intelligence import cluster_questions, find_guide_gaps
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_question_cluster_and_guide_gap_use_repeated_questions() -> None:
    temp_dir = Path(".test_tmp") / f"creator-gap-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            import_returning_player_questions(session)
            clusters = cluster_questions(session)
            gaps = find_guide_gaps(session)

        assert clusters[0].topic == "returner gearing"
        assert clusters[0].question_count == 2
        assert gaps[0].topic == "returner gearing"
        assert gaps[0].audience_segment == "returning_player"
        assert len(gaps[0].supporting_signal_ids) == 3
    finally:
        close_database()
