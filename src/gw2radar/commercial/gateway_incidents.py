from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import MarketSnapshotModel, PlayerGatewayIncidentSnapshotModel, RefreshQueueModel
from gw2radar.commercial.market_radar import get_last_official_price_refresh_result


class GatewayIncidentEvent(BaseModel):
    event_id: str
    source: Literal["account_sync", "public_refresh", "market_price_refresh"]
    event_type: str
    status: str
    severity: Literal["info", "warn", "blocked"]
    endpoint: str | None = None
    retryable: bool = False
    retry_after_seconds: int | None = None
    next_attempt_at: datetime | None = None
    attempt_count: int = 0
    last_error_code: str | None = None
    params_hash: str | None = None
    player_message: str
    player_action: str
    observed_at: datetime


class GatewayIncidentTimeline(BaseModel):
    schema_version: str = "gw2radar.gateway_incident_timeline.v1"
    timeline_status: Literal["clear", "active", "waiting_retry", "needs_review"]
    event_count: int
    retry_event_count: int
    failed_event_count: int
    latest_market_snapshot_at: datetime | None = None
    events: list[GatewayIncidentEvent] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    boundary: str = (
        "Gateway incident timeline is metadata-only; it must not include raw API keys, "
        "private account payloads, or market order automation."
    )


class GatewayIncidentSnapshot(BaseModel):
    schema_version: str = "gw2radar.gateway_incident_snapshot.v1"
    snapshot_id: str
    user_id: str
    source: str
    created_at: datetime
    timeline_status: str
    event_count: int
    retry_event_count: int
    failed_event_count: int
    latest_market_snapshot_at: datetime | None = None
    events: list[dict] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    boundary: str


class GatewayIncidentHistoryComparison(BaseModel):
    schema_version: str = "gw2radar.gateway_incident_history_comparison.v1"
    status: Literal["insufficient_history", "unchanged", "improved", "regressed"]
    retry_event_delta: int = 0
    failed_event_delta: int = 0
    event_count_delta: int = 0
    notes: list[str] = Field(default_factory=list)


class GatewayIncidentHistory(BaseModel):
    schema_version: str = "gw2radar.gateway_incident_history.v1"
    snapshots: list[GatewayIncidentSnapshot]
    comparison: GatewayIncidentHistoryComparison
    boundary: str = "Gateway incident history stores metadata-only snapshots and excludes raw API keys and private account payloads."


def build_gateway_incident_timeline(session: Session, *, limit: int = 20) -> GatewayIncidentTimeline:
    events = _refresh_queue_events(session)
    events.extend(_market_price_events(session))
    events = sorted(events, key=lambda item: item.observed_at, reverse=True)[: max(1, limit)]
    retry_count = sum(1 for event in events if event.retryable or event.status in {"delayed", "refresh_pending"})
    failed_count = sum(1 for event in events if event.severity == "blocked")
    if failed_count:
        status = "needs_review"
    elif retry_count:
        status = "waiting_retry"
    elif any(event.status in {"queued", "processing"} for event in events):
        status = "active"
    else:
        status = "clear"
    latest_market_snapshot_at = _latest_market_snapshot_at(session)
    return GatewayIncidentTimeline(
        timeline_status=status,
        event_count=len(events),
        retry_event_count=retry_count,
        failed_event_count=failed_count,
        latest_market_snapshot_at=latest_market_snapshot_at,
        events=events,
        next_actions=_next_actions(status, events),
    )


def record_gateway_incident_snapshot(
    session: Session,
    timeline: GatewayIncidentTimeline,
    *,
    source: str = "player_dashboard",
    user_id: str = "local-user",
) -> GatewayIncidentSnapshot:
    created_at = datetime.now(timezone.utc)
    row = PlayerGatewayIncidentSnapshotModel(
        snapshot_id=f"gateway-incident-snapshot-{created_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        user_id=user_id,
        source=source,
        timeline_status=timeline.timeline_status,
        event_count=timeline.event_count,
        retry_event_count=timeline.retry_event_count,
        failed_event_count=timeline.failed_event_count,
        latest_market_snapshot_at=timeline.latest_market_snapshot_at,
        events_json=[event.model_dump(mode="json") for event in timeline.events],
        next_actions_json=list(timeline.next_actions),
        boundary=timeline.boundary,
        created_at=created_at,
    )
    session.add(row)
    session.commit()
    return _snapshot_from_model(row)


def list_gateway_incident_history(session: Session, *, limit: int = 10) -> GatewayIncidentHistory:
    rows = (
        session.query(PlayerGatewayIncidentSnapshotModel)
        .order_by(PlayerGatewayIncidentSnapshotModel.created_at.desc())
        .limit(max(1, limit))
        .all()
    )
    snapshots = [_snapshot_from_model(row) for row in rows]
    return GatewayIncidentHistory(snapshots=snapshots, comparison=_compare_snapshots(snapshots))


