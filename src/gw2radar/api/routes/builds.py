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
    get_character_snapshot,
    import_build,
    list_character_snapshots,
    list_builds,
    match_account_gear,
    recommend_budget_alternative,
    render_build_fit_report,
)
from gw2radar.commercial.patch_freshness import (
    build_freshness_notices,
    build_patch_freshness_report,
    render_patch_freshness_section,
)
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb.kb_repository import list_rules
from gw2radar.kb.kb_source_semantics import build_source_semantic_report
from gw2radar.kb.patch_impact_review import build_patch_review_dashboard

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


@router.get("/character-snapshots", response_model=ApiDataEnvelope)
def get_build_character_snapshots() -> ApiDataEnvelope:
    snapshots = [snapshot.model_dump(mode="json") for snapshot in list_character_snapshots()]
    return ApiDataEnvelope(
        data={
            "snapshots": snapshots,
            "boundary": "Manual sample snapshots only; verify actual character equipment in game.",
        }
    )


@router.get("/character-snapshots/{snapshot_id}/account-gear", response_model=ApiDataEnvelope)
def get_build_character_snapshot_account_gear(snapshot_id: str) -> ApiDataEnvelope:
    snapshot = get_character_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Character snapshot not found")
    return ApiDataEnvelope(
        data={
            "snapshot": snapshot.model_dump(mode="json"),
            "account_gear": snapshot.to_account_gear_snapshot().model_dump(mode="json"),
            "boundary": "This account gear payload is derived from a manual sample snapshot.",
        }
    )


@router.post("/fit", response_model=ApiDataEnvelope)
def post_build_fit(request: BuildFitRequest) -> ApiDataEnvelope:
    build = _load_build(request.build_id)
    result = evaluate_build_fit(build, request.account_gear)
    notices = _build_notices(build)
    return ApiDataEnvelope(
        data={
            "fit": result.model_dump(mode="json"),
            "patch_freshness_notices": [notice.model_dump(mode="json") for notice in notices],
        }
    )


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
    notices = _build_notices(build)
    freshness = build_patch_freshness_report([build], [], _patch_dashboard_items(), _source_semantics())
    markdown = render_build_fit_report(result)
    if notices:
        markdown = markdown.rstrip() + "\n\n" + "\n".join(render_patch_freshness_section(freshness)) + "\n"
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


@router.get("/{build_id}/patch-freshness", response_model=ApiDataEnvelope)
def get_build_patch_freshness(build_id: str) -> ApiDataEnvelope:
    build = _load_build(build_id)
    notices = _build_notices(build)
    return ApiDataEnvelope(
        data={
            "build_id": build_id,
            "notice_count": len(notices),
            "notices": [notice.model_dump(mode="json") for notice in notices],
        }
    )


def _load_build(build_id: str):
    init_db()
    with db_session.SessionLocal() as session:
        build = get_build(session, build_id)
    if build is None:
        raise HTTPException(status_code=404, detail="Build not found")
    return build


def _build_notices(build):
    return build_freshness_notices(build, _patch_dashboard_items(), _source_semantics())


def _patch_dashboard_items():
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    return build_patch_review_dashboard(rules)


def _source_semantics():
    return build_source_semantic_report()
