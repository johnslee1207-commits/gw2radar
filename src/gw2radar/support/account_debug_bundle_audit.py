from __future__ import annotations

import re
from csv import DictWriter
from datetime import datetime
from io import StringIO
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.db.models import SupportReviewAuditModel
from gw2radar.support.account_debug_bundle_review import SupportReviewReport


API_KEY_SHAPED_PATTERN = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){4,}-[0-9a-fA-F]{12,}")
LONG_SECRET_PATTERN = re.compile(r"[A-Za-z0-9_=-]{48,}")
SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}


class SupportReviewAuditRecord(BaseModel):
    case_id: str
    bundle_schema_version: str | None = None
    review_schema_version: str
    overall_status: str
    summary: str
    highest_severity: str
    finding_count: int
    finding_ids: list[str] = Field(default_factory=list)
    reviewer: str
    source: str
    reply_template_summary: str
    properties: dict = Field(default_factory=dict)
    created_at: datetime


class SupportReviewMetricCount(BaseModel):
    key: str
    count: int


class SupportReviewMetricsSummary(BaseModel):
    schema_version: str = "gw2radar.account_debug_bundle_review_metrics.v1"
    total_records: int
    status_counts: list[SupportReviewMetricCount] = Field(default_factory=list)
    severity_counts: list[SupportReviewMetricCount] = Field(default_factory=list)
    finding_counts: list[SupportReviewMetricCount] = Field(default_factory=list)
    top_blockers: list[SupportReviewMetricCount] = Field(default_factory=list)
    trend_summary: str
    boundary: str = "Metrics are aggregated from privacy-safe audit metadata only; raw bundles and raw API keys are not read."


class SupportReviewPlaybookItem(BaseModel):
    blocker_id: str
    title: str
    support_steps: list[str] = Field(default_factory=list)
    player_reply_template: str
    product_fix_suggestion: str
    priority: str
    evidence_needed: list[str] = Field(default_factory=list)


class SupportReviewPlaybookSummary(BaseModel):
    schema_version: str = "gw2radar.account_debug_bundle_review_playbook.v1"
    total_records: int
    plays: list[SupportReviewPlaybookItem] = Field(default_factory=list)
    unmapped_blockers: list[str] = Field(default_factory=list)
    summary: str
    boundary: str = "Playbooks are derived from privacy-safe audit metadata and never require raw API keys or private account payloads."


class SupportReviewBacklogItem(BaseModel):
    backlog_id: str
    blocker_id: str
    title: str
    priority: str
    affected_cases: int
    product_fix_suggestion: str
    support_signal: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class SupportReviewBacklogSummary(BaseModel):
    schema_version: str = "gw2radar.account_debug_bundle_review_backlog.v1"
    total_records: int
    backlog_items: list[SupportReviewBacklogItem] = Field(default_factory=list)
    summary: str
    boundary: str = "Backlog items are generated from aggregated privacy-safe support metadata only."


