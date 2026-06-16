from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import compute_team_readiness, revoke_member_consent
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from guild_test_helpers import create_sample_team


def test_member_privacy_summary_hides_roles_after_revoke() -> None:
    temp_dir = Path(".test_tmp") / f"guild-privacy-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _guild, team, quickness, _healer = create_sample_team(session)
            revoke_member_consent(session, team.team_id, quickness.member_id)
            result = compute_team_readiness(session, team.team_id)

        summary = next(item for item in result.member_summaries if item.member_id == quickness.member_id)
        assert summary.consent_granted is False
        assert summary.preferred_roles == []
        assert summary.readiness_band == "not_ready"
    finally:
        close_database()
