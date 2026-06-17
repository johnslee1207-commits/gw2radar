from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from gw2radar.acquisition.final_maturity_rollup import build_final_maturity_rollup, render_final_maturity_rollup_markdown
from gw2radar.acquisition.local_pdf_adapter import ingest_pdf_inventory_as_acquisition_sources
from gw2radar.acquisition.coverage import build_evidence_coverage_map, render_evidence_coverage_markdown
from gw2radar.acquisition.manual_adapter import (
    ManualNoteImportInput,
    WebSummaryImportInput,
    ingest_manual_note,
    ingest_web_summary,
)
from gw2radar.acquisition.maturity import build_acquisition_maturity_report, render_acquisition_maturity_markdown
from gw2radar.acquisition.models import (
    AcquisitionJobInput,
    AcquisitionJobStatus,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    KbTarget,
    SourcePolicyInput,
)
from gw2radar.acquisition.official_api_adapter import run_official_api_acquisition_job
from gw2radar.acquisition.promotion_action_plan import (
    build_acquisition_promotion_action_plans,
    render_acquisition_promotion_action_plans_markdown,
)
from gw2radar.acquisition.promotion_queue import (
    build_acquisition_promotion_queue,
    render_acquisition_promotion_queue_markdown,
)
from gw2radar.acquisition.promotion_readiness import (
    build_acquisition_promotion_readiness_report,
    render_acquisition_promotion_readiness_markdown,
)
from gw2radar.acquisition.promotion_release_manifest import (
    build_acquisition_promotion_release_manifest,
    render_acquisition_promotion_release_manifest_markdown,
)
from gw2radar.acquisition.promotion_workflow import (
    build_acquisition_promotion_workflow,
    render_acquisition_promotion_workflow_markdown,
)
from gw2radar.acquisition.readiness import build_acquisition_readiness_report, render_acquisition_readiness_markdown
from gw2radar.acquisition.repository import (
    create_job,
    get_job,
    get_source,
    get_source_health,
    list_jobs,
    list_sources,
    mark_job_skipped,
    mark_source_deprecated,
    mark_source_reviewed,
    register_source,
    upsert_policy,
)
from gw2radar.acquisition.seed_packs import (
    AcquisitionSeedPackId,
    get_acquisition_seed_pack,
    import_acquisition_seed_pack,
    list_acquisition_seed_packs,
)
from gw2radar.acquisition.worker import AcquisitionWorker
from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb_pdf.pdf_inventory import build_inventory
from gw2radar.security.api_key_store import EncryptedApiKeyStore

router = APIRouter(tags=["acquisition"])


class LocalPdfImportRequest(BaseModel):
    repo_root: str = "."
    source_root: str = "docs/knowledge_base/_sources/pdf"
    requested_by: str = "admin"


class RunOfficialApiJobRequest(BaseModel):
    api_key: str | None = None


class DrainAcquisitionJobRequest(BaseModel):
    worker_id: str = "acquisition-drain-one"
    use_stored_api_key: bool = True


class AcquisitionAdminWorkflowRequest(BaseModel):
    source: AcquisitionSourceInput | None = None
    source_id: str | None = None
    policy: SourcePolicyInput | None = None
    mark_reviewed: bool = False
    mark_deprecated: bool = False
    job: AcquisitionJobInput | None = None
    drain_one: bool = False
    worker_id: str = "acquisition-admin-workflow"
    use_stored_api_key: bool = True
    include_readiness: bool = True
    include_markdown_export: bool = False


class ImportAcquisitionSeedPackRequest(BaseModel):
    confirmed: bool = False