PLAYBOOKS: dict[str, SupportReviewPlaybookItem] = {
    "needs_key": SupportReviewPlaybookItem(
        blocker_id="needs_key",
        title="API key is not connected",
        support_steps=[
            "Confirm the player is on the Connect page.",
            "Ask them to paste a read-only GW2 API key and save it.",
            "Ask them to run connection diagnostic again after saving.",
        ],
        player_reply_template="GW2Radar does not currently see a saved GW2 API key. Please paste a read-only key on Connect, save it, then run the connection diagnostic again. Do not send the raw key to support.",
        product_fix_suggestion="Keep the key input visible after failed diagnostics and surface the Paste key fix action near the failed check.",
        priority="P0",
        evidence_needed=["key_status.is_configured", "diagnostic_summary.checks.api_key_stored"],
    ),
    "needs_permissions": SupportReviewPlaybookItem(
        blocker_id="needs_permissions",
        title="Required GW2 API permissions are missing",
        support_steps=[
            "Confirm the missing required permissions named in the review.",
            "Ask the player to regenerate or update the GW2 API key with those scopes.",
            "Ask them to save the key again and resync.",
        ],
        player_reply_template="Your key is saved, but it is missing required permissions. Please create or update the key with the permissions named in GW2Radar, save it again, and resync. Do not send the raw key to support.",
        product_fix_suggestion="Add a one-click copy list for missing required scopes and keep limited-mode feature impact visible.",
        priority="P0",
        evidence_needed=["permission_summary.missing_required_permissions", "diagnostic_summary.checks.permissions_ready"],
    ),
    "sync_delayed": SupportReviewPlaybookItem(
        blocker_id="sync_delayed",
        title="Sync is delayed or waiting for retry",
        support_steps=[
            "Check endpoint progress for delayed or retry-scheduled work.",
            "Ask the player to wait for the retry window or run drain-one in local development.",
            "Re-run diagnostic after the queue advances.",
        ],
        player_reply_template="Your account sync appears delayed or waiting for retry. Please wait for the retry window, then run Sync again. In local development, run drain-one after queueing the job.",
        product_fix_suggestion="Expose retry-after timing and endpoint-specific delay reasons in the Connect progress view.",
        priority="P1",
        evidence_needed=["sync_summary.counts", "sync_summary.endpoint_progress"],
    ),
    "needs_sync": SupportReviewPlaybookItem(
        blocker_id="needs_sync",
        title="No sync job is visible",
        support_steps=[
            "Confirm key and permissions are ready.",
            "Ask the player to click Sync now.",
            "Refresh sync status and diagnostic after queueing.",
        ],
        player_reply_template="Your key looks connected, but no account sync job is visible yet. Please click Sync now, then run the connection diagnostic again.",
        product_fix_suggestion="Make Sync now the primary fix action when queue history is empty.",
        priority="P1",
        evidence_needed=["diagnostic_summary.checks.sync_job_visible"],
    ),
    "needs_drain": SupportReviewPlaybookItem(
        blocker_id="needs_drain",
        title="Private account snapshot was not written",
        support_steps=[
            "Confirm a sync job was queued.",
            "Ask local developers to run drain-one, or ask players to wait for the worker.",
            "Verify private player-state count after the worker finishes.",
        ],
        player_reply_template="A sync job is visible, but the private account snapshot has not been written yet. Please wait for the worker to finish, then run the diagnostic again.",
        product_fix_suggestion="Show worker status and private snapshot write confirmation beside endpoint progress.",
        priority="P1",
        evidence_needed=["diagnostic_summary.checks.private_snapshot_written", "snapshot_summary.private_player_state_count"],
    ),
    "needs_character_sync": SupportReviewPlaybookItem(
        blocker_id="needs_character_sync",
        title="Synced character snapshot is missing",
        support_steps=[
            "Confirm the key includes character permission.",
            "Ask the player to resync account data.",
            "Ask them to load character snapshots in Build Fit.",
        ],
        player_reply_template="Build Fit can only see manual sample snapshots right now. Please resync with character permission enabled, then load character snapshots in Build Fit.",
        product_fix_suggestion="Add a direct Connect-to-Build-Fit snapshot load prompt after character sync succeeds.",
        priority="P1",
        evidence_needed=["diagnostic_summary.checks.synced_character_snapshot", "snapshot_summary.synced_character_snapshot_count"],
    ),
    "needs_build_snapshot_load": SupportReviewPlaybookItem(
        blocker_id="needs_build_snapshot_load",
        title="Build Fit has not loaded synced gear",
        support_steps=[
            "Confirm a synced character snapshot exists.",
            "Ask the player to open Build Fit.",
            "Ask them to load the synced character snapshot and rerun Fit score.",
        ],
        player_reply_template="Your account snapshot exists, but Build Fit has not loaded the synced gear yet. Please open Build Fit, load the synced character snapshot, and rerun Fit score.",
        product_fix_suggestion="Auto-suggest the newest synced character snapshot when Build Fit opens.",
        priority="P2",
        evidence_needed=["diagnostic_summary.checks.build_fit_bridge_ready", "snapshot_summary.synced_gear_count"],
    ),
    "frontend_flow_incomplete": SupportReviewPlaybookItem(
        blocker_id="frontend_flow_incomplete",
        title="Backend is ready; player UI flow is incomplete",
        support_steps=[
            "Confirm diagnostic status is ready.",
            "Ask the player to open Build Fit.",
            "Ask them to select or import a build, load account gear, and run the expected result action.",
        ],
        player_reply_template="The backend connection looks healthy. Please open Build Fit, select or import a build, load account gear, then run the fit check or report again.",
        product_fix_suggestion="Add a guided next-step card when diagnostics are ready but the active view or build selection is incomplete.",
        priority="P2",
        evidence_needed=["diagnostic_summary.summary_status", "client_state.active_view", "client_state.active_build_id_present"],
    ),
    "privacy_boundary_violation": SupportReviewPlaybookItem(
        blocker_id="privacy_boundary_violation",
        title="Bundle violates support privacy boundary",
        support_steps=[
            "Discard the uploaded file.",
            "Ask the player to export a fresh debug bundle from GW2Radar.",
            "Remind them not to include raw keys or private payloads.",
        ],
        player_reply_template="Please discard that file and export a fresh debug bundle from GW2Radar. Do not send raw API keys, inventory, bank, wallet, material, achievement, equipment, or report payloads.",
        product_fix_suggestion="Keep automated sensitive-field detection and add stronger UI copy before export.",
        priority="P0",
        evidence_needed=["privacy_boundary_violation evidence paths"],
    ),
}


