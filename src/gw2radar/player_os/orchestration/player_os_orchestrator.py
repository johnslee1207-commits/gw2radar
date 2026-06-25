from __future__ import annotations

from uuid import uuid4

from gw2radar.player_os.governance.gates import run_governance_gates
from gw2radar.player_os.intent.intent_parser import parse_player_intent
from gw2radar.player_os.intent.intent_templates import get_intent_template, list_intent_templates
from gw2radar.player_os.intent.models import (
    IntentParseResult,
    IntentStartResult,
    PlayerIntent,
    PlayerPlan,
    PlayerReport,
    WorkflowState,
)
from gw2radar.player_os.iteration.plan_revision import evaluate_what_if, revise_plan
from gw2radar.player_os.workflows.wizards import build_workflow_and_plan


INTENTS: dict[str, PlayerIntent] = {}
WORKFLOWS: dict[str, WorkflowState] = {}
PLANS: dict[str, PlayerPlan] = {}
REPORTS: dict[str, PlayerReport] = {}


def parse_intent(raw_text: str | None = None, template_id: str | None = None, ui_constraints: dict | None = None) -> IntentParseResult:
    return parse_player_intent(raw_text=raw_text, template_id=template_id, ui_constraints=ui_constraints)


def start_intent(raw_text: str | None = None, template_id: str | None = None, ui_constraints: dict | None = None) -> IntentStartResult:
    parsed = parse_intent(raw_text=raw_text, template_id=template_id, ui_constraints=ui_constraints)
    workflow, plan = build_workflow_and_plan(parsed.intent)
    report = build_report_preview(plan)
    governance = run_governance_gates(parsed.intent, plan)
    INTENTS[parsed.intent.intent_id] = parsed.intent
    WORKFLOWS[workflow.workflow_id] = workflow
    PLANS[plan.plan_id] = plan
    REPORTS[report.report_id] = report
    return IntentStartResult(
        intent=parsed.intent,
        workflow=workflow,
        plan=plan,
        report_preview=report,
        governance=governance,
    )


def start_template(template_id: str) -> IntentStartResult:
    if get_intent_template(template_id) is None:
        raise KeyError(template_id)
    return start_intent(template_id=template_id)


def get_intent(intent_id: str) -> PlayerIntent | None:
    return INTENTS.get(intent_id)


def update_intent_constraints(intent_id: str, constraints: dict) -> PlayerIntent | None:
    intent = INTENTS.get(intent_id)
    if intent is None:
        return None
    intent.constraints.update(constraints)
    INTENTS[intent_id] = intent
    return intent


def clarify_intent(intent_id: str, raw_text: str) -> IntentStartResult | None:
    current = INTENTS.get(intent_id)
    if current is None:
        return None
    return start_intent(raw_text=raw_text, template_id=current.template_id, ui_constraints=current.constraints)


def get_workflow(workflow_id: str) -> WorkflowState | None:
    return WORKFLOWS.get(workflow_id)


def advance_workflow(workflow_id: str) -> WorkflowState | None:
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        return None
    next_status = {
        "created": "checking_account",
        "checking_account": "analyzing",
        "needs_user_choice": "planning",
        "planning": "ready",
        "analyzing": "ready",
    }.get(workflow.status, workflow.status)
    workflow.status = next_status
    workflow.current_step = "ready" if next_status == "ready" else workflow.current_step
    WORKFLOWS[workflow_id] = workflow
    return workflow


def answer_workflow(workflow_id: str, answer: dict) -> WorkflowState | None:
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        return None
    workflow.required_user_actions = []
    workflow.warnings.append(f"Player answer captured with keys: {', '.join(sorted(answer)) or 'none'}.")
    workflow.status = "planning"
    WORKFLOWS[workflow_id] = workflow
    return workflow


def cancel_workflow(workflow_id: str) -> WorkflowState | None:
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        return None
    workflow.status = "failed"
    workflow.current_step = "cancelled"
    workflow.warnings.append("Workflow cancelled by player.")
    WORKFLOWS[workflow_id] = workflow
    return workflow


def get_plan(plan_id: str) -> PlayerPlan | None:
    return PLANS.get(plan_id)


def revise_existing_plan(plan_id: str, raw_revision_text: str, constraints_delta: dict | None = None):
    plan = PLANS.get(plan_id)
    if plan is None:
        return None
    revised, diff = revise_plan(plan, raw_revision_text, constraints_delta)
    PLANS[revised.plan_id] = revised
    report = build_report_preview(revised)
    REPORTS[report.report_id] = report
    return revised, diff, report


def what_if_plan(plan_id: str, raw_text: str, constraints_delta: dict | None = None):
    plan = PLANS.get(plan_id)
    if plan is None:
        return None
    return evaluate_what_if(plan, raw_text, constraints_delta)


def diff_plan(previous_plan_id: str, revised_plan_id: str):
    previous = PLANS.get(previous_plan_id)
    revised = PLANS.get(revised_plan_id)
    if previous is None or revised is None:
        return None
    return {
        "schema_version": "gw2radar.player_plan_diff_lookup.v1",
        "previous_plan_id": previous.plan_id,
        "revised_plan_id": revised.plan_id,
        "changed_constraints": {
            key: value
            for key, value in revised.constraints.items()
            if previous.constraints.get(key) != value
        },
        "old_focus": previous.focus,
        "new_focus": revised.focus,
    }


def build_now_result() -> PlayerPlan:
    result = start_intent(raw_text="What should I do now?", ui_constraints={"daily_time_limit": "30m"})
    return result.plan


def build_report_preview(plan: PlayerPlan) -> PlayerReport:
    report = PlayerReport(
        report_id=f"report-{uuid4().hex[:12]}",
        plan_id=plan.plan_id,
        title=f"{plan.title} Preview",
        sections=[
            {"heading": "Focus", "content": plan.focus},
            {"heading": "Top Actions", "content": [action.model_dump(mode="json") for action in plan.top_actions]},
            {"heading": "Assumptions", "content": plan.assumptions},
            {"heading": "Warnings", "content": plan.warnings},
        ],
        assumptions=plan.assumptions,
        warnings=plan.warnings,
        evidence_refs=plan.evidence_refs,
        safety_boundaries=plan.safety_boundaries,
    )
    return report


def get_report(report_id: str) -> PlayerReport | None:
    return REPORTS.get(report_id)


def revise_report(report_id: str, raw_revision_text: str) -> PlayerReport | None:
    report = REPORTS.get(report_id)
    if report is None:
        return None
    revised = report.model_copy(deep=True)
    revised.report_id = f"report-{uuid4().hex[:12]}"
    revised.version = report.version + 1
    revised.sections.append({"heading": "Revision", "content": raw_revision_text})
    revised.warnings.append("Report revision preserved prior evidence and assumptions.")
    REPORTS[revised.report_id] = revised
    return revised


def report_versions(report_id: str) -> list[PlayerReport]:
    report = REPORTS.get(report_id)
    return [report] if report else []


def templates_payload() -> list[dict]:
    return [template.model_dump(mode="json") for template in list_intent_templates()]
