from fastapi import APIRouter, HTTPException, Response

from gw2radar.api.state import get_graph
from gw2radar.reports.markdown_report import generate_markdown_report

router = APIRouter()


@router.get("/reports/{goal_id}/markdown")
def get_markdown_report(goal_id: str) -> Response:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Response(
        content=generate_markdown_report(graph, goal_id),
        media_type="text/markdown; charset=utf-8",
    )