def create_support_review_audit(
    session: Session,
    *,
    review: SupportReviewReport,
    reviewer: str | None = None,
    reply_template: str | None = None,
    source: str = "support_workbench",
) -> SupportReviewAuditRecord:
    finding_ids = [finding.finding_id for finding in review.findings]
    severities = [finding.severity for finding in review.findings]
    record = SupportReviewAuditModel(
        case_id=f"support-review-{uuid4().hex}",
        bundle_schema_version=review.bundle_schema_version,
        review_schema_version=review.schema_version,
        overall_status=review.overall_status,
        summary=review.summary,
        highest_severity=_highest_severity(severities),
        finding_count=len(review.findings),
        finding_ids_json=finding_ids,
        reviewer=_safe_text(reviewer or "support", max_length=80),
        source=_safe_text(source, max_length=80),
        reply_template_summary=_safe_text(reply_template or "", max_length=360),
        properties_json={
            "evidence_refs": _evidence_refs(review),
            "redaction_boundary": list(review.redaction_boundary),
            "stores_raw_bundle": False,
            "stores_raw_api_key": False,
        },
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _to_record(record)


def list_support_review_audits(
    session: Session,
    *,
    limit: int = 20,
    status: str | None = None,
    severity: str | None = None,
    reviewer: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[SupportReviewAuditRecord]:
    safe_limit = min(max(int(limit or 20), 1), 100)
    statement = select(SupportReviewAuditModel)
    if status:
        statement = statement.where(SupportReviewAuditModel.overall_status == _safe_text(status, max_length=80))
    if severity:
        statement = statement.where(SupportReviewAuditModel.highest_severity == _safe_text(severity, max_length=20))
    if reviewer:
        statement = statement.where(SupportReviewAuditModel.reviewer == _safe_text(reviewer, max_length=80))
    if created_from:
        statement = statement.where(SupportReviewAuditModel.created_at >= created_from)
    if created_to:
        statement = statement.where(SupportReviewAuditModel.created_at <= created_to)
    rows = session.scalars(statement.order_by(SupportReviewAuditModel.created_at.desc()).limit(safe_limit)).all()
    return [_to_record(row) for row in rows]


def render_support_review_audit_csv(records: list[SupportReviewAuditRecord]) -> str:
    output = StringIO()
    fieldnames = [
        "case_id",
        "created_at",
        "overall_status",
        "highest_severity",
        "finding_count",
        "finding_ids",
        "reviewer",
        "source",
        "bundle_schema_version",
        "reply_template_summary",
    ]
    writer = DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "case_id": record.case_id,
                "created_at": record.created_at.isoformat(),
                "overall_status": record.overall_status,
                "highest_severity": record.highest_severity,
                "finding_count": record.finding_count,
                "finding_ids": ";".join(record.finding_ids),
                "reviewer": record.reviewer,
                "source": record.source,
                "bundle_schema_version": record.bundle_schema_version or "",
                "reply_template_summary": record.reply_template_summary,
            }
        )
    return output.getvalue()


def build_support_review_metrics(records: list[SupportReviewAuditRecord]) -> SupportReviewMetricsSummary:
    status_counts = _count_values(record.overall_status for record in records)
    severity_counts = _count_values(record.highest_severity for record in records)
    finding_counts = _count_values(finding_id for record in records for finding_id in record.finding_ids)
    blockers = [item for item in finding_counts if item.key != "none"][:5]
    return SupportReviewMetricsSummary(
        total_records=len(records),
        status_counts=status_counts,
        severity_counts=severity_counts,
        finding_counts=finding_counts,
        top_blockers=blockers,
        trend_summary=_trend_summary(len(records), status_counts, severity_counts, blockers),
    )


def build_support_review_playbook(metrics: SupportReviewMetricsSummary) -> SupportReviewPlaybookSummary:
    blocker_ids = [blocker.key for blocker in metrics.top_blockers]
    if not blocker_ids:
        blocker_ids = [count.key for count in metrics.status_counts if count.key != "ready"][:5]
    plays = [PLAYBOOKS[blocker_id] for blocker_id in blocker_ids if blocker_id in PLAYBOOKS]
    unmapped = [blocker_id for blocker_id in blocker_ids if blocker_id not in PLAYBOOKS]
    return SupportReviewPlaybookSummary(
        total_records=metrics.total_records,
        plays=plays,
        unmapped_blockers=unmapped,
        summary=_playbook_summary(metrics.total_records, plays, unmapped),
    )


