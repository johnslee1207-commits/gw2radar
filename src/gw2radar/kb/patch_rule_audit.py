import os
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field

from gw2radar.kb.kb_models import KnowledgeRule


DEFAULT_PATCH_RULE_AUDIT_STORE = Path("data") / "kb" / "patch_rule_audit.jsonl"
PATCH_RULE_AUDIT_STORE_ENV = "GW2RADAR_PATCH_RULE_AUDIT_STORE"


class PatchRuleAuditAction(StrEnum):
    REVIEW = "review"
    PERSIST = "persist"
    ENABLE = "enable"


class PatchRuleAuditEvent(BaseModel):
    event_id: str
    action: PatchRuleAuditAction
    patch_id: str
    rule_id: str | None = None
    reviewer: str
    evidence_refs: list[str] = Field(default_factory=list)
    occurred_at: datetime
    details: dict[str, str | int | bool] = Field(default_factory=dict)


class PatchRuleAuditManifestEntry(BaseModel):
    rule_id: str
    rule_name: str
    source_patch_id: str
    reviewer: str | None = None
    reviewed_at: str | None = None
    persisted_at: str | None = None
    enabled_at: str | None = None
    evidence_chain: list[str] = Field(default_factory=list)


def record_patch_rule_audit_event(
    action: PatchRuleAuditAction,
    patch_id: str,
    reviewer: str,
    rule_id: str | None = None,
    evidence_refs: list[str] | None = None,
    details: dict[str, str | int | bool] | None = None,
    audit_store: Path | None = None,
) -> PatchRuleAuditEvent:
    event = PatchRuleAuditEvent(
        event_id=f"patch_audit_{_timestamp_id()}",
        action=action,
        patch_id=patch_id,
        rule_id=rule_id,
        reviewer=reviewer,
        evidence_refs=evidence_refs or [],
        occurred_at=datetime.now(UTC),
        details=details or {},
    )
    store = _resolve_audit_store(audit_store)
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json() + "\n")
    return event


def load_patch_rule_audit_events(audit_store: Path | None = None) -> list[PatchRuleAuditEvent]:
    store = _resolve_audit_store(audit_store)
    if not store.exists():
        return []
    events: list[PatchRuleAuditEvent] = []
    for line in store.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(PatchRuleAuditEvent.model_validate_json(line))
    return events


def list_patch_rule_audit_events(
    patch_id: str | None = None,
    rule_id: str | None = None,
    audit_store: Path | None = None,
) -> list[PatchRuleAuditEvent]:
    events = load_patch_rule_audit_events(audit_store)
    if patch_id is not None:
        events = [event for event in events if event.patch_id == patch_id]
    if rule_id is not None:
        events = [event for event in events if event.rule_id == rule_id]
    return events


def build_patch_rule_audit_manifest(
    rules: list[KnowledgeRule],
    audit_store: Path | None = None,
) -> list[dict]:
    events = load_patch_rule_audit_events(audit_store)
    by_rule: dict[str, list[PatchRuleAuditEvent]] = {}
    for event in events:
        if event.rule_id:
            by_rule.setdefault(event.rule_id, []).append(event)

    entries: list[PatchRuleAuditManifestEntry] = []
    for rule in rules:
        if not rule.enabled:
            continue
        rule_events = by_rule.get(rule.rule_id, [])
        persist_event = _last_event(rule_events, PatchRuleAuditAction.PERSIST)
        if persist_event is None:
            continue
        enable_event = _last_event(rule_events, PatchRuleAuditAction.ENABLE)
        review_event = _last_patch_event(events, PatchRuleAuditAction.REVIEW, persist_event.patch_id)
        evidence_chain = _unique_refs(
            [
                *rule.evidence_refs,
                *persist_event.evidence_refs,
                *(enable_event.evidence_refs if enable_event else []),
                *(review_event.evidence_refs if review_event else []),
            ]
        )
        entries.append(
            PatchRuleAuditManifestEntry(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                source_patch_id=persist_event.patch_id,
                reviewer=(enable_event or review_event or persist_event).reviewer,
                reviewed_at=review_event.occurred_at.isoformat() if review_event else None,
                persisted_at=persist_event.occurred_at.isoformat(),
                enabled_at=enable_event.occurred_at.isoformat() if enable_event else None,
                evidence_chain=evidence_chain,
            )
        )
    return [entry.model_dump(mode="json") for entry in entries]


def _last_event(events: list[PatchRuleAuditEvent], action: PatchRuleAuditAction) -> PatchRuleAuditEvent | None:
    matches = [event for event in events if event.action == action]
    return matches[-1] if matches else None


def _last_patch_event(
    events: list[PatchRuleAuditEvent],
    action: PatchRuleAuditAction,
    patch_id: str,
) -> PatchRuleAuditEvent | None:
    matches = [event for event in events if event.action == action and event.patch_id == patch_id]
    return matches[-1] if matches else None


def _unique_refs(refs: list[str]) -> list[str]:
    unique: list[str] = []
    for ref in refs:
        if ref and ref not in unique:
            unique.append(ref)
    return unique


def _timestamp_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")


def _resolve_audit_store(audit_store: Path | None) -> Path:
    if audit_store is not None:
        return audit_store
    env_path = os.environ.get(PATCH_RULE_AUDIT_STORE_ENV)
    return Path(env_path) if env_path else DEFAULT_PATCH_RULE_AUDIT_STORE
