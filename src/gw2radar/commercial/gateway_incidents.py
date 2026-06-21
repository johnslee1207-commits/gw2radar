from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import MarketSnapshotModel, RefreshQueueModel
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
