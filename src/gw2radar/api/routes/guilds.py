from fastapi import APIRouter, HTTPException, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.commercial.guild_readiness import (
    GuildCreateRequest,
    TeamCreateRequest,
    TeamMemberInviteRequest,
    compute_team_readiness,
    create_guild,
    create_team,
    invite_team_member,
    render_guild_readiness_report,
    revoke_member_consent,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

guild_router = APIRouter(prefix="/api/v1/guilds", tags=["guilds"])
team_router = APIRouter(prefix="/api/v1/teams", tags=["teams"])


@guild_router.post("", response_model=ApiDataEnvelope)
def post_guild(request: GuildCreateRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        guild = create_guild(session, request)
    return ApiDataEnvelope(data={"guild": guild.model_dump(mode="json")})


@team_router.post("", response_model=ApiDataEnvelope)
def post_team(request: TeamCreateRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            team = create_team(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"team": team.model_dump(mode="json")})


@team_router.post("/{team_id}/members/invite", response_model=ApiDataEnvelope)
def post_team_member_invite(team_id: str, request: TeamMemberInviteRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            member, consent = invite_team_member(session, team_id, request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={"member": member.model_dump(mode="json"), "consent": consent.model_dump(mode="json")}
    )


@team_router.post("/{team_id}/readiness", response_model=ApiDataEnvelope)
def post_team_readiness(team_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            readiness = compute_team_readiness(session, team_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"readiness": readiness.model_dump(mode="json")})


@team_router.get("/{team_id}/report")
def get_team_report(team_id: str) -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            readiness = compute_team_readiness(session, team_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=render_guild_readiness_report(readiness),
        media_type="text/markdown; charset=utf-8",
    )


@team_router.post("/{team_id}/members/{member_id}/revoke", response_model=ApiDataEnvelope)
def post_member_revoke(team_id: str, member_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            consent = revoke_member_consent(session, team_id, member_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"consent": consent.model_dump(mode="json")})