def render_gateway_incident_history_markdown(history: GatewayIncidentHistory) -> str:
    lines = [
        "# Gateway Incident History",
        "",
        f"- Schema: {history.schema_version}",
        f"- Snapshot count: {len(history.snapshots)}",
        f"- Comparison: {history.comparison.status}",
        f"- Retry delta: {history.comparison.retry_event_delta}",
        f"- Failed delta: {history.comparison.failed_event_delta}",
        "",
        "## Snapshots",
        "",
    ]
    for snapshot in history.snapshots:
        lines.append(
            f"- `{snapshot.snapshot_id}` {snapshot.timeline_status}: "
            f"{snapshot.event_count} events, {snapshot.retry_event_count} retry, "
            f"{snapshot.failed_event_count} failed at {snapshot.created_at.isoformat()}"
        )
    lines.extend(["", "## Latest Events", ""])
    for event in (history.snapshots[0].events if history.snapshots else [])[:10]:
        lines.append(
            f"- {event.get('source')} / {event.get('status')}: "
            f"{event.get('endpoint') or event.get('event_type')} -> {event.get('player_action')}"
        )
    lines.extend(["", "## Boundary", "", f"- {history.boundary}"])
    return "\n".join(lines) + "\n"


def render_gateway_incident_history_csv(history: GatewayIncidentHistory) -> str:
    rows = [
        "snapshot_id,created_at,source,timeline_status,event_count,retry_event_count,failed_event_count,next_actions",
    ]
    for snapshot in history.snapshots:
        rows.append(
            ",".join(
                [
                    _csv(snapshot.snapshot_id),
                    _csv(snapshot.created_at.isoformat()),
                    _csv(snapshot.source),
                    _csv(snapshot.timeline_status),
                    str(snapshot.event_count),
                    str(snapshot.retry_event_count),
                    str(snapshot.failed_event_count),
                    _csv("; ".join(snapshot.next_actions)),
                ]
            )
        )
    rows.extend(
        [
            "",
            "comparison_key,comparison_value",
            f"status,{_csv(history.comparison.status)}",
            f"retry_event_delta,{history.comparison.retry_event_delta}",
            f"failed_event_delta,{history.comparison.failed_event_delta}",
            f"event_count_delta,{history.comparison.event_count_delta}",
        ]
    )
    return "\n".join(rows) + "\n"


def _refresh_queue_events(session: Session) -> list[GatewayIncidentEvent]:
    rows = (
        session.query(RefreshQueueModel)
        .order_by(RefreshQueueModel.updated_at.desc())
        .limit(50)
        .all()
    )
    events: list[GatewayIncidentEvent] = []
    for row in rows:
        if row.task_type == "account_snapshot_sync":
            source = "account_sync"
            message = "Account sync job is visible in the worker queue."
            action = _account_action(row.status)
        elif row.task_type == "public_static_refresh":
            source = "public_refresh"
            message = "Public static refresh job is visible in the worker queue."
            action = _public_action(row.status)
        else:
            continue
        events.append(
            GatewayIncidentEvent(
                event_id=row.request_id,
                source=source,
                event_type=row.task_type,
                status=row.status,
                severity=_queue_severity(row.status),
                endpoint=row.endpoint,
                retryable=row.status == "delayed",
                retry_after_seconds=row.retry_after_seconds,
                next_attempt_at=_aware(row.next_attempt_at),
                attempt_count=row.attempts,
                last_error_code=row.last_error_code,
                params_hash=row.params_hash,
                player_message=message,
                player_action=action,
                observed_at=_aware(row.updated_at) or datetime.now(timezone.utc),
            )
        )
    return events


def _market_price_events(session: Session) -> list[GatewayIncidentEvent]:
    result = get_last_official_price_refresh_result()
    if result is not None:
        status = str(result.get("status") or "unknown")
        diagnostics = result.get("gateway_diagnostics") if isinstance(result.get("gateway_diagnostics"), list) else []
        retryable = status == "refresh_pending" or any(item.get("retryable") for item in diagnostics if isinstance(item, dict))
        return [
            GatewayIncidentEvent(
                event_id="market_price_refresh:last_result",
                source="market_price_refresh",
                event_type="official_price_refresh",
                status=status,
                severity="warn" if retryable else "info",
                endpoint="/v2/commerce/prices",
                retryable=retryable,
                retry_after_seconds=result.get("retry_after_seconds"),
                last_error_code=(diagnostics[0].get("status") if diagnostics and isinstance(diagnostics[0], dict) else None),
                player_message="Latest official market price refresh result is available.",
                player_action=str(result.get("player_action") or "Refresh official prices before relying on market coverage."),
                observed_at=datetime.now(timezone.utc),
            )
        ]
    latest = _latest_market_snapshot_at(session)
    if latest is None:
        return [
            GatewayIncidentEvent(
                event_id="market_price_refresh:no_recent_snapshot",
                source="market_price_refresh",
                event_type="official_price_refresh",
                status="not_started",
                severity="warn",
                endpoint="/v2/commerce/prices",
                player_message="No official commerce price snapshot is available yet.",
                player_action="Run Refresh official prices after account holdings are synced.",
                observed_at=datetime.now(timezone.utc),
            )
        ]
    return [
        GatewayIncidentEvent(
            event_id="market_price_refresh:latest_snapshot",
            source="market_price_refresh",
            event_type="official_price_refresh",
            status="succeeded",
            severity="info",
            endpoint="/v2/commerce/prices",
            player_message="Official commerce price snapshots exist for account value coverage.",
            player_action="Rerun account value or readiness to refresh visible coverage.",
            observed_at=latest,
        )
    ]


