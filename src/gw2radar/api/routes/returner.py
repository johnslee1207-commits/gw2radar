from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.commercial.returner_readiness import (
    build_returner_readiness_report,
    render_returner_full_report_markdown,
    render_returner_readiness_markdown,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/returner", tags=["returner"])


class ReturnerReportRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"
    format: ReportExportFormat = ReportExportFormat.MARKDOWN


@router.get("/readiness", response_model=ApiDataEnvelope)
def get_returner_readiness(goal_id: str = "gw2:goal:aurora") -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    report = build_returner_readiness_report(graph, goal_id)
    return ApiDataEnvelope(data={"readiness": report.model_dump(mode="json")})


@router.get("/readiness/export")
def get_returner_readiness_export(goal_id: str = "gw2:goal:aurora", format: str = "markdown") -> Response:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    if format != "markdown":
        raise HTTPException(status_code=400, detail="Unsupported returner readiness export format.")
    report = build_returner_readiness_report(graph, goal_id)
    return Response(
        content=render_returner_readiness_markdown(report),
        media_type="text/markdown; charset=utf-8",
    )


@router.post("/report", response_model=ApiDataEnvelope)
def post_returner_full_report(request: ReturnerReportRequest) -> ApiDataEnvelope:
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    report = build_returner_readiness_report(graph, request.goal_id)
    markdown = render_returner_full_report_markdown(report)
    init_db()
    with db_session.SessionLocal() as session:
        try:
            job = generate_report_job(
                session,
                graph,
                user_id="local-user",
                product_id="returner_full_report",
                goal_id=request.goal_id,
                export_format=request.format,
                markdown_override=markdown,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})
