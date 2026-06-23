from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.commercial.growth import DEFAULT_USER_ID, ensure_growth_defaults
from gw2radar.db.models import ReportExportJobModel, SubscriptionModel, utc_now


class WeeklyReportStatus(StrEnum):
    READY = "ready"
    NEEDS_REPORT_HISTORY = "needs_report_history"


class MockEmailStatus(StrEnum):
    QUEUED_MOCK = "queued_mock"


class ReportHistoryEntry(BaseModel):
    job_id: str
    report_type: str
    export_format: str
    status: str
    artifact_name: str | None = None
    manifest_name: str | None = None
    created_at: datetime
    updated_at: datetime


class WeeklyReportRequest(BaseModel):
    user_id: str = DEFAULT_USER_ID
    focus: str = "account_planning"
    include_share_preview: bool = True


class WeeklyReportJob(BaseModel):
    job_id: str
    user_id: str
    status: WeeklyReportStatus
    focus: str
    generated_at: datetime
    summary_markdown: str
    history_count: int
    safety_boundaries: list[str]
    assumptions: list[str]


class SafeSharePreview(BaseModel):
    user_id: str
    title: str
    summary: str
    public_url: str | None = None
    contains_private_payload: bool = False
    contains_raw_secret: bool = False
    artifact_names: list[str] = Field(default_factory=list)
    omitted_fields: list[str] = Field(default_factory=list)
    review_required: bool = True


class MockEmailRequest(BaseModel):
    user_id: str = DEFAULT_USER_ID
    recipient_label: str = "player"
    subject: str = "Your GW2Radar weekly planning summary is ready"
    include_share_preview: bool = True


class MockEmailDelivery(BaseModel):
    delivery_id: str
    provider: str = "mock_email"
    status: MockEmailStatus
    user_id: str
    recipient_label: str
    subject: str
    real_provider_used: bool = False
    contains_private_payload: bool = False
    contains_raw_secret: bool = False
    queued_at: datetime
    preview: SafeSharePreview | None = None


class RetentionStatus(BaseModel):
    user_id: str
    active_subscription_count: int
    report_history_count: int
    unsubscribe_available: bool = True
    unsubscribe_path: str = "/api/v1/growth/retention/unsubscribe"
    private_data_delete_path: str = "/api/v1/security/private-data"
    real_email_provider_locked: bool = False
    safety_boundaries: list[str]


def build_report_history(session: Session, user_id: str = DEFAULT_USER_ID, limit: int = 10) -> list[ReportHistoryEntry]:
    ensure_growth_defaults(session)
    rows = (
        session.query(ReportExportJobModel)
        .filter(ReportExportJobModel.user_id == user_id)
        .order_by(ReportExportJobModel.created_at.desc(), ReportExportJobModel.job_id.desc())
        .limit(limit)
        .all()
    )
    return [_history_entry_from_model(row) for row in rows]


def build_weekly_report_job(session: Session, request: WeeklyReportRequest) -> WeeklyReportJob:
    history = build_report_history(session, request.user_id, limit=5)
    status = WeeklyReportStatus.READY if history else WeeklyReportStatus.NEEDS_REPORT_HISTORY
    generated_at = utc_now()
    latest_lines = [
        f"- {entry.report_type} ({entry.status}) via {entry.export_format}"
        for entry in history[:3]
    ] or ["- No completed report history yet; generate a planning report first."]
    summary = "\n".join(
        [
            "# Weekly GW2Radar Planning Summary",
            "",
            f"- Focus: {request.focus}",
            f"- Status: {status.value}",
            f"- Report history entries considered: {len(history)}",
            "",
            "## Recent report signals",
            *latest_lines,
            "",
            "## Safety boundary",
            "This summary supports manual player review only. It does not promise completion, returns, or trading outcomes.",
        ]
    )
    return WeeklyReportJob(
        job_id=f"weekly_{generated_at.strftime('%Y%m%d%H%M%S')}_{request.user_id}",
        user_id=request.user_id,
        status=status,
        focus=request.focus,
        generated_at=generated_at,
        summary_markdown=summary,
        history_count=len(history),
        safety_boundaries=[
            "manual review only",
            "no automatic gameplay actions",
            "no automatic trading instructions",
            "no private payload sharing",
        ],
        assumptions=["Report history is local metadata; missing report content is treated as unavailable."],
    )


def build_safe_share_preview(session: Session, user_id: str = DEFAULT_USER_ID) -> SafeSharePreview:
    history = build_report_history(session, user_id, limit=5)
    artifact_names = [entry.artifact_name for entry in history if entry.artifact_name]
    return SafeSharePreview(
        user_id=user_id,
        title="GW2Radar planning progress preview",
        summary=f"{len(history)} local report metadata entries are available for manual review.",
        public_url=None,
        artifact_names=artifact_names,
        omitted_fields=[
            "raw credential values",
            "private account payloads",
            "local artifact paths",
            "report body contents",
        ],
        review_required=True,
    )


def queue_mock_email_delivery(session: Session, request: MockEmailRequest) -> MockEmailDelivery:
    preview = build_safe_share_preview(session, request.user_id) if request.include_share_preview else None
    queued_at = utc_now()
    return MockEmailDelivery(
        delivery_id=f"mock_email_{queued_at.strftime('%Y%m%d%H%M%S')}_{request.user_id}",
        status=MockEmailStatus.QUEUED_MOCK,
        user_id=request.user_id,
        recipient_label=request.recipient_label,
        subject=request.subject,
        queued_at=queued_at,
        preview=preview,
    )


def build_retention_status(session: Session, user_id: str = DEFAULT_USER_ID) -> RetentionStatus:
    ensure_growth_defaults(session)
    active_subscriptions = (
        session.query(SubscriptionModel)
        .filter(SubscriptionModel.user_id == user_id, SubscriptionModel.status == "active")
        .count()
    )
    history_count = (
        session.query(ReportExportJobModel)
        .filter(ReportExportJobModel.user_id == user_id)
        .count()
    )
    return RetentionStatus(
        user_id=user_id,
        active_subscription_count=active_subscriptions,
        report_history_count=history_count,
        safety_boundaries=[
            "mock email only until a provider is explicitly configured",
            "unsubscribe and private-data deletion paths are visible",
            "safe share previews omit report bodies and private payloads",
        ],
    )


def _history_entry_from_model(row: ReportExportJobModel) -> ReportHistoryEntry:
    return ReportHistoryEntry(
        job_id=row.job_id,
        report_type=row.report_type,
        export_format=row.export_format,
        status=row.status,
        artifact_name=_name_only(row.artifact_path),
        manifest_name=_name_only(row.manifest_path),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _name_only(path: str | None) -> str | None:
    if not path:
        return None
    return Path(path).name
