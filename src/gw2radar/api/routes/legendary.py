from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.legendary_planner import (
    DEFAULT_USER_ID,
    LegendaryGoalInput,
    add_legendary_goal,
    ensure_default_portfolio,
    get_portfolio,
    recompute_legendary_plan,
    render_legendary_planner_report,
)
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/legendary", tags=["legendary"])


class LegendaryReportRequest(BaseModel):
    format: ReportExportFormat = ReportExportFormat.MARKDOWN


@router.post("/goals", response_model=ApiDataEnvelope)
def post_legendary_goal(request: LegendaryGoalInput) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        try:
            goal = add_legendary_goal(
                session,
                graph,
                request.graph_goal_id,
                user_id=DEFAULT_USER_ID,
                priority=request.priority,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"goal": goal.model_dump(mode="json")})


@router.get("/portfolio", response_model=ApiDataEnvelope)
def get_legendary_portfolio() -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        portfolio = ensure_default_portfolio(session, graph, user_id=DEFAULT_USER_ID)
    return ApiDataEnvelope(data={"portfolio": portfolio.model_dump(mode="json")})


@router.post("/recompute", response_model=ApiDataEnvelope)
def post_legendary_recompute() -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        result = recompute_legendary_plan(session, graph, user_id=DEFAULT_USER_ID)
    return ApiDataEnvelope(data={"planner": result.model_dump(mode="json")})


@router.get("/do-not-sell", response_model=ApiDataEnvelope)
def get_legendary_do_not_sell() -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        result = recompute_legendary_plan(session, graph, user_id=DEFAULT_USER_ID)
    return ApiDataEnvelope(
        data={"do_not_sell": [item.model_dump(mode="json") for item in result.do_not_sell]}
    )


@router.post("/report", response_model=ApiDataEnvelope)
def post_legendary_report(request: LegendaryReportRequest) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        result = recompute_legendary_plan(session, graph, user_id=DEFAULT_USER_ID)
        markdown = render_legendary_planner_report(result)
        try:
            job = generate_report_job(
                session,
                graph,
                user_id=DEFAULT_USER_ID,
                product_id="legendary_planner_pro_report",
                goal_id=result.portfolio.goals[0].graph_goal_id,
                export_format=request.format,
                markdown_override=markdown,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})