def build_support_review_product_backlog(
    metrics: SupportReviewMetricsSummary,
    playbook: SupportReviewPlaybookSummary,
) -> SupportReviewBacklogSummary:
    blocker_counts = {item.key: item.count for item in metrics.finding_counts}
    items = [
        SupportReviewBacklogItem(
            backlog_id=f"support-backlog-{play.blocker_id}",
            blocker_id=play.blocker_id,
            title=play.title,
            priority=play.priority,
            affected_cases=blocker_counts.get(play.blocker_id, 0),
            product_fix_suggestion=play.product_fix_suggestion,
            support_signal=_support_signal(play.blocker_id, blocker_counts.get(play.blocker_id, 0)),
            acceptance_criteria=_acceptance_criteria(play),
        )
        for play in playbook.plays
    ]
    items.sort(key=lambda item: (_priority_rank(item.priority), -item.affected_cases, item.blocker_id))
    return SupportReviewBacklogSummary(
        total_records=metrics.total_records,
        backlog_items=items,
        summary=_backlog_summary(metrics.total_records, items),
    )


def _highest_severity(severities: list[str]) -> str:
    if not severities:
        return "info"
    return max(severities, key=lambda item: SEVERITY_RANK.get(item, 0))


def _safe_text(value: str, *, max_length: int) -> str:
    scrubbed = API_KEY_SHAPED_PATTERN.sub("[redacted-api-key-shaped-token]", str(value))
    scrubbed = LONG_SECRET_PATTERN.sub("[redacted-long-token]", scrubbed)
    scrubbed = " ".join(scrubbed.split())
    return scrubbed[:max_length]


def _evidence_refs(review: SupportReviewReport) -> list[str]:
    refs: list[str] = []
    for finding in review.findings:
        refs.extend(finding.evidence_refs)
    return refs[:20]


def _count_values(values) -> list[SupportReviewMetricCount]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "none")
        counts[key] = counts.get(key, 0) + 1
    return [
        SupportReviewMetricCount(key=key, count=count)
        for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _trend_summary(
    total_records: int,
    status_counts: list[SupportReviewMetricCount],
    severity_counts: list[SupportReviewMetricCount],
    blockers: list[SupportReviewMetricCount],
) -> str:
    if total_records == 0:
        return "No support review audit records match the current filters."
    top_status = status_counts[0].key if status_counts else "unknown"
    top_severity = severity_counts[0].key if severity_counts else "unknown"
    if blockers:
        top_blocker = blockers[0].key
        return f"{total_records} reviewed cases; most common status is {top_status}, severity is {top_severity}, and top blocker is {top_blocker}."
    return f"{total_records} reviewed cases; most common status is {top_status}, severity is {top_severity}, with no finding-specific blocker recorded."


def _playbook_summary(total_records: int, plays: list[SupportReviewPlaybookItem], unmapped: list[str]) -> str:
    if total_records == 0:
        return "No matching support cases; no remediation playbook is needed."
    if plays:
        return f"{len(plays)} remediation plays selected for {total_records} matching support cases."
    return f"{total_records} matching support cases found, but no mapped playbook exists for: {', '.join(unmapped) or 'unknown'}."


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)


def _support_signal(blocker_id: str, affected_cases: int) -> str:
    case_text = "case" if affected_cases == 1 else "cases"
    return f"{affected_cases} support {case_text} include blocker `{blocker_id}`."


def _acceptance_criteria(play: SupportReviewPlaybookItem) -> list[str]:
    return [
        f"Support review for `{play.blocker_id}` still avoids raw API keys and private account payloads.",
        "The UI presents the next player action without requiring support to inspect raw bundle JSON.",
        f"Diagnostic evidence includes: {', '.join(play.evidence_needed) if play.evidence_needed else 'safe support metadata'}.",
    ]


def _backlog_summary(total_records: int, items: list[SupportReviewBacklogItem]) -> str:
    if total_records == 0:
        return "No matching support cases; no product backlog items generated."
    if not items:
        return f"{total_records} matching support cases found, but no mapped product fix suggestion is available."
    top = items[0]
    return f"{len(items)} product backlog items generated from {total_records} matching cases; top priority is {top.priority} `{top.blocker_id}`."


def _to_record(row: SupportReviewAuditModel) -> SupportReviewAuditRecord:
    return SupportReviewAuditRecord(
        case_id=row.case_id,
        bundle_schema_version=row.bundle_schema_version,
        review_schema_version=row.review_schema_version,
        overall_status=row.overall_status,
        summary=row.summary,
        highest_severity=row.highest_severity,
        finding_count=row.finding_count,
        finding_ids=list(row.finding_ids_json or []),
        reviewer=row.reviewer,
        source=row.source,
        reply_template_summary=row.reply_template_summary,
        properties=dict(row.properties_json or {}),
        created_at=row.created_at,
    )
