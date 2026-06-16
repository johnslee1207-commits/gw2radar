from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import compute_team_readiness, render_guild_readiness_report
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from guild_test_helpers import create_sample_team


def test_guild_report_contains_privacy_boundary() -> None:
    temp_dir = Path(".test_tmp") / f"guild-report-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _guild, team, _quickness, _healer = create_sample_team(session)
            report = render_guild_readiness_report(compute_team_readiness(session, team.team_id))

        assert "Guild Readiness Report" in report
        assert "Role Coverage" in report
        assert "Privacy-Safe Member Summary" in report
        assert "does not expose raw inventory" in report
    finally:
        close_database()
