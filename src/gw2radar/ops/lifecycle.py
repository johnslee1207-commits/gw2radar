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
    PACKAGED = "packaged"
    VERIFIED = "verified"
    AUDITED = "audited"
    ARCHIVED = "archived"
    DIFF_REVIEWED = "diff_reviewed"
    SIGNED_OFF = "signed_off"
    HANDOFF_READY = "handoff_ready"


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

DEFAULT_DELIVERY_LIFECYCLE = [
    OperationalLifecycleStage.DRAFT,
    OperationalLifecycleStage.EXPORTED,
    OperationalLifecycleStage.PACKAGED,
    OperationalLifecycleStage.VERIFIED,
    OperationalLifecycleStage.AUDITED,
    OperationalLifecycleStage.HANDOFF_READY,
]


class OperationalLifecycleEvent(BaseModel):
    stage: OperationalLifecycleStage
    actor: str | None = None
    occurred_at: datetime | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    details: dict[str, str | int | bool] = Field(default_factory=dict)


class OperationalLifecycleGate(BaseModel):
    stage: OperationalLifecycleStage
    complete: bool
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


class DeliveryReadinessProjection(BaseModel):
    schema_version: str = "gw2radar.delivery_readiness_projection.v1"
    ready: bool
    maturity_label: str
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Delivery readiness projections are metadata-only; they do not execute files, publish content, "
        "automate gameplay, trade items, or store raw private payloads."
    )


def build_delivery_readiness_projection(
    *,
    missing_gates: list[str] | None = None,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    ready_next_actions: list[str],
    blocked_next_actions: list[str],
    evidence_refs: list[str] | None = None,
) -> DeliveryReadinessProjection:
    gate_list = _unique_refs(missing_gates or [])
    blocker_list = _unique_refs(blockers or [])
    warning_list = _unique_refs(warnings or [])
    ready = not gate_list and not blocker_list
    if blocker_list:
        maturity_label = "blocked"
    elif gate_list or warning_list:
        maturity_label = "review_needed"
    else:
        maturity_label = "ready"
    return DeliveryReadinessProjection(
        ready=ready,
        maturity_label=maturity_label,
        missing_gates=gate_list,
        blockers=blocker_list,
        warnings=warning_list,
        next_actions=ready_next_actions if ready else blocked_next_actions,
        evidence_refs=_unique_refs(evidence_refs or []),
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


def build_operational_lifecycle_summary_from_gates(
    *,
    object_id: str,
    object_type: str,
    gates: list[OperationalLifecycleGate],
    stage_order: list[OperationalLifecycleStage] | None = None,
) -> OperationalLifecycleSummary:
    order = stage_order or [gate.stage for gate in gates]
    events = [
        lifecycle_event(
            gate.stage,
            actor=gate.actor,
            occurred_at=gate.occurred_at,
            evidence_refs=gate.evidence_refs,
            details=gate.details,
        )
        for gate in gates
        if gate.complete
    ]
    return build_operational_lifecycle_summary(
        object_id=object_id,
        object_type=object_type,
        events=events,
        stage_order=order,
    )


def build_delivery_operational_lifecycle_summary(
    *,
    object_id: str,
    object_type: str,
    draft_ready: bool,
    exported_ready: bool,
    packaged_ready: bool,
    verified_ready: bool,
    audited_ready: bool,
    handoff_ready: bool,
    actor: str = "delivery_lifecycle",
    occurred_at: datetime | None = None,
    evidence_refs: list[str] | None = None,
    details: dict[str, str | int | bool] | None = None,
) -> OperationalLifecycleSummary:
    when = occurred_at or datetime.now(UTC)
    refs = evidence_refs or []
    base_details = details or {}
    return build_operational_lifecycle_summary_from_gates(
        object_id=object_id,
        object_type=object_type,
        stage_order=DEFAULT_DELIVERY_LIFECYCLE,
        gates=[
            lifecycle_gate(
                OperationalLifecycleStage.DRAFT,
                complete=draft_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
            lifecycle_gate(
                OperationalLifecycleStage.EXPORTED,
                complete=exported_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
            lifecycle_gate(
                OperationalLifecycleStage.PACKAGED,
                complete=packaged_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
            lifecycle_gate(
                OperationalLifecycleStage.VERIFIED,
                complete=verified_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
            lifecycle_gate(
                OperationalLifecycleStage.AUDITED,
                complete=audited_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
            lifecycle_gate(
                OperationalLifecycleStage.HANDOFF_READY,
                complete=handoff_ready,
                actor=actor,
                occurred_at=when,
                evidence_refs=refs,
                details=base_details,
            ),
        ],
    )


def build_delivery_operational_lifecycle_projection(
    *,
    object_type: str,
    primary_object_id: str | None,
    fallback_object_id: str,
    draft_ready: bool,
    exported_ready: bool,
    packaged_ready: bool,
    verified_ready: bool,
    audited_ready: bool,
    handoff_ready: bool,
    actor: str | None = None,
    fallback_actor: str = "delivery_lifecycle",
    occurred_at: datetime | None = None,
    fallback_occurred_at: datetime | None = None,
    evidence_refs: list[str] | None = None,
    details: dict[str, str | int | bool] | None = None,
) -> OperationalLifecycleSummary:
    """Project domain delivery state into the shared metadata-only lifecycle."""
    return build_delivery_operational_lifecycle_summary(
        object_id=primary_object_id or fallback_object_id,
        object_type=object_type,
        draft_ready=draft_ready,
        exported_ready=exported_ready,
        packaged_ready=packaged_ready,
        verified_ready=verified_ready,
        audited_ready=audited_ready,
        handoff_ready=handoff_ready,
        actor=actor or fallback_actor,
        occurred_at=occurred_at or fallback_occurred_at,
        evidence_refs=evidence_refs,
        details=details,
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


def lifecycle_gate(
    stage: OperationalLifecycleStage | str,
    *,
    complete: bool,
    actor: str | None = None,
    occurred_at: datetime | None = None,
    evidence_refs: list[str] | None = None,
    details: dict[str, str | int | bool] | None = None,
) -> OperationalLifecycleGate:
    return OperationalLifecycleGate(
        stage=OperationalLifecycleStage(stage),
        complete=complete,
        actor=actor,
        occurred_at=occurred_at,
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
    if stage == OperationalLifecycleStage.PACKAGED:
        return "Package the reviewed delivery files into a checksumed zip bundle."
    if stage == OperationalLifecycleStage.VERIFIED:
        return "Verify the delivery zip checksum, whitelist, schema, and no-secret boundaries."
    if stage == OperationalLifecycleStage.AUDITED:
        return "Record a metadata-only verification audit before handoff."
    if stage == OperationalLifecycleStage.ARCHIVED:
        return "Archive the reviewed evidence bundle before sign-off."
    if stage == OperationalLifecycleStage.DIFF_REVIEWED:
        return "Review archive diff evidence and resolve regressions before sign-off."
    if stage == OperationalLifecycleStage.SIGNED_OFF:
        return "Record explicit release sign-off after archive diff review."
    if stage == OperationalLifecycleStage.HANDOFF_READY:
        return "Complete the operator handoff checklist after package verification and audit."
    return "Create the draft metadata record."
