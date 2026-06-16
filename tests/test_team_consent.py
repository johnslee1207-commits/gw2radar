from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.guild_readiness import ConsentScope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from guild_test_helpers import create_sample_team


def test_team_member_invite_records_consent() -> None:
    temp_dir = Path(".test_tmp") / f"guild-consent-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            _guild, _team, quickness, _healer = create_sample_team(session)
            from gw2radar.commercial.guild_readiness import _consent_for_member
            consent = _consent_for_member(session, quickness.team_id, quickness.member_id)

        assert consent is not None
        assert consent.granted is True
        assert consent.consent_scope == ConsentScope.TEAM_READINESS_SUMMARY.value
    finally:
        close_database()
