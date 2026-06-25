from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.player_os.intent.intent_templates import get_intent_template, list_intent_templates
from gw2radar.player_os.orchestration import player_os_orchestrator as os
from gw2radar.player_os.trial_feedback_review import review_player_os_trial_feedback


router = APIRouter(prefix="/api/v1", tags=["player-os"])


class IntentParseRequest(BaseModel):
    raw_text: str | None = None
    template_id: str | None = None
    constraints: dict = Field(default_factory=dict)


class IntentStartRequest(IntentParseRequest):
    pass


class ConstraintUpdateRequest(BaseModel):
    constraints: dict = Field(default_factory=dict)


class ClarifyRequest(BaseModel):
    raw_text: str


class WorkflowAnswerRequest(BaseModel):
    answer: dict = Field(default_factory=dict)


class PlanReviseRequest(BaseModel):
    raw_revision_text: str
    constraints_delta: dict = Field(default_factory=dict)
    requested_by: str = "local-player"


class WhatIfRequest(BaseModel):
    raw_text: str
    constraints_delta: dict = Field(default_factory=dict)


class ReportReviseRequest(BaseModel):
    raw_revision_text: str


class TrialFeedbackReviewRequest(BaseModel):
    feedback: dict = Field(default_factory=dict)


@router.post("/intents/parse", response_model=ApiDataEnvelope)
def post_intent_parse(request: IntentParseRequest) -> ApiDataEnvelope:
    result = os.parse_intent(
        raw_text=request.raw_text,
        template_id=request.template_id,
        ui_constraints=request.constraints,
    )
    return ApiDataEnvelope(data={"intent_parse": result.model_dump(mode="json")})


@router.post("/intents/start", response_model=ApiDataEnvelope)
def post_intent_start(request: IntentStartRequest) -> ApiDataEnvelope:
    result = os.start_intent(
        raw_text=request.raw_text,
        template_id=request.template_id,
        ui_constraints=request.constraints,
    )
    return ApiDataEnvelope(data={"intent_start": result.model_dump(mode="json")})


@router.get("/intents/{intent_id}", response_model=ApiDataEnvelope)
def get_intent(intent_id: str) -> ApiDataEnvelope:
    intent = os.get_intent(intent_id)
    if intent is None:
        raise HTTPException(status_code=404, detail="Intent not found")
    return ApiDataEnvelope(data={"intent": intent.model_dump(mode="json")})


@router.post("/intents/{intent_id}/constraints", response_model=ApiDataEnvelope)
def post_intent_constraints(intent_id: str, request: ConstraintUpdateRequest) -> ApiDataEnvelope:
    intent = os.update_intent_constraints(intent_id, request.constraints)
    if intent is None:
        raise HTTPException(status_code=404, detail="Intent not found")
    return ApiDataEnvelope(data={"intent": intent.model_dump(mode="json")})


@router.post("/intents/{intent_id}/clarify", response_model=ApiDataEnvelope)
def post_intent_clarify(intent_id: str, request: ClarifyRequest) -> ApiDataEnvelope:
    result = os.clarify_intent(intent_id, request.raw_text)
    if result is None:
        raise HTTPException(status_code=404, detail="Intent not found")
    return ApiDataEnvelope(data={"intent_start": result.model_dump(mode="json")})


@router.get("/templates", response_model=ApiDataEnvelope)
def get_templates() -> ApiDataEnvelope:
    return ApiDataEnvelope(data={"templates": [template.model_dump(mode="json") for template in list_intent_templates()]})


@router.get("/templates/{template_id}", response_model=ApiDataEnvelope)
def get_template(template_id: str) -> ApiDataEnvelope:
    template = get_intent_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return ApiDataEnvelope(data={"template": template.model_dump(mode="json")})