@router.post("/api/v1/sources", response_model=ApiDataEnvelope)
def post_source(request: AcquisitionSourceInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = register_source(session, request)
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.get("/api/v1/sources", response_model=ApiDataEnvelope)
def get_sources(
    source_type: AcquisitionSourceType | None = None,
    kb_target: KbTarget | None = None,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        sources = [
            source.model_dump(mode="json")
            for source in list_sources(
                session,
                source_type=source_type.value if source_type else None,
                kb_target=kb_target.value if kb_target else None,
            )
        ]
    return ApiDataEnvelope(data={"sources": sources})


@router.get("/api/v1/acquisition/seed-packs", response_model=ApiDataEnvelope)
def get_acquisition_seed_packs() -> ApiDataEnvelope:
    packs = list_acquisition_seed_packs()
    return ApiDataEnvelope(
        data={
            "count": len(packs),
            "packs": [pack.model_dump(mode="json") for pack in packs],
        }
    )


@router.get("/api/v1/acquisition/seed-packs/{pack_id}", response_model=ApiDataEnvelope)
def get_acquisition_seed_pack_route(pack_id: AcquisitionSeedPackId) -> ApiDataEnvelope:
    pack = get_acquisition_seed_pack(pack_id)
    return ApiDataEnvelope(data={"pack": pack.model_dump(mode="json")})


@router.post("/api/v1/acquisition/seed-packs/{pack_id}/import", response_model=ApiDataEnvelope)
def post_acquisition_seed_pack_import(
    pack_id: AcquisitionSeedPackId,
    request: ImportAcquisitionSeedPackRequest,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            result = import_acquisition_seed_pack(session, pack_id, confirmed=request.confirmed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"result": result.model_dump(mode="json")})


@router.get("/api/v1/sources/{source_id}", response_model=ApiDataEnvelope)
def get_source_detail(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = get_source(session, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Acquisition source not found.")
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.get("/api/v1/sources/{source_id}/health", response_model=ApiDataEnvelope)
def get_source_health_route(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            health = get_source_health(session, source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"health": health.model_dump(mode="json")})


@router.post("/api/v1/sources/{source_id}/policy", response_model=ApiDataEnvelope)
def post_source_policy(source_id: str, request: SourcePolicyInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            policy = upsert_policy(session, source_id, request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"policy": policy.model_dump(mode="json")})


@router.post("/api/v1/sources/{source_id}/mark-reviewed", response_model=ApiDataEnvelope)
def post_source_mark_reviewed(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            source = mark_source_reviewed(session, source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.post("/api/v1/sources/{source_id}/mark-deprecated", response_model=ApiDataEnvelope)
def post_source_mark_deprecated(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            source = mark_source_deprecated(session, source_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.post("/api/v1/acquisition/jobs", response_model=ApiDataEnvelope)
def post_acquisition_job(request: AcquisitionJobInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            job = create_job(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


@router.get("/api/v1/acquisition/jobs", response_model=ApiDataEnvelope)
def get_acquisition_jobs(
    source_id: str | None = None,
    status: AcquisitionJobStatus | None = None,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        jobs = [job.model_dump(mode="json") for job in list_jobs(session, source_id=source_id, status=status)]
    return ApiDataEnvelope(data={"jobs": jobs})


@router.get("/api/v1/acquisition/jobs/{job_id}", response_model=ApiDataEnvelope)
def get_acquisition_job(job_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        job = get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Acquisition job not found.")
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


@router.post("/api/v1/acquisition/jobs/drain-one", response_model=ApiDataEnvelope)
def post_acquisition_jobs_drain_one(request: DrainAcquisitionJobRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        api_key_provider = (
            (lambda: EncryptedApiKeyStore(session).get())
            if request.use_stored_api_key
            else (lambda: None)
        )
        result = AcquisitionWorker(session, api_key_provider=api_key_provider).drain_one(worker_id=request.worker_id)
    return ApiDataEnvelope(data=result)


@router.post("/api/v1/acquisition/admin/workflow", response_model=ApiDataEnvelope)
def post_acquisition_admin_workflow(request: AcquisitionAdminWorkflowRequest) -> ApiDataEnvelope:
    if request.mark_reviewed and request.mark_deprecated:
        raise HTTPException(status_code=400, detail="Cannot mark a source reviewed and deprecated in the same workflow.")
    init_db()
    with db_session.SessionLocal() as session:
        steps: list[dict] = []
        source_id = request.source_id
        if request.source is not None:
            source = register_source(session, request.source)
            source_id = source.source_id
            steps.append({"step": "source_created", "source": source.model_dump(mode="json")})
        if source_id is None and any([request.policy, request.mark_reviewed, request.mark_deprecated, request.job]):
            raise HTTPException(status_code=400, detail="source_id or source is required for source-scoped workflow steps.")
        if request.policy is not None and source_id is not None:
            try:
                policy = upsert_policy(session, source_id, request.policy)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            steps.append({"step": "policy_upserted", "policy": policy.model_dump(mode="json")})
        if request.mark_reviewed and source_id is not None:
            try:
                source = mark_source_reviewed(session, source_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            steps.append({"step": "source_reviewed", "source": source.model_dump(mode="json")})
        if request.mark_deprecated and source_id is not None:
            try:
                source = mark_source_deprecated(session, source_id)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            steps.append({"step": "source_deprecated", "source": source.model_dump(mode="json")})
        if request.job is not None:
            if source_id is not None and request.job.source_id != source_id:
                raise HTTPException(status_code=400, detail="Workflow job.source_id must match the workflow source_id.")
            try:
                job = create_job(session, request.job)
            except ValueError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            steps.append({"step": "job_created", "job": job.model_dump(mode="json")})
        if request.drain_one:
            api_key_provider = (
                (lambda: EncryptedApiKeyStore(session).get())
                if request.use_stored_api_key
                else (lambda: None)
            )
            drained = AcquisitionWorker(session, api_key_provider=api_key_provider).drain_one(worker_id=request.worker_id)
            steps.append({"step": "drain_one", "result": drained})

        data: dict = {"steps": steps}
        if request.include_readiness:
            report = build_acquisition_readiness_report(session)
            data["readiness"] = report.model_dump(mode="json")
            if request.include_markdown_export:
                data["readiness_markdown"] = render_acquisition_readiness_markdown(report)
    return ApiDataEnvelope(data=data)


@router.post("/api/v1/acquisition/jobs/{job_id}/run-once", response_model=ApiDataEnvelope)
def post_acquisition_job_run_once(job_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            job = mark_job_skipped(
                session,
                job_id,
                error_code="adapter_not_implemented",
                error="P18 registers acquisition jobs but does not execute source adapters yet.",
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


@router.post("/api/v1/acquisition/jobs/{job_id}/run-official-api", response_model=ApiDataEnvelope)
def post_acquisition_job_run_official_api(job_id: str, request: RunOfficialApiJobRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            result = run_official_api_acquisition_job(session, job_id, api_key=request.api_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={
            "job": result.job.model_dump(mode="json"),
            "gateway_status": result.gateway_status,
            "evidence_created": result.evidence_created,
            "gateway_evidence_id": result.gateway_evidence_id,
        }
    )


@router.post("/api/v1/acquisition/local-pdf/import", response_model=ApiDataEnvelope)
def post_local_pdf_import(request: LocalPdfImportRequest) -> ApiDataEnvelope:
    from pathlib import Path

    repo_root = Path(request.repo_root).resolve()
    source_root = (repo_root / request.source_root).resolve()
    if not source_root.exists():
        raise HTTPException(status_code=400, detail="Local PDF source root does not exist.")
    records = build_inventory(repo_root, source_root)
    init_db()
    with db_session.SessionLocal() as session:
        result = ingest_pdf_inventory_as_acquisition_sources(session, records, requested_by=request.requested_by)
    return ApiDataEnvelope(
        data={
            "result": {
                "source_count": result.source_count,
                "new_source_count": result.new_source_count,
                "raw_evidence_count": result.evidence_count,
                "new_raw_evidence_count": result.new_evidence_count,
                "acquisition_job_count": result.job_count,
            }
        }
    )


@router.post("/api/v1/acquisition/manual-note/import", response_model=ApiDataEnvelope)
def post_manual_note_import(request: ManualNoteImportInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        result = ingest_manual_note(session, request)
    return ApiDataEnvelope(data={"result": result.__dict__})


@router.post("/api/v1/acquisition/web-summary/import", response_model=ApiDataEnvelope)
def post_web_summary_import(request: WebSummaryImportInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        result = ingest_web_summary(session, request)
    return ApiDataEnvelope(data={"result": result.__dict__})


@router.get("/api/v1/acquisition/readiness", response_model=ApiDataEnvelope)
def get_acquisition_readiness() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_readiness_report(session)
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/api/v1/acquisition/readiness/export")
def get_acquisition_readiness_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_readiness_report(session)
    if format == "markdown":
        return Response(
            content=render_acquisition_readiness_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition readiness export format.")


@router.get("/api/v1/acquisition/maturity", response_model=ApiDataEnvelope)
def get_acquisition_maturity() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_maturity_report(session)
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/api/v1/acquisition/maturity/export")
def get_acquisition_maturity_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_maturity_report(session)
    if format == "markdown":
        return Response(
            content=render_acquisition_maturity_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition maturity export format.")


@router.get("/api/v1/acquisition/evidence-coverage", response_model=ApiDataEnvelope)
def get_acquisition_evidence_coverage() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_evidence_coverage_map(session)
    return ApiDataEnvelope(data={"coverage": report.model_dump(mode="json")})


@router.get("/api/v1/acquisition/evidence-coverage/export")
def get_acquisition_evidence_coverage_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_evidence_coverage_map(session)
    if format == "markdown":
        return Response(
            content=render_evidence_coverage_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition evidence coverage export format.")


@router.get("/api/v1/acquisition/promotion-queue", response_model=ApiDataEnvelope)
def get_acquisition_promotion_queue() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        queue = build_acquisition_promotion_queue(session)
    return ApiDataEnvelope(data={"queue": queue.model_dump(mode="json")})


@router.get("/api/v1/acquisition/promotion-queue/export")
def get_acquisition_promotion_queue_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        queue = build_acquisition_promotion_queue(session)
    if format == "markdown":
        return Response(
            content=render_acquisition_promotion_queue_markdown(queue),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition promotion queue export format.")


@router.get("/api/v1/acquisition/promotion-readiness", response_model=ApiDataEnvelope)
def get_acquisition_promotion_readiness() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_promotion_readiness_report(session)
    return ApiDataEnvelope(data={"report": report.model_dump(mode="json")})


@router.get("/api/v1/acquisition/promotion-readiness/export")
def get_acquisition_promotion_readiness_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_acquisition_promotion_readiness_report(session)
    if format == "markdown":
        return Response(
            content=render_acquisition_promotion_readiness_markdown(report),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition promotion readiness export format.")


@router.get("/api/v1/acquisition/promotion-workflow", response_model=ApiDataEnvelope)
def get_acquisition_promotion_workflow(
    priority: str | None = None,
    item_type: str | None = None,
    limit: int = 25,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        workflow = build_acquisition_promotion_workflow(
            session,
            priority=priority,
            item_type=item_type,
            limit=limit,
        )
    return ApiDataEnvelope(data={"workflow": workflow.model_dump(mode="json")})


@router.get("/api/v1/acquisition/promotion-workflow/export")
def get_acquisition_promotion_workflow_export(
    format: str = "markdown",
    priority: str | None = None,
    item_type: str | None = None,
    limit: int = 25,
) -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        workflow = build_acquisition_promotion_workflow(
            session,
            priority=priority,
            item_type=item_type,
            limit=limit,
        )
    if format == "markdown":
        return Response(
            content=render_acquisition_promotion_workflow_markdown(workflow),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition promotion workflow export format.")


@router.get("/api/v1/acquisition/promotion-action-plans", response_model=ApiDataEnvelope)
def get_acquisition_promotion_action_plans(
    item_id: str | None = None,
    limit: int = 50,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        bundle = build_acquisition_promotion_action_plans(session, item_id=item_id, limit=limit)
    return ApiDataEnvelope(data={"bundle": bundle.model_dump(mode="json")})


@router.get("/api/v1/acquisition/promotion-action-plans/export")
def get_acquisition_promotion_action_plans_export(
    format: str = "markdown",
    item_id: str | None = None,
    limit: int = 50,
) -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        bundle = build_acquisition_promotion_action_plans(session, item_id=item_id, limit=limit)
    if format == "markdown":
        return Response(
            content=render_acquisition_promotion_action_plans_markdown(bundle),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition promotion action plans export format.")


@router.get("/api/v1/acquisition/promotion-release-manifest", response_model=ApiDataEnvelope)
def get_acquisition_promotion_release_manifest() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        manifest = build_acquisition_promotion_release_manifest(session)
    return ApiDataEnvelope(data={"manifest": manifest.model_dump(mode="json")})


@router.get("/api/v1/acquisition/promotion-release-manifest/export")
def get_acquisition_promotion_release_manifest_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        manifest = build_acquisition_promotion_release_manifest(session)
    if format == "markdown":
        return Response(
            content=render_acquisition_promotion_release_manifest_markdown(manifest),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported acquisition promotion release manifest export format.")


@router.get("/api/v1/acquisition/final-maturity-rollup", response_model=ApiDataEnvelope)
def get_final_maturity_rollup() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        rollup = build_final_maturity_rollup(session)
    return ApiDataEnvelope(data={"rollup": rollup.model_dump(mode="json")})


@router.get("/api/v1/acquisition/final-maturity-rollup/export")
def get_final_maturity_rollup_export(format: str = "markdown") -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        rollup = build_final_maturity_rollup(session)
    if format == "markdown":
        return Response(
            content=render_final_maturity_rollup_markdown(rollup),
            media_type="text/markdown; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported final maturity rollup export format.")
