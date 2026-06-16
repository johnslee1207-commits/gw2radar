from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.build_fit import (
    DEFAULT_USER_ID,
    AccountGearSnapshot,
    BuildImport,
    build_transition_plan,
    evaluate_build_fit,
    get_build,
    import_build,
    list_builds,
    match_account_gear,
    recommend_budget_alternative,
    render_build_fit_report,
)
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/builds", tags=["builds"])


class BuildFitRequest(BaseModel):
    build_id: str
    account_gear: AccountGearSnapshot = Field(default_factory=AccountGearSnapshot)


class BuildReportRequest(BuildFitRequest):
    format: ReportExportFormat = ReportExportFormat.MARKDOWN


@router.post("/import", response_model=ApiDataEnvelope)
def post_build_import(request: BuildImport) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        build = import_build(session, request, user_id=DEFAULT_USER_ID)
    return ApiDataEnvelope(data={"build": build.model_dump(mode="json")})


@router.get("", response_model=ApiDataEnvelope)
def get_builds() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        builds = [build.model_dump(mode="json") for build in list_builds(session, user_id=DEFAULT_USER_ID)]
    return ApiDataEnvelope(data={"builds": builds})


@router.post("/fit", response_model=ApiDataEnvelope)
def post_build_fit(request: BuildFitRequest) -> ApiDataEnvelope:
    build = _load_build(request.build_id)
    result = evaluate_build_fit(build, request.account_gear)
    return ApiDataEnvelope(data={"fit": result.model_dump(mode="json")})


@router.post("/transition-plan", response_model=ApiDataEnvelope)
def post_build_transition_plan(request: BuildFitRequest) -> ApiDataEnvelope:
    build = _load_build(request.build_id)
    matches = match_account_gear(build, request.account_gear)
    plan = build_transition_plan(build, matches)
    budget = recommend_budget_alternative(build, plan)
    return ApiDataEnvelope(
        data={
            "transition_plan": plan.model_dump(mode="json"),
            "budget_alternative": budget.model_dump(mode="json"),
        }
    )


@router.post("/report", response_model=ApiDataEnvelope)
def post_build_report(request: BuildReportRequest) -> ApiDataEnvelope:
    build = _load_build(request.build_id)
    result = evaluate_build_fit(build, request.account_gear)
    markdown = render_build_fit_report(result)
    init_db()
    with db_session.SessionLocal() as session:
        try:
            job = generate_report_job(
                session,
                get_graph(),
                user_id=DEFAULT_USER_ID,
                product_id="build_fit_report",
                goal_id="gw2:goal:aurora",
                export_format=request.format,
                markdown_override=markdown,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})


def _load_build(build_id: str):
    init_db()
    with db_session.SessionLocal() as session:
        build = get_build(session, build_id)
    if build is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return build