def _latest_market_snapshot_at(session: Session) -> datetime | None:
    row = (
        session.query(MarketSnapshotModel)
        .filter(MarketSnapshotModel.source == "official_commerce_api")
        .order_by(MarketSnapshotModel.observed_at.desc())
        .first()
    )
    return _aware(row.observed_at) if row else None


def _queue_severity(status: str) -> Literal["info", "warn", "blocked"]:
    if status == "failed":
        return "blocked"
    if status in {"delayed", "processing"}:
        return "warn"
    return "info"


def _account_action(status: str) -> str:
    if status == "delayed":
        return "Wait for the retry window, then run the account sync worker again."
    if status == "failed":
        return "Review account sync permissions and latest worker error before retrying."
    if status in {"queued", "processing"}:
        return "Run the account sync worker or wait for the local worker loop."
    return "Use readiness or account value after sync has completed."


def _public_action(status: str) -> str:
    if status == "delayed":
        return "Wait for the public refresh backoff window, then drain one public refresh job."
    if status == "failed":
        return "Review public refresh endpoint and id list before queueing more work."
    if status in {"queued", "processing"}:
        return "Drain the public refresh queue in development or wait for the worker."
    return "Public refresh metadata is available for planning evidence."


def _next_actions(status: str, events: list[GatewayIncidentEvent]) -> list[str]:
    if status == "clear":
        return ["No gateway incident needs action right now; refresh stale data before high-value planning."]
    actions = []
    if any(event.source == "account_sync" and event.retryable for event in events):
        actions.append("Account sync is waiting for retry; use Queue health before syncing again.")
    if any(event.source == "public_refresh" and event.retryable for event in events):
        actions.append("Public refresh is waiting for retry; inspect public refresh health before draining.")
    if any(event.source == "market_price_refresh" and event.retryable for event in events):
        actions.append("Market price refresh is delayed; wait, then run Refresh official prices again.")
    if any(event.severity == "blocked" for event in events):
        actions.append("A gateway job is blocked; review the latest error code before adding more work.")
    return actions or ["Review the latest gateway event and retry the specific refresh step."]


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _snapshot_from_model(row: PlayerGatewayIncidentSnapshotModel) -> GatewayIncidentSnapshot:
    return GatewayIncidentSnapshot(
        snapshot_id=row.snapshot_id,
        user_id=row.user_id,
        source=row.source,
        created_at=_aware(row.created_at) or datetime.now(timezone.utc),
        timeline_status=row.timeline_status,
        event_count=row.event_count,
        retry_event_count=row.retry_event_count,
        failed_event_count=row.failed_event_count,
        latest_market_snapshot_at=_aware(row.latest_market_snapshot_at),
        events=list(row.events_json or []),
        next_actions=list(row.next_actions_json or []),
        boundary=row.boundary,
    )


def _compare_snapshots(snapshots: list[GatewayIncidentSnapshot]) -> GatewayIncidentHistoryComparison:
    if len(snapshots) < 2:
        return GatewayIncidentHistoryComparison(
            status="insufficient_history",
            notes=["Save at least two gateway incident snapshots to compare retry and failure changes."],
        )
    latest, previous = snapshots[0], snapshots[1]
    retry_delta = latest.retry_event_count - previous.retry_event_count
    failed_delta = latest.failed_event_count - previous.failed_event_count
    event_delta = latest.event_count - previous.event_count
    if retry_delta == 0 and failed_delta == 0 and event_delta == 0:
        status = "unchanged"
    elif retry_delta <= 0 and failed_delta <= 0:
        status = "improved"
    else:
        status = "regressed"
    notes = [
        f"Retry events changed by {retry_delta}.",
        f"Failed events changed by {failed_delta}.",
        f"Total gateway events changed by {event_delta}.",
    ]
    return GatewayIncidentHistoryComparison(
        status=status,
        retry_event_delta=retry_delta,
        failed_event_delta=failed_delta,
        event_count_delta=event_delta,
        notes=notes,
    )


def _csv(value: str) -> str:
    text = str(value).replace('"', '""')
    if any(character in text for character in [",", "\n", '"']):
        return f'"{text}"'
    return text
