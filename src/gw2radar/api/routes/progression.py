from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph, save_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.inference.progression_decision_engine import build_progression_decisions
from gw2radar.inference.seven_day_plan import (
    build_seven_day_plan,
    render_seven_day_plan_csv,
    render_seven_day_plan_markdown,
)
from gw2radar.kb.kb_repository import list_rules

router = APIRouter(prefix="/api/v1/progression", tags=["progression"])


class ProgressionDecisionRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"
    top_k: int = Field(default=5, ge=1, le=25)


@router.post("/decisions/top-k", response_model=ApiDataEnvelope)
def post_progression_decision_top_k(request: ProgressionDecisionRequest) -> ApiDataEnvelope:
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    result = build_progression_decisions(
        graph,
        request.goal_id,
        rules,
        top_k=request.top_k,
    )
    save_graph(graph)
    return ApiDataEnvelope(data={"decision_result": result.model_dump(mode="json")})


@router.post("/plans/7-day", response_model=ApiDataEnvelope)
def post_progression_seven_day_plan(request: ProgressionDecisionRequest) -> ApiDataEnvelope:
    plan = _build_plan(request)
    return ApiDataEnvelope(data={"seven_day_plan": plan.model_dump(mode="json")})


@router.post("/plans/7-day/export", response_model=None)
def post_progression_seven_day_plan_export(
    request: ProgressionDecisionRequest,
    format: str = "markdown",
) -> ApiDataEnvelope | Response:
    plan = _build_plan(request)
    if format == "json":
        return ApiDataEnvelope(data={"seven_day_plan": plan.model_dump(mode="json")})
    if format == "markdown":
        return Response(
            content=render_seven_day_plan_markdown(plan),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="gw2radar_7_day_plan.md"'},
        )
    if format == "csv":
        return Response(
            content=render_seven_day_plan_csv(plan),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="gw2radar_7_day_plan.csv"'},
        )
    raise HTTPException(status_code=400, detail="Unsupported 7-day plan export format.")


def _build_plan(request: ProgressionDecisionRequest):
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    decisions = build_progression_decisions(
        graph,
        request.goal_id,
        rules,
        top_k=request.top_k,
    )
    save_graph(graph)
    return build_seven_day_plan(decisions)
