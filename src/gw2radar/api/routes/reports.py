from fastapi import APIRouter, HTTPException, Response
from pathlib import Path
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.report_engine import (
    ReportExportFormat,
    generate_report_job,
    generate_report_preview,
    get_report_job,
    list_report_products,
    resolve_artifact_path,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.exports.package_builder import build_export_package
from gw2radar.reports.markdown_report import generate_markdown_report

router = APIRouter()

LOCAL_USER_ID = "local-user"


class ReportPreviewRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"
    report_type: str = "returner"


class ReportGenerateRequest(BaseModel):
    product_id: str
    goal_id: str = "gw2:goal:aurora"
    format: ReportExportFormat = ReportExportFormat.MARKDOWN


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


@router.get("/api/v1/reports/products", response_model=ApiDataEnvelope)
def get_report_products() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        products = [product.model_dump(mode="json") for product in list_report_products(session)]
    return ApiDataEnvelope(data={"products": products})


@router.post("/api/v1/reports/preview", response_model=ApiDataEnvelope)
def post_report_preview(request: ReportPreviewRequest) -> ApiDataEnvelope:
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    preview = generate_report_preview(graph, request.goal_id, request.report_type)
    return ApiDataEnvelope(data=preview)


@router.post("/api/v1/reports/generate", response_model=ApiDataEnvelope)
def post_report_generate(request: ReportGenerateRequest) -> ApiDataEnvelope:
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        try:
            job = generate_report_job(
                session,
                graph,
                user_id=LOCAL_USER_ID,
                product_id=request.product_id,
                goal_id=request.goal_id,
                export_format=request.format,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


@router.get("/api/v1/reports/jobs/{job_id}", response_model=ApiDataEnvelope)
def get_report_export_job(job_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        job = get_report_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Report job not found")
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


@router.get("/api/v1/reports/artifacts/{artifact_id}")
def get_report_artifact(artifact_id: str) -> Response:
    path = resolve_artifact_path(artifact_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Report artifact not found")
    media_type = "text/html" if path.suffix == ".html" else "text/markdown"
    return Response(content=path.read_text(encoding="utf-8"), media_type=f"{media_type}; charset=utf-8")
