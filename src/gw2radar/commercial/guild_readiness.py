from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import ConsentRecordModel, GuildModel, TeamMemberModel, TeamModel, utc_now


DEFAULT_USER_ID = "local-user"
REQUIRED_ROLES = ["quickness", "alacrity", "healer", "dps"]


class ConsentScope(StrEnum):
    TEAM_READINESS_SUMMARY = "team_readiness_summary"


class GuildCreateRequest(BaseModel):
    name: str
    owner_user_id: str = DEFAULT_USER_ID


class TeamCreateRequest(BaseModel):
    guild_id: str
    name: str
    game_mode: str = "strike"


class TeamMemberInviteRequest(BaseModel):
    user_id: str
    display_name: str
    preferred_roles: list[str] = Field(default_factory=list)
    readiness_score: float = 0.0
    consent_granted: bool = True


class GuildRecord(BaseModel):
    guild_id: str
    owner_user_id: str
    name: str
    created_at: datetime
    updated_at: datetime


class TeamRecord(BaseModel):
    team_id: str
    guild_id: str
    name: str
    game_mode: str
    created_at: datetime
    updated_at: datetime


class TeamMemberRecord(BaseModel):
    member_id: str
    team_id: str
    user_id: str
    display_name: str
    preferred_roles: list[str]
    readiness_score: float
    created_at: datetime
    updated_at: datetime


class ConsentRecord(BaseModel):
    consent_id: str
    team_id: str
    member_id: str
    consent_scope: ConsentScope
    granted: bool
    granted_at: datetime
    revoked_at: datetime | None = None


class RoleCoverage(BaseModel):
    role: str
    covered: bool
    member_count: int


class MemberReadinessSummary(BaseModel):
    member_id: str
    display_name: str
    preferred_roles: list[str]
    readiness_band: str
    consent_granted: bool


class TeamReadinessResult(BaseModel):
    team: TeamRecord
    role_coverage: list[RoleCoverage]
    readiness_score: float
    member_summaries: list[MemberReadinessSummary]
    missing_roles: list[str]
    privacy_boundary: str = "summary_only_no_raw_inventory_or_private_payload"