@router.post("/templates/{template_id}/start", response_model=ApiDataEnvelope)
def post_template_start(template_id: str) -> ApiDataEnvelope:
    try:
        result = os.start_template(template_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Template not found") from exc
    return ApiDataEnvelope(data={"intent_start": result.model_dump(mode="json")})


@router.get("/workflows/{workflow_id}", response_model=ApiDataEnvelope)
def get_workflow(workflow_id: str) -> ApiDataEnvelope:
    workflow = os.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return ApiDataEnvelope(data={"workflow": workflow.model_dump(mode="json")})


@router.post("/workflows/{workflow_id}/next", response_model=ApiDataEnvelope)
def post_workflow_next(workflow_id: str) -> ApiDataEnvelope:
    workflow = os.advance_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return ApiDataEnvelope(data={"workflow": workflow.model_dump(mode="json")})


@router.post("/workflows/{workflow_id}/answer", response_model=ApiDataEnvelope)
def post_workflow_answer(workflow_id: str, request: WorkflowAnswerRequest) -> ApiDataEnvelope:
    workflow = os.answer_workflow(workflow_id, request.answer)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return ApiDataEnvelope(data={"workflow": workflow.model_dump(mode="json")})


@router.post("/workflows/{workflow_id}/cancel", response_model=ApiDataEnvelope)
def post_workflow_cancel(workflow_id: str) -> ApiDataEnvelope:
    workflow = os.cancel_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return ApiDataEnvelope(data={"workflow": workflow.model_dump(mode="json")})


@router.get("/plans/{plan_id}", response_model=ApiDataEnvelope)
def get_plan(plan_id: str) -> ApiDataEnvelope:
    plan = os.get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return ApiDataEnvelope(data={"plan": plan.model_dump(mode="json")})


@router.post("/plans/{plan_id}/revise", response_model=ApiDataEnvelope)
def post_plan_revise(plan_id: str, request: PlanReviseRequest) -> ApiDataEnvelope:
    result = os.revise_existing_plan(plan_id, request.raw_revision_text, request.constraints_delta)
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    revised, diff, report = result
    return ApiDataEnvelope(
        data={
            "plan": revised.model_dump(mode="json"),
            "diff": diff.model_dump(mode="json"),
            "report_preview": report.model_dump(mode="json"),
        }
    )


@router.post("/plans/{plan_id}/what-if", response_model=ApiDataEnvelope)
def post_plan_what_if(plan_id: str, request: WhatIfRequest) -> ApiDataEnvelope:
    result = os.what_if_plan(plan_id, request.raw_text, request.constraints_delta)
    if result is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return ApiDataEnvelope(data={"what_if": result.model_dump(mode="json")})


@router.get("/plans/{plan_id}/diff/{previous_version}", response_model=ApiDataEnvelope)
def get_plan_diff(plan_id: str, previous_version: str) -> ApiDataEnvelope:
    result = os.diff_plan(previous_version, plan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Plan diff not found")
    return ApiDataEnvelope(data={"diff": result})


@router.get("/reports/{report_id}", response_model=ApiDataEnvelope)
def get_player_os_report(report_id: str) -> ApiDataEnvelope:
    report = os.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.post("/reports/{report_id}/revise", response_model=ApiDataEnvelope)
def post_player_os_report_revise(report_id: str, request: ReportReviseRequest) -> ApiDataEnvelope:
    report = os.revise_report(report_id, request.raw_revision_text)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/reports/{report_id}/versions", response_model=ApiDataEnvelope)
def get_player_os_report_versions(report_id: str) -> ApiDataEnvelope:
    reports = os.report_versions(report_id)
    if not reports:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiDataEnvelope(data={"versions": [report.model_dump(mode="json") for report in reports]})


@router.get("/now", response_model=ApiDataEnvelope)
def get_now() -> ApiDataEnvelope:
    plan = os.build_now_result()
    return ApiDataEnvelope(data={"now": plan.model_dump(mode="json")})


@router.post("/now/recompute", response_model=ApiDataEnvelope)
def post_now_recompute() -> ApiDataEnvelope:
    plan = os.build_now_result()
    return ApiDataEnvelope(data={"now": plan.model_dump(mode="json")})


@router.post("/player-os/trial-feedback/review", response_model=ApiDataEnvelope)
def post_player_os_trial_feedback_review(request: TrialFeedbackReviewRequest) -> ApiDataEnvelope:
    review = review_player_os_trial_feedback(request.feedback)
    return ApiDataEnvelope(data={"trial_feedback_review": review.model_dump(mode="json")})
