from sqlalchemy import func, select
from fastapi import APIRouter, Query, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import ApiKeySecretModel, RefreshQueueModel
from gw2radar.ops.release_readiness import (
    build_operational_hardening_readiness,
    render_operational_hardening_csv,
    render_operational_hardening_markdown,
)
from gw2radar.ops.operator_release_packet import (
    build_operator_release_packet_bundle,
    build_operator_release_packet_summary,
    render_operator_release_packet_summary_csv,
    render_operator_release_packet_summary_markdown,
    verify_operator_release_packet_bundle,
    write_operator_release_packet_artifacts,
)
from gw2radar.ops.final_closeout import (
    build_final_closeout_dashboard,
    build_stop_line_review,
    render_final_closeout_dashboard_csv,
    render_final_closeout_dashboard_markdown,
    render_stop_line_review_csv,
    render_stop_line_review_markdown,
)

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


@router.get("/status", response_model=ApiDataEnvelope)
def get_operational_status() -> ApiDataEnvelope:
    init_db()
    graph = get_graph()
    with db_session.SessionLocal() as session:
        queue_counts = {
            status: count
            for status, count in session.execute(
                select(RefreshQueueModel.status, func.count()).group_by(RefreshQueueModel.status)
            ).all()
        }
        has_api_key = session.get(ApiKeySecretModel, "default") is not None
    return ApiDataEnvelope(
        data={
            "status": "ok",
            "database": "ok",
            "graph": {
                "entities": len(graph.entities),
                "relations": len(graph.relations),
                "player_state": len(graph.player_state),
                "actions": len(graph.actions),
            },
            "refresh_queue": queue_counts,
            "api_key_configured": has_api_key,
            "capabilities": {
                "account_sync": True,
                "public_refresh": True,
                "export_package": True,
                "mock_generation": True,
            },
        }
    )


@router.get("/release-readiness", response_model=None)
def get_operational_release_readiness(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    readiness = build_operational_hardening_readiness()
    if format == "markdown":
        return Response(
            content=render_operational_hardening_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_operational_hardening_csv(readiness),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"release_readiness": readiness.model_dump(mode="json")})


@router.get("/release-packet", response_model=None)
def get_operator_release_packet(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    summary = build_operator_release_packet_summary()
    if format == "markdown":
        return Response(
            content=render_operator_release_packet_summary_markdown(summary),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_operator_release_packet_summary_csv(summary),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"operator_release_packet": summary.model_dump(mode="json")})


@router.post("/release-packet/artifacts", response_model=ApiDataEnvelope)
def post_operator_release_packet_artifacts() -> ApiDataEnvelope:
    index = write_operator_release_packet_artifacts()
    return ApiDataEnvelope(data={"operator_release_packet_artifacts": index.model_dump(mode="json")})


@router.get("/release-packet/artifacts/bundle", response_model=None)
def get_operator_release_packet_bundle(
    format: str = Query(default="zip", pattern="^(zip|manifest)$"),
):
    manifest, bundle_bytes = build_operator_release_packet_bundle()
    if format == "manifest":
        return ApiDataEnvelope(data={"operator_release_packet_bundle": manifest.model_dump(mode="json")})
    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "x-checksum-sha256": manifest.checksum_sha256,
            "content-disposition": f'attachment; filename="{manifest.filename}"',
        },
    )


@router.post("/release-packet/artifacts/bundle/verify", response_model=ApiDataEnvelope)
def post_operator_release_packet_bundle_verify() -> ApiDataEnvelope:
    manifest, bundle_bytes = build_operator_release_packet_bundle()
    verification = verify_operator_release_packet_bundle(
        bundle_bytes,
        expected_checksum_sha256=manifest.checksum_sha256,
    )
    return ApiDataEnvelope(data={"operator_release_packet_bundle_verification": verification.model_dump(mode="json")})


@router.get("/final-closeout-dashboard", response_model=None)
def get_final_closeout_dashboard(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    dashboard = build_final_closeout_dashboard()
    if format == "markdown":
        return Response(
            content=render_final_closeout_dashboard_markdown(dashboard),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_final_closeout_dashboard_csv(dashboard),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"final_closeout_dashboard": dashboard.model_dump(mode="json")})


@router.get("/stop-line-review", response_model=None)
def get_stop_line_review(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    review = build_stop_line_review()
    if format == "markdown":
        return Response(
            content=render_stop_line_review_markdown(review),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_stop_line_review_csv(review),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"stop_line_review": review.model_dump(mode="json")})