def create_guild(session: Session, request: GuildCreateRequest) -> GuildRecord:
    row = GuildModel(
        guild_id=f"guild_{uuid4().hex}",
        owner_user_id=request.owner_user_id,
        name=request.name,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _guild_from_model(row)


def create_team(session: Session, request: TeamCreateRequest) -> TeamRecord:
    if session.get(GuildModel, request.guild_id) is None:
        raise ValueError("Guild not found.")
    row = TeamModel(
        team_id=f"team_{uuid4().hex}",
        guild_id=request.guild_id,
        name=request.name,
        game_mode=request.game_mode,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _team_from_model(row)


def invite_team_member(session: Session, team_id: str, request: TeamMemberInviteRequest) -> tuple[TeamMemberRecord, ConsentRecord]:
    if session.get(TeamModel, team_id) is None:
        raise ValueError("Team not found.")
    member = TeamMemberModel(
        member_id=f"member_{uuid4().hex}",
        team_id=team_id,
        user_id=request.user_id,
        display_name=request.display_name,
        preferred_roles_json=request.preferred_roles,
        readiness_score=request.readiness_score,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(member)
    session.flush()
    consent = ConsentRecordModel(
        consent_id=f"consent_{uuid4().hex}",
        team_id=team_id,
        member_id=member.member_id,
        consent_scope=ConsentScope.TEAM_READINESS_SUMMARY.value,
        granted=request.consent_granted,
        granted_at=utc_now(),
    )
    session.add(consent)
    session.commit()
    return _member_from_model(member), _consent_from_model(consent)


def revoke_member_consent(session: Session, team_id: str, member_id: str) -> ConsentRecord:
    consent = _consent_for_member(session, team_id, member_id)
    if consent is None:
        raise ValueError("Consent record not found.")
    consent.granted = False
    consent.revoked_at = utc_now()
    session.commit()
    return _consent_from_model(consent)


def compute_team_readiness(session: Session, team_id: str) -> TeamReadinessResult:
    team = session.get(TeamModel, team_id)
    if team is None:
        raise ValueError("Team not found.")
    members = session.query(TeamMemberModel).filter(TeamMemberModel.team_id == team_id).order_by(TeamMemberModel.display_name).all()
    consenting = [member for member in members if _has_active_consent(session, team_id, member.member_id)]
    coverage = _role_coverage(consenting)
    summaries = [_summary_for_member(session, team_id, member) for member in members]
    missing = [item.role for item in coverage if not item.covered]
    readiness = (
        sum(member.readiness_score for member in consenting) / len(consenting)
        if consenting
        else 0.0
    )
    coverage_ratio = sum(1 for item in coverage if item.covered) / len(coverage)
    score = round((readiness * 0.65) + (coverage_ratio * 100 * 0.35), 2)
    return TeamReadinessResult(
        team=_team_from_model(team),
        role_coverage=coverage,
        readiness_score=score,
        member_summaries=summaries,
        missing_roles=missing,
    )


def render_guild_readiness_report(result: TeamReadinessResult) -> str:
    lines = [
        "# Guild Readiness Report",
        "",
        f"Team: {result.team.name}",
        f"Mode: {result.team.game_mode}",
        f"Readiness score: {result.readiness_score:.2f}",
        "",
        "## Role Coverage",
        *[f"- {role.role}: {'covered' if role.covered else 'missing'} ({role.member_count} members)" for role in result.role_coverage],
        "",
        "## Privacy-Safe Member Summary",
        *[
            f"- {member.display_name}: {member.readiness_band}, roles={', '.join(member.preferred_roles) or 'none'}, consent={str(member.consent_granted).lower()}"
            for member in result.member_summaries
        ],
        "",
        "## Training Suggestions",
        *([f"- Train or recruit for {role} coverage." for role in result.missing_roles] or ["- Coverage baseline is met; focus on practice consistency."]),
        "",
        "## Privacy Boundary",
        "- This report shows summary readiness only.",
        "- It does not expose raw inventory, bank, API keys, or private account payloads.",
        "- Members can revoke consent and then disappear from readiness calculations.",
    ]
    return "\n".join(lines) + "\n"


def _role_coverage(members: list[TeamMemberModel]) -> list[RoleCoverage]:
    rows: list[RoleCoverage] = []
    for role in REQUIRED_ROLES:
        count = sum(1 for member in members if role in member.preferred_roles_json)
        rows.append(RoleCoverage(role=role, covered=count > 0, member_count=count))
    return rows


def _summary_for_member(session: Session, team_id: str, member: TeamMemberModel) -> MemberReadinessSummary:
    consent = _has_active_consent(session, team_id, member.member_id)
    score = member.readiness_score if consent else 0.0
    return MemberReadinessSummary(
        member_id=member.member_id,
        display_name=member.display_name,
        preferred_roles=member.preferred_roles_json if consent else [],
        readiness_band=_readiness_band(score),
        consent_granted=consent,
    )


def _readiness_band(score: float) -> str:
    if score >= 80:
        return "ready"
    if score >= 50:
        return "needs_practice"
    return "not_ready"


def _has_active_consent(session: Session, team_id: str, member_id: str) -> bool:
    consent = _consent_for_member(session, team_id, member_id)
    return bool(consent and consent.granted and consent.revoked_at is None)


def _consent_for_member(session: Session, team_id: str, member_id: str) -> ConsentRecordModel | None:
    return (
        session.query(ConsentRecordModel)
        .filter(ConsentRecordModel.team_id == team_id, ConsentRecordModel.member_id == member_id)
        .order_by(ConsentRecordModel.granted_at.desc())
        .first()
    )


def _guild_from_model(row: GuildModel) -> GuildRecord:
    return GuildRecord(
        guild_id=row.guild_id,
        owner_user_id=row.owner_user_id,
        name=row.name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _team_from_model(row: TeamModel) -> TeamRecord:
    return TeamRecord(
        team_id=row.team_id,
        guild_id=row.guild_id,
        name=row.name,
        game_mode=row.game_mode,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _member_from_model(row: TeamMemberModel) -> TeamMemberRecord:
    return TeamMemberRecord(
        member_id=row.member_id,
        team_id=row.team_id,
        user_id=row.user_id,
        display_name=row.display_name,
        preferred_roles=row.preferred_roles_json,
        readiness_score=row.readiness_score,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _consent_from_model(row: ConsentRecordModel) -> ConsentRecord:
    return ConsentRecord(
        consent_id=row.consent_id,
        team_id=row.team_id,
        member_id=row.member_id,
        consent_scope=ConsentScope(row.consent_scope),
        granted=row.granted,
        granted_at=row.granted_at,
        revoked_at=row.revoked_at,
    )
