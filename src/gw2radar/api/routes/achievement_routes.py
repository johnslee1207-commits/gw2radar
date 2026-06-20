import json

from fastapi import APIRouter, HTTPException, Query, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.commercial.achievement_route import (
    ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    AchievementRouteOperatorActionBundleRequest,
    AchievementRouteBackfillCandidateReviewRequest,
    AchievementRouteReviewedPromotionRequest,
    AchievementRouteRemediationReviewRequest,
    AchievementRouteRequest,
    AchievementRouteDraftSourcePromotionRequest,
    AchievementRouteSourceEditPatchApplyRequest,
    OfficialAccountAchievementProgress,
    OfficialAchievementFetchPreviewRequest,
    OfficialAchievementRoutePreviewRequest,
    build_achievement_route_backfill_candidates,
    build_achievement_route_backfill_candidate_readiness,
    build_achievement_route_operator_action_bundle,
    build_achievement_route_operator_release_packet,
    build_achievement_route_release_readiness,
    build_achievement_route_remediation_queue,
    build_achievement_route_remediation_readiness,
    build_achievement_route_source_edit_patch_draft,
    build_achievement_route_source_quality_review,
    build_official_achievement_fetch_preview,
    build_achievement_route_plan,
    build_official_achievement_route_preview,
    apply_achievement_route_source_edit_patch_draft,
    promote_draft_achievement_route_source_to_reviewed,
    list_achievement_route_promotion_audits,
    list_achievement_route_backfill_candidate_review_audits,
    list_achievement_route_draft_source_promotion_audits,
    list_achievement_route_remediation_review_audits,
    list_achievement_route_source_edit_patch_apply_audits,
    load_reviewed_achievement_route_steps,
    promote_official_fetch_preview_to_reviewed_manifest,
    record_achievement_route_promotion_audit,
    record_achievement_route_backfill_candidate_review,
    record_achievement_route_remediation_review,
    render_achievement_route_csv,
    render_achievement_route_backfill_candidate_readiness_csv,
    render_achievement_route_backfill_candidate_readiness_markdown,
    render_achievement_route_backfill_candidate_review_audit_csv,
    render_achievement_route_backfill_candidate_review_audit_markdown,
    render_achievement_route_backfill_candidates_csv,
    render_achievement_route_backfill_candidates_markdown,
    render_achievement_route_markdown,
    render_achievement_route_operator_action_bundle_csv,
    render_achievement_route_operator_action_bundle_markdown,
    render_achievement_route_operator_release_packet_csv,
    render_achievement_route_operator_release_packet_markdown,
    render_achievement_route_promotion_audit_csv,
    render_achievement_route_promotion_audit_markdown,
    render_achievement_route_release_readiness_csv,
    render_achievement_route_release_readiness_markdown,
    render_achievement_route_remediation_queue_csv,
    render_achievement_route_remediation_queue_markdown,
    render_achievement_route_remediation_readiness_csv,
    render_achievement_route_remediation_readiness_markdown,
    render_achievement_route_remediation_review_audit_csv,
    render_achievement_route_remediation_review_audit_markdown,
    render_achievement_route_source_edit_patch_draft_csv,
    render_achievement_route_source_edit_patch_draft_markdown,
    render_achievement_route_source_edit_patch_apply_audit_csv,
    render_achievement_route_source_edit_patch_apply_audit_markdown,
    render_achievement_route_draft_source_promotion_audit_csv,
    render_achievement_route_draft_source_promotion_audit_markdown,
    render_achievement_route_source_quality_csv,
    render_achievement_route_source_quality_markdown,
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


@router.get("/release-readiness", response_model=None)
def get_achievement_route_release_readiness(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    readiness = build_achievement_route_release_readiness(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_release_readiness_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_release_readiness_csv(readiness),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"readiness": readiness.model_dump(mode="json")})


@router.get("/source-quality", response_model=None)
def get_achievement_route_source_quality(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    review = build_achievement_route_source_quality_review(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_source_quality_markdown(review),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_source_quality_csv(review),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"quality": review.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue", response_model=None)
def get_achievement_route_remediation_queue(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    queue = build_achievement_route_remediation_queue(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_remediation_queue_markdown(queue),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_remediation_queue_csv(queue),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"remediation_queue": queue.model_dump(mode="json")})


@router.post("/source-quality/remediation-queue/review", response_model=ApiDataEnvelope)
def post_achievement_route_remediation_review(request: AchievementRouteRemediationReviewRequest) -> ApiDataEnvelope:
    try:
        record = record_achievement_route_remediation_review(request, source_root, audit_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"remediation_review": record.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/review-audit", response_model=None)
def get_achievement_route_remediation_review_audit(
    reviewer: str | None = None,
    status: str | None = Query(default=None, pattern="^(acknowledged|resolved|deferred)$"),
    item_id: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    audit_list = list_achievement_route_remediation_review_audits(
        audit_root,
        reviewer=reviewer,
        status=status,
        item_id=item_id,
        limit=limit,
    )
    if format == "markdown":
        return Response(
            content=render_achievement_route_remediation_review_audit_markdown(audit_list),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_remediation_review_audit_csv(audit_list),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"remediation_review_audit": audit_list.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/readiness", response_model=None)
def get_achievement_route_remediation_readiness(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    readiness = build_achievement_route_remediation_readiness(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_remediation_readiness_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_remediation_readiness_csv(readiness),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"remediation_readiness": readiness.model_dump(mode="json")})


@router.post("/source-quality/remediation-queue/action-bundle", response_model=None)
def post_achievement_route_operator_action_bundle(
    request: AchievementRouteOperatorActionBundleRequest | None = None,
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    try:
        bundle = build_achievement_route_operator_action_bundle(request, source_root, audit_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if format == "markdown":
        return Response(
            content=render_achievement_route_operator_action_bundle_markdown(bundle),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_operator_action_bundle_csv(bundle),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"operator_action_bundle": bundle.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/release-packet", response_model=None)
def get_achievement_route_operator_release_packet(
    format: str = Query(default="json", pattern="^(json|markdown|csv|manifest)$"),
):
    packet = build_achievement_route_operator_release_packet(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_operator_release_packet_markdown(packet),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_operator_release_packet_csv(packet),
            media_type="text/csv; charset=utf-8",
        )
    if format == "manifest":
        return Response(
            content=json.dumps(packet.manifest, indent=2),
            media_type="application/json; charset=utf-8",
        )
    return ApiDataEnvelope(data={"operator_release_packet": packet.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates", response_model=None)
def get_achievement_route_backfill_candidates(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    export = build_achievement_route_backfill_candidates(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_backfill_candidates_markdown(export),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_backfill_candidates_csv(export),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"backfill_candidates": export.model_dump(mode="json")})


@router.post("/source-quality/remediation-queue/backfill-candidates/review", response_model=None)
def post_achievement_route_backfill_candidate_review(request: AchievementRouteBackfillCandidateReviewRequest):
    try:
        record = record_achievement_route_backfill_candidate_review(request, source_root, audit_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"backfill_candidate_review": record.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates/review-audit", response_model=None)
def get_achievement_route_backfill_candidate_review_audit(
    reviewer: str | None = None,
    status: str | None = Query(default=None, pattern="^(acknowledged|resolved|deferred)$"),
    candidate_id: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    audit = list_achievement_route_backfill_candidate_review_audits(
        audit_root,
        reviewer=reviewer,
        status=status,
        candidate_id=candidate_id,
        limit=limit,
    )
    if format == "markdown":
        return Response(
            content=render_achievement_route_backfill_candidate_review_audit_markdown(audit),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_backfill_candidate_review_audit_csv(audit),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"backfill_candidate_review_audit": audit.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates/readiness", response_model=None)
def get_achievement_route_backfill_candidate_readiness(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    readiness = build_achievement_route_backfill_candidate_readiness(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_backfill_candidate_readiness_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_backfill_candidate_readiness_csv(readiness),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"backfill_candidate_readiness": readiness.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft", response_model=None)
def get_achievement_route_source_edit_patch_draft(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    export = build_achievement_route_source_edit_patch_draft(source_root, audit_root)
    if format == "markdown":
        return Response(
            content=render_achievement_route_source_edit_patch_draft_markdown(export),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_source_edit_patch_draft_csv(export),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"source_edit_patch_draft": export.model_dump(mode="json")})


@router.post("/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply", response_model=None)
def post_achievement_route_source_edit_patch_apply(request: AchievementRouteSourceEditPatchApplyRequest):
    try:
        record = apply_achievement_route_source_edit_patch_draft(request, source_root, audit_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"source_edit_patch_apply": record.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit", response_model=None)
def get_achievement_route_source_edit_patch_apply_audit(
    reviewer: str | None = None,
    draft_id: str | None = None,
    output_source_id: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    audit = list_achievement_route_source_edit_patch_apply_audits(
        audit_root,
        reviewer=reviewer,
        draft_id=draft_id,
        output_source_id=output_source_id,
        limit=limit,
    )
    if format == "markdown":
        return Response(
            content=render_achievement_route_source_edit_patch_apply_audit_markdown(audit),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_source_edit_patch_apply_audit_csv(audit),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"source_edit_patch_apply_audit": audit.model_dump(mode="json")})


@router.post("/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source", response_model=None)
def post_achievement_route_draft_source_promotion(request: AchievementRouteDraftSourcePromotionRequest):
    try:
        record = promote_draft_achievement_route_source_to_reviewed(request, source_root, audit_root)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"draft_source_promotion": record.model_dump(mode="json")})


@router.get("/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit", response_model=None)
def get_achievement_route_draft_source_promotion_audit(
    reviewer: str | None = None,
    draft_source_id: str | None = None,
    reviewed_source_id: str | None = None,
    limit: int = Query(default=25, ge=1, le=200),
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    audit = list_achievement_route_draft_source_promotion_audits(
        audit_root,
        reviewer=reviewer,
        draft_source_id=draft_source_id,
        reviewed_source_id=reviewed_source_id,
        limit=limit,
    )
    if format == "markdown":
        return Response(
            content=render_achievement_route_draft_source_promotion_audit_markdown(audit),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_draft_source_promotion_audit_csv(audit),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"draft_source_promotion_audit": audit.model_dump(mode="json")})


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
