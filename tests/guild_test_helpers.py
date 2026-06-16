from gw2radar.commercial.guild_readiness import (
    GuildCreateRequest,
    TeamCreateRequest,
    TeamMemberInviteRequest,
    create_guild,
    create_team,
    invite_team_member,
)


def create_sample_team(session):
    guild = create_guild(session, GuildCreateRequest(name="Training Guild"))
    team = create_team(session, TeamCreateRequest(guild_id=guild.guild_id, name="Strike Static", game_mode="strike"))
    quickness, _ = invite_team_member(
        session,
        team.team_id,
        TeamMemberInviteRequest(
            user_id="user_quick",
            display_name="Quickness Player",
            preferred_roles=["quickness", "dps"],
            readiness_score=82,
        ),
    )
    healer, _ = invite_team_member(
        session,
        team.team_id,
        TeamMemberInviteRequest(
            user_id="user_heal",
            display_name="Healer Player",
            preferred_roles=["healer"],
            readiness_score=74,
        ),
    )
    return guild, team, quickness, healer
