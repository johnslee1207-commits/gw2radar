from fastapi import APIRouter, HTTPException, Query, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.commercial.achievement_route import (
    ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    AchievementRouteReviewedPromotionRequest,
    AchievementRouteRequest,
    OfficialAccountAchievementProgress,
    OfficialAchievementFetchPreviewRequest,
    OfficialAchievementRoutePreviewRequest,
    build_official_achievement_fetch_preview,
    build_achievement_route_plan,
    build_official_achievement_route_preview,
    list_achievement_route_promotion_audits,
    load_reviewed_achievement_route_steps,
    promote_official_fetch_preview_to_reviewed_manifest,
    record_achievement_route_promotion_audit,
    render_achievement_route_csv,
    render_achievement_route_markdown,
    render_achievement_route_promotion_audit_csv,
    render_achievement_route_promotion_audit_markdown,
    render_official_achievement_fetch_preview_markdown,
    render_official_achievement_route_preview_markdown,
)
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.security.api_key_store import EncryptedApiKeyStore

router = APIRouter(prefix="/api/v1/achievement-routes", tags=["achievement-routes"])
gateway_factory = Gw2ApiGateway
source_root = ACHIEVEMENT_ROUTE_SOURCE_ROOT
audit_root = ACHIEVEMENT_ROUTE_AUDIT_ROOT


@router.post("/plan", response_model=ApiDataEnvelope)
def post_achievement_route_plan(request: AchievementRouteRequest) -> ApiDataEnvelope:
    plan = build_achievement_route_plan(request, source_root)
    return ApiDataEnvelope(data={"plan": plan.model_dump(mode="json")})


@router.get("/sources", response_model=ApiDataEnvelope)
def get_achievement_route_sources() -> ApiDataEnvelope:
    _steps, summaries = load_reviewed_achievement_route_steps(source_root)
    return ApiDataEnvelope(
        data={
            "sources": [summary.model_dump(mode="json") for summary in summaries],
            "reviewed_step_count": len(_steps),
        }
    )


@router.post("/official-preview", response_model=ApiDataEnvelope)
def post_official_achievement_route_preview(request: OfficialAchievementRoutePreviewRequest) -> ApiDataEnvelope:
    preview = build_official_achievement_route_preview(request)
    return ApiDataEnvelope(data={"preview": preview.model_dump(mode="json")})


@router.post("/official-preview/export")
def post_official_achievement_route_preview_export(
    request: OfficialAchievementRoutePreviewRequest,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
) -> Response:
    preview = build_official_achievement_route_preview(request)
    if format == "markdown":
        return Response(
            content=render_official_achievement_route_preview_markdown(preview),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "json":
        return Response(
            content=preview.manifest.model_dump_json(indent=2),
            media_type="application/json; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported official achievement preview export format.")


@router.post("/official-fetch-preview", response_model=ApiDataEnvelope)
def post_official_achievement_fetch_preview(request: OfficialAchievementFetchPreviewRequest) -> ApiDataEnvelope:
    gateway = gateway_factory()
    progress, warnings = _load_account_progress_for_fetch_preview(request, gateway)
    preview = build_official_achievement_fetch_preview(
        request,
        gateway,
        account_achievements=progress,
        extra_warnings=warnings,
    )
    return ApiDataEnvelope(data={"fetch_preview": preview.model_dump(mode="json")})


@router.post("/official-fetch-preview/export")
def post_official_achievement_fetch_preview_export(
    request: OfficialAchievementFetchPreviewRequest,
    format: str = Query(default="markdown", pattern="^(markdown|json)$"),
) -> Response:
    gateway = gateway_factory()
    progress, warnings = _load_account_progress_for_fetch_preview(request, gateway)
    preview = build_official_achievement_fetch_preview(
        request,
        gateway,
        account_achievements=progress,
        extra_warnings=warnings,
    )
    if format == "markdown":
        return Response(
            content=render_official_achievement_fetch_preview_markdown(preview),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "json":
        return Response(
            content=preview.preview.manifest.model_dump_json(indent=2),
            media_type="application/json; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported official achievement fetch preview export format.")


@router.post("/official-fetch-preview/promote-reviewed", response_model=ApiDataEnvelope)
def post_official_achievement_fetch_preview_promote_reviewed(
    request: OfficialAchievementFetchPreviewRequest,
    review: AchievementRouteReviewedPromotionRequest,
) -> ApiDataEnvelope:
    gateway = gateway_factory()
    progress, warnings = _load_account_progress_for_fetch_preview(request, gateway)
    fetch_preview = build_official_achievement_fetch_preview(
        request,
        gateway,
        account_achievements=progress,
        extra_warnings=warnings,
    )
    try:
        result = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, source_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    audit_record = record_achievement_route_promotion_audit(result, fetch_preview, review, audit_root)
    return ApiDataEnvelope(data={"promotion": result.model_dump(mode="json"), "audit_record": audit_record.model_dump(mode="json")})


@router.get("/promotion-audit", response_model=None)
def get_achievement_route_promotion_audit(
    reviewer: str | None = None,
    source_id: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    audit_list = list_achievement_route_promotion_audits(
        audit_root,
        reviewer=reviewer,
        source_id=source_id,
        limit=limit,
    )
    if format == "markdown":
        return Response(
            content=render_achievement_route_promotion_audit_markdown(audit_list),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_promotion_audit_csv(audit_list),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"audit": audit_list.model_dump(mode="json")})


@router.post("/plan/export")
def post_achievement_route_export(
    request: AchievementRouteRequest,
    format: str = Query(default="markdown", pattern="^(markdown|csv)$"),
) -> Response:
    plan = build_achievement_route_plan(request, source_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_markdown(plan),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_csv(plan),
            media_type="text/csv; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported achievement route export format.")


def _load_account_progress_for_fetch_preview(
    request: OfficialAchievementFetchPreviewRequest,
    gateway: Gw2ApiGateway,
) -> tuple[list[OfficialAccountAchievementProgress], list[str]]:
    if request.account_achievements:
        return request.account_achievements, ["Using request-provided account achievement progress summary."]
    if not request.use_stored_account_progress:
        return [], ["Stored account achievement progress was not requested."]

    init_db()
    with db_session.SessionLocal() as session:
        api_key = EncryptedApiKeyStore(session).get()
    if not api_key:
        return [], ["Stored account achievement progress requested, but no API key is configured."]

    result = gateway.get("/v2/account/achievements", api_key=api_key, priority="P2")
    status = getattr(result.status, "value", str(result.status))
    if result.status not in {GatewayStatus.OK, GatewayStatus.CACHE_HIT}:
        return [], [f"Stored account achievement progress fetch returned status {status}."]
    progress = [
        OfficialAccountAchievementProgress.model_validate(item)
        for item in (result.payload or [])
        if isinstance(item, dict)
    ]
    return progress, [f"Loaded {len(progress)} account achievement progress rows from stored API key."]
