from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_guild_api_create_invite_readiness_report_and_revoke() -> None:
    temp_dir = Path(".test_tmp") / f"guild-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'guild.db'}")
        init_db()
        client = TestClient(app)
        guild = client.post("/api/v1/guilds", json={"name": "Training Guild"})
        guild_id = guild.json()["data"]["guild"]["guild_id"]
        team = client.post("/api/v1/teams", json={"guild_id": guild_id, "name": "Strike Static", "game_mode": "strike"})
        team_id = team.json()["data"]["team"]["team_id"]
        invite = client.post(
            f"/api/v1/teams/{team_id}/members/invite",
            json={
                "user_id": "user_quick",
                "display_name": "Quickness Player",
                "preferred_roles": ["quickness", "dps"],
                "readiness_score": 85,
            },
        )
        member_id = invite.json()["data"]["member"]["member_id"]
        readiness = client.post(f"/api/v1/teams/{team_id}/readiness")
        report = client.get(f"/api/v1/teams/{team_id}/report")
        revoke = client.post(f"/api/v1/teams/{team_id}/members/{member_id}/revoke")

        assert guild.status_code == 200
        assert team.status_code == 200
        assert invite.status_code == 200
        assert readiness.status_code == 200
        assert report.status_code == 200
        assert "Guild Readiness Report" in report.text
        assert revoke.status_code == 200
        assert revoke.json()["data"]["consent"]["granted"] is False
    finally:
        close_database()
