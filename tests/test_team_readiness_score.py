from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import compute_team_readiness
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from guild_test_helpers import create_sample_team


def test_team_readiness_score_combines_member_readiness_and_coverage() -> None:
    temp_dir = Path(".test_tmp") / f"guild-score-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _guild, team, _quickness, _healer = create_sample_team(session)
            result = compute_team_readiness(session, team.team_id)

        assert result.readiness_score > 0
        assert result.readiness_score < 100
    finally:
        close_database()
