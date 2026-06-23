from fastapi import APIRouter, Body, HTTPException, Response
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
from gw2radar.commercial.report_productization import (
    ProductizedReportPacketZipVerificationAuditRequest,
    build_productized_report_packet_zip_bundle,
    generate_productized_report_artifact,
    list_productized_report_packet_zip_verification_audits,
    list_productized_report_templates,
    record_productized_report_packet_zip_verification_audit,
    render_productized_report_packet_zip_verification_audit_csv,
    render_productized_report_packet_zip_verification_audit_markdown,
    resolve_productized_report_artifact_path,
    verify_productized_report_packet_zip_bundle,
)
from gw2radar.commercial.build_fit import AccountGearSnapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.exports.package_builder import build_export_package
from gw2radar.kb.kb_repository import list_rules
from gw2radar.reports.markdown_report import generate_kb_backed_markdown_report, generate_markdown_report

router = APIRouter()

LOCAL_USER_ID = "local-user"


class ReportPreviewRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"
    report_type: str = "returner"


class ReportGenerateRequest(BaseModel):
    product_id: str
    goal_id: str = "gw2:goal:aurora"
    format: ReportExportFormat = ReportExportFormat.MARKDOWN
    knowledge_backed: bool = False


class ProductizedReportGenerateRequest(BaseModel):
    template_id: str
    format: str = "markdown"
    build_id: str | None = None
    account_gear: AccountGearSnapshot | None = None


@router.get("/reports/{goal_id}/markdown")
def get_markdown_report(goal_id: str) -> Response:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    return Response(
        content=generate_markdown_report(graph, goal_id),
        media_type="text/markdown; charset=utf-8",
    )


@router.get("/reports/{goal_id}/markdown/kb")
def get_kb_markdown_report(goal_id: str) -> Response:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    return Response(
        content=generate_kb_backed_markdown_report(graph, goal_id, rules),
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


@router.get("/api/v1/reports/productized/templates", response_model=ApiDataEnvelope)
def get_productized_report_templates() -> ApiDataEnvelope:
    templates = [template.model_dump(mode="json") for template in list_productized_report_templates()]
    return ApiDataEnvelope(
        data={
            "templates": templates,
            "boundary": "Templates are deterministic commercial report contracts; generation requires entitlement.",
        }
    )


@router.post("/api/v1/reports/productized/generate", response_model=ApiDataEnvelope)
def post_productized_report_generate(request: ProductizedReportGenerateRequest) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        try:
            manifest = generate_productized_report_artifact(
                session,
                graph,
                user_id=LOCAL_USER_ID,
                template_id=request.template_id,
                export_format=request.format,
                build_id=request.build_id,
                account_gear=request.account_gear,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"productized_report": manifest.model_dump(mode="json")})


@router.get("/api/v1/reports/productized/artifacts/bundle", response_model=None)
def get_productized_report_artifact_bundle(
    format: str = "zip",
    limit: int = 20,
) -> ApiDataEnvelope | Response:
    try:
        manifest, bundle_bytes = build_productized_report_packet_zip_bundle(limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if format == "manifest":
        return ApiDataEnvelope(data={"productized_report_packet_zip_bundle": manifest.model_dump(mode="json")})
    if format != "zip":
        raise HTTPException(status_code=400, detail="Unsupported bundle format")
    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{manifest.filename}"',
            "X-Checksum-SHA256": manifest.checksum_sha256,
        },
    )


@router.post("/api/v1/reports/productized/artifacts/bundle/verify", response_model=ApiDataEnvelope)
def post_productized_report_artifact_bundle_verify(
    bundle: bytes | None = Body(default=None, media_type="application/zip"),
    expected_checksum_sha256: str | None = None,
    limit: int = 20,
) -> ApiDataEnvelope:
    if bundle is None or len(bundle) == 0:
        manifest, bundle = build_productized_report_packet_zip_bundle(limit=limit)
        expected_checksum_sha256 = expected_checksum_sha256 or manifest.checksum_sha256
    verification = verify_productized_report_packet_zip_bundle(
        bundle,
        expected_checksum_sha256=expected_checksum_sha256,
    )
    return ApiDataEnvelope(data={"productized_report_packet_zip_verification": verification.model_dump(mode="json")})


@router.post("/api/v1/reports/productized/artifacts/bundle/verification-audit", response_model=ApiDataEnvelope)
def post_productized_report_artifact_bundle_verification_audit(
    request: ProductizedReportPacketZipVerificationAuditRequest,
) -> ApiDataEnvelope:
    try:
        record = record_productized_report_packet_zip_verification_audit(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={"productized_report_packet_zip_verification_audit_record": record.model_dump(mode="json")}
    )


@router.post("/api/v1/reports/productized/artifacts/bundle/verification-audit/upload", response_model=ApiDataEnvelope)
def post_productized_report_artifact_bundle_verification_audit_upload(
    bundle: bytes = Body(media_type="application/zip"),
    reviewer: str = "report-ops",
    expected_checksum_sha256: str | None = None,
) -> ApiDataEnvelope:
    request = ProductizedReportPacketZipVerificationAuditRequest(
        reviewer=reviewer,
        expected_checksum_sha256=expected_checksum_sha256,
        notes=["Productized report packet zip verification audit recorded from uploaded zip bytes."],
    )
    record = record_productized_report_packet_zip_verification_audit(request, bundle_bytes=bundle)
    return ApiDataEnvelope(
        data={"productized_report_packet_zip_verification_audit_record": record.model_dump(mode="json")}
    )


@router.get("/api/v1/reports/productized/artifacts/bundle/verification-audit", response_model=None)
def get_productized_report_artifact_bundle_verification_audit(
    reviewer: str | None = None,
    limit: int = 20,
    format: str = "json",
) -> ApiDataEnvelope | Response:
    audit = list_productized_report_packet_zip_verification_audits(reviewer=reviewer, limit=limit)
    if format == "markdown":
        return Response(
            content=render_productized_report_packet_zip_verification_audit_markdown(audit),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="productized_report_packet_zip_verification_audit.md"'},
        )
    if format == "csv":
        return Response(
            content=render_productized_report_packet_zip_verification_audit_csv(audit),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="productized_report_packet_zip_verification_audit.csv"'},
        )
    return ApiDataEnvelope(data={"productized_report_packet_zip_verification_audit": audit.model_dump(mode="json")})


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
        rules = list_rules(session) if request.knowledge_backed else []
        try:
            job = generate_report_job(
                session,
                graph,
                user_id=LOCAL_USER_ID,
                product_id=request.product_id,
                goal_id=request.goal_id,
                export_format=request.format,
                knowledge_backed=request.knowledge_backed,
                knowledge_rules=rules,
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
        path = resolve_productized_report_artifact_path(artifact_id)
    if path is None:
        raise HTTPException(status_code=404, detail="Report artifact not found")
    media_type = "text/html" if path.suffix == ".html" else "text/csv" if path.suffix == ".csv" else "text/markdown"
    return Response(content=path.read_text(encoding="utf-8"), media_type=f"{media_type}; charset=utf-8")
