from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


IntentType = Literal[
    "returner",
    "legendary",
    "build_fit",
    "account_overview",
    "what_should_i_do_now",
    "market_watch",
    "unknown",
]

Urgency = Literal["low", "medium", "high"]
ConstraintSource = Literal["template", "user_text", "ui_selection", "system_default"]
WorkflowStatus = Literal[
    "created",
    "checking_account",
    "needs_api_key",
    "needs_permission",
    "syncing",
    "analyzing",
    "needs_user_choice",
    "planning",
    "ready",
    "failed",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlayerConstraint(BaseModel):
    constraint_id: str
    intent_id: str
    key: str
    value: Any
    source: ConstraintSource
    confidence: float = 1.0


class PlayerIntent(BaseModel):
    schema_version: str = "gw2radar.player_intent.v1"
    intent_id: str
    account_id: str | None = None
    raw_text: str | None = None
    template_id: str | None = None
    intent_type: IntentType = "unknown"
    goal_id: str | None = None
    profession: str | None = None
    specialization: str | None = None
    game_mode: str | None = None
    urgency: Urgency = "medium"
    constraints: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IntentTemplate(BaseModel):
    schema_version: str = "gw2radar.intent_template.v1"
    template_id: str
    name: str
    domain: Literal["returner", "legendary", "build_fit", "account", "market"]
    description: str
    default_intent_type: IntentType
    default_constraints: dict[str, Any] = Field(default_factory=dict)
    required_permissions: list[str] = Field(default_factory=list)
    recommended_next_questions: list[str] = Field(default_factory=list)
    enabled: bool = True


class WorkflowState(BaseModel):
    schema_version: str = "gw2radar.workflow_state.v1"
    workflow_id: str
    intent_id: str
    workflow_type: str
    status: WorkflowStatus
    current_step: str
    required_user_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class PlanAction(BaseModel):
    title: str
    reason: str
    urgency: Urgency = "medium"
    linked_goal: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundary: str = "advisory_manual_action_only"
    confidence: float = 1.0
    liquidity_note: str | None = None
    risk_reason: str | None = None
    execution_risk: str | None = None
    liquidity_reason: str | None = None


class PlayerPlan(BaseModel):
    schema_version: str = "gw2radar.player_plan.v1"
    plan_id: str
    intent_id: str
    workflow_id: str
    intent_type: IntentType
    title: str
    focus: str
    top_actions: list[PlanAction]
    this_week: list[PlanAction] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    safety_boundaries: list[str] = Field(default_factory=list)
    freshness_notes: list[str] = Field(default_factory=list)
    version: int = 1


class PlanRevisionRequest(BaseModel):
    plan_id: str
    raw_revision_text: str
    constraints_delta: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "local-player"


class PlanDiff(BaseModel):
    schema_version: str = "gw2radar.player_plan_diff.v1"
    previous_plan_id: str
    revised_plan_id: str
    changed_constraints: dict[str, Any]
    added_warnings: list[str] = Field(default_factory=list)
    old_focus: str
    new_focus: str
    summary: str


class WhatIfResult(BaseModel):
    schema_version: str = "gw2radar.player_what_if.v1"
    plan_id: str
    changed_constraints: dict[str, Any]
    plan_delta: str
    cost_delta: str
    time_delta: str
    feasibility: str
    warnings: list[str] = Field(default_factory=list)


class PlayerReport(BaseModel):
    schema_version: str = "gw2radar.player_os_report.v1"
    report_id: str
    plan_id: str
    version: int = 1
    title: str
    sections: list[dict[str, Any]]
    assumptions: list[str]
    warnings: list[str]
    evidence_refs: list[str]
    safety_boundaries: list[str]


class IntentParseResult(BaseModel):
    schema_version: str = "gw2radar.intent_parse_result.v1"
    intent: PlayerIntent
    constraints: list[PlayerConstraint]
    clarifying_questions: list[str] = Field(default_factory=list)
    router_target: str


class IntentStartResult(BaseModel):
    schema_version: str = "gw2radar.intent_start_result.v1"
    intent: PlayerIntent
    workflow: WorkflowState
    plan: PlayerPlan
    report_preview: PlayerReport
    governance: dict[str, Any]
