from fastapi import APIRouter, HTTPException, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.returner_readiness import (
    build_returner_readiness_report,
    render_returner_readiness_markdown,
)

router = APIRouter(prefix="/api/v1/returner", tags=["returner"])


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
