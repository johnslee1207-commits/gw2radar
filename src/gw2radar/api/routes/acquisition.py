from fastapi import APIRouter, HTTPException

from gw2radar.acquisition.models import (
    AcquisitionJobInput,
    AcquisitionJobStatus,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    KbTarget,
    SourcePolicyInput,
)
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
from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(tags=["acquisition"])


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
