from fastapi import APIRouter, HTTPException, Response
from pathlib import Path

from gw2radar.api.state import get_graph
from gw2radar.exports.package_builder import build_export_package
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


@router.post("/reports/{goal_id}/export-package")
def post_export_package(goal_id: str) -> dict:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    package = build_export_package(graph, goal_id, Path("outputs"))
    return {
        "goal_id": package.goal_id,
        "output_dir": package.output_dir.as_posix(),
        "manifest_path": package.manifest_path.as_posix(),
        "files": [path.name for path in package.files],
    }
