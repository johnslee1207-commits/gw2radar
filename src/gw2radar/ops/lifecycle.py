from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OperationalLifecycleStage(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PERSISTED = "persisted"
    ENABLED = "enabled"
    EXPORTED = "exported"
    ARCHIVED = "archived"
    SIGNED_OFF = "signed_off"


DEFAULT_REVIEW_LIFECYCLE = [
    OperationalLifecycleStage.DRAFT,
    OperationalLifecycleStage.REVIEWED,
    OperationalLifecycleStage.PERSISTED,
    OperationalLifecycleStage.ENABLED,
]

DEFAULT_RELEASE_LIFECYCLE = [
    OperationalLifecycleStage.DRAFT,
    OperationalLifecycleStage.REVIEWED,
    OperationalLifecycleStage.EXPORTED,
    OperationalLifecycleStage.ARCHIVED,
    OperationalLifecycleStage.SIGNED_OFF,
]


class OperationalLifecycleEvent(BaseModel):
    stage: OperationalLifecycleStage
    actor: str | None = None
    occurred_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    details: dict[str, str | int | bool] = Field(default_factory=dict)


class OperationalLifecycleSummary(BaseModel):
    schema_version: str = "gw2radar.operational_lifecycle_summary.v1"
    object_id: str
    object_type: str
    current_stage: OperationalLifecycleStage
    stage_order: list[OperationalLifecycleStage]
    completed_stages: list[OperationalLifecycleStage]
    missing_stages: list[OperationalLifecycleStage]
    ready: bool
    progress_percent: float
    latest_actor: str | None = None
    latest_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    next_action: str
    boundary: str = (
        "Operational lifecycle summaries are metadata-only; they do not enable rules, publish content, "
        "execute files, automate gameplay, trade items, or store raw private payloads."
    )


def build_operational_lifecycle_summary(
    *,
    object_id: str,
    object_type: str,
    events: list[OperationalLifecycleEvent],
    stage_order: list[OperationalLifecycleStage] | None = None,
) -> OperationalLifecycleSummary:
    order = stage_order or DEFAULT_REVIEW_LIFECYCLE
    completed = _completed_stages(events, order)
    missing = [stage for stage in order if stage not in completed]
    current = completed[-1] if completed else order[0]
    latest = _latest_event(events)
    return OperationalLifecycleSummary(
        object_id=object_id,
        object_type=object_type,
        current_stage=current,
        stage_order=order,
        completed_stages=completed,
        missing_stages=missing,
        ready=not missing,
        progress_percent=round((len(completed) / len(order)) * 100, 1) if order else 100.0,
        latest_actor=latest.actor if latest else None,
        latest_at=latest.occurred_at if latest else None,
        evidence_refs=_unique_refs([ref for event in events for ref in event.evidence_refs]),
        next_action=_next_action(missing),
    )


def lifecycle_event(
    stage: OperationalLifecycleStage | str,
    *,
    actor: str | None = None,
    occurred_at: datetime | None = None,
    evidence_refs: list[str] | None = None,
    details: dict[str, str | int | bool] | None = None,
) -> OperationalLifecycleEvent:
    return OperationalLifecycleEvent(
        stage=OperationalLifecycleStage(stage),
        actor=actor,
        occurred_at=occurred_at or datetime.now(UTC),
        evidence_refs=evidence_refs or [],
        details=details or {},
    )


def _completed_stages(
    events: list[OperationalLifecycleEvent],
    stage_order: list[OperationalLifecycleStage],
) -> list[OperationalLifecycleStage]:
    seen = {event.stage for event in events}
    return [stage for stage in stage_order if stage in seen]


def _latest_event(events: list[OperationalLifecycleEvent]) -> OperationalLifecycleEvent | None:
    dated = [event for event in events if event.occurred_at is not None]
    if dated:
        return sorted(dated, key=lambda event: event.occurred_at or datetime.min.replace(tzinfo=UTC))[-1]
    return events[-1] if events else None


def _unique_refs(refs: list[str]) -> list[str]:
    unique: list[str] = []
    for ref in refs:
        if ref and ref not in unique:
            unique.append(ref)
    return unique


def _next_action(missing: list[OperationalLifecycleStage]) -> str:
    if not missing:
        return "Lifecycle is complete for the configured gate."
    stage = missing[0]
    if stage == OperationalLifecycleStage.REVIEWED:
        return "Perform manual review and record reviewer evidence."
    if stage == OperationalLifecycleStage.PERSISTED:
        return "Persist reviewed candidates with explicit operator confirmation."
    if stage == OperationalLifecycleStage.ENABLED:
        return "Enable reviewed persisted rules only after separate confirmation."
    if stage == OperationalLifecycleStage.EXPORTED:
        return "Export a metadata-only operator packet for review."
    if stage == OperationalLifecycleStage.ARCHIVED:
        return "Archive the reviewed evidence bundle before sign-off."
    if stage == OperationalLifecycleStage.SIGNED_OFF:
        return "Record explicit release sign-off after archive diff review."
    return "Create the draft metadata record."
