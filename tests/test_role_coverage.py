from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import compute_team_readiness
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from guild_test_helpers import create_sample_team


def test_role_coverage_detects_missing_alacrity() -> None:
    temp_dir = Path(".test_tmp") / f"guild-coverage-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _guild, team, _quickness, _healer = create_sample_team(session)
            result = compute_team_readiness(session, team.team_id)

        by_role = {row.role: row for row in result.role_coverage}
        assert by_role["quickness"].covered is True
        assert by_role["healer"].covered is True
        assert by_role["alacrity"].covered is False
        assert "alacrity" in result.missing_roles
    finally:
        close_database()
