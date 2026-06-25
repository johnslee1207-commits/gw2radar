from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from gw2radar.player_os.intent.models import PlayerIntent, PlayerPlan


RAW_KEY_PATTERN = re.compile(r"[0-9a-fA-F-]{36,}-[0-9a-fA-F-]{20,}")


class GovernanceGateResult(BaseModel):
    gate_id: str
    status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


def run_governance_gates(intent: PlayerIntent, plan: PlayerPlan) -> dict[str, Any]:
    results = [
        privacy_gate(intent, plan),
        recommendation_safety_gate(intent, plan),
        source_review_gate(intent, plan),
        report_publication_gate(intent, plan),
        quota_budget_gate(intent, plan),
    ]
    blocker_count = sum(len(result.blockers) for result in results)
    return {
        "schema_version": "gw2radar.player_os_governance.v1",
        "status": "blocked" if blocker_count else "ready",
        "blocker_count": blocker_count,
        "gates": [result.model_dump(mode="json") for result in results],
        "boundary": "Governance gates block unsafe or unsupported strong recommendations; they do not automate gameplay or trading.",
    }


def privacy_gate(intent: PlayerIntent, plan: PlayerPlan) -> GovernanceGateResult:
    rendered = f"{intent.model_dump(mode='json')} {plan.model_dump(mode='json')}"
    blockers = []
    if RAW_KEY_PATTERN.search(rendered):
        blockers.append("Potential raw API key shaped value detected in intent or plan output.")
    if "raw_payload" in rendered:
        blockers.append("Raw private payload marker detected.")
    return GovernanceGateResult(
        gate_id="privacy_gate",
        status="blocked" if blockers else "pass",
        blockers=blockers,
        evidence_refs=["/account/debug-bundle", "/api/v1/security/private-data"],
    )


def recommendation_safety_gate(intent: PlayerIntent, plan: PlayerPlan) -> GovernanceGateResult:
    rendered = " ".join(
        [
            intent.raw_text or "",
            plan.title,
            plan.focus,
            " ".join(action.title + " " + action.reason for action in plan.top_actions + plan.this_week),
            " ".join(plan.warnings),
        ]
    ).lower()
    blockers = []
    if any(term in rendered for term in ("auto trade", "automated trading", "自动交易", "guaranteed profit", "保证收益")):
        blockers.append("Automated trading or guaranteed-profit language is not allowed.")
    if any(term in rendered for term in ("bot farm", "自动刷", "gameplay automation")):
        blockers.append("Gameplay automation language is not allowed.")
    return GovernanceGateResult(gate_id="recommendation_safety_gate", status="blocked" if blockers else "pass", blockers=blockers)


def source_review_gate(intent: PlayerIntent, plan: PlayerPlan) -> GovernanceGateResult:
    warnings = []
    if intent.intent_type == "build_fit":
        warnings.append("Strong Build Fit recommendations require reviewed build metadata and patch freshness evidence.")
    if intent.intent_type == "market_watch":
        warnings.append("Market signals are informational and require reviewed or fresh price evidence.")
    return GovernanceGateResult(gate_id="source_review_gate", status="pass", warnings=warnings, evidence_refs=plan.evidence_refs)


def report_publication_gate(intent: PlayerIntent, plan: PlayerPlan) -> GovernanceGateResult:
    warnings = []
    if not plan.evidence_refs:
        warnings.append("Report preview has no evidence refs and must remain weak guidance.")
    return GovernanceGateResult(
        gate_id="report_publication_gate",
        status="pass",
        warnings=warnings,
        evidence_refs=plan.evidence_refs,
    )


def quota_budget_gate(intent: PlayerIntent, plan: PlayerPlan) -> GovernanceGateResult:
    warnings = ["Local MVP mode uses conservative refresh/report budgets; heavy refresh is manual."]
    return GovernanceGateResult(gate_id="quota_budget_gate", status="pass", warnings=warnings)
