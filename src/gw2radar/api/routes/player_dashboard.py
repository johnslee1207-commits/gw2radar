from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.account_value import (
    build_account_holding_index,
    build_account_value_snapshot,
    list_account_value_history,
    record_account_value_history_snapshot,
    render_account_value_history_csv,
    render_account_value_history_markdown,
    render_account_value_snapshot_csv,
    render_account_value_snapshot_markdown,
)
from gw2radar.commercial.player_intelligence import (
    build_player_history_correlation,
    build_data_freshness_annotations,
    build_player_dashboard_plan,
    build_player_session_packet,
    build_player_support_handoff_bundle,
    build_player_support_handoff_dashboard,
    build_player_support_handoff_final_archive_zip_bundle,
    build_player_support_handoff_operator_packet,
    build_player_support_handoff_readiness_checklist,
    build_player_support_handoff_zip_bundle,
    build_player_readiness_summary,
    list_player_readiness_history,
    list_player_session_packet_artifacts,
    list_player_support_handoff_artifacts,
    list_player_support_handoff_final_archives,
    list_player_support_handoff_zip_verification_audits,
    PlayerSupportHandoffZipVerificationAuditRequest,
    record_player_readiness_snapshot,
    record_player_support_handoff_zip_verification_audit,
    resolve_player_session_packet_artifact_path,
    resolve_player_support_handoff_artifact_path,
    resolve_player_support_handoff_final_archive_path,
    render_player_history_correlation_csv,
    render_player_history_correlation_markdown,
    render_player_session_packet_csv,
    render_player_session_packet_markdown,
    render_player_support_handoff_dashboard_csv,
    render_player_support_handoff_dashboard_markdown,
    render_player_support_handoff_csv,
    render_player_support_handoff_markdown,
    render_player_support_handoff_operator_packet_csv,
    render_player_support_handoff_operator_packet_markdown,
    render_player_support_handoff_readiness_checklist_csv,
    render_player_support_handoff_readiness_checklist_markdown,
    render_player_support_handoff_zip_verification_audit_csv,
    render_player_support_handoff_zip_verification_audit_markdown,
    render_player_readiness_history_csv,
    render_player_readiness_history_markdown,
    render_player_readiness_csv,
    render_player_readiness_markdown,
    write_player_session_packet_artifacts,
    write_player_support_handoff_artifacts,
    write_player_support_handoff_final_archive,
    verify_player_support_handoff_final_archive_zip_bundle,
    verify_player_support_handoff_zip_bundle,
)
from gw2radar.commercial.gateway_incidents import build_gateway_incident_timeline
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/player", tags=["player-dashboard"])


class PlayerSupportHandoffRequest(BaseModel):
    debug_bundle: dict | None = None


@router.get("/dashboard", response_model=ApiDataEnvelope)
def get_player_dashboard() -> ApiDataEnvelope:
    graph = get_graph()
    plan = build_player_dashboard_plan(graph)
    return ApiDataEnvelope(data={"dashboard": plan.model_dump(mode="json")})


@router.get("/readiness", response_model=None)
def get_player_readiness(format: str = "json") -> ApiDataEnvelope | Response:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, snapshot)
    if format == "markdown":
        return Response(
            content=render_player_readiness_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_readiness_summary.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_readiness_csv(readiness),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_readiness_summary.csv"'},
        )
    return ApiDataEnvelope(data={"readiness": readiness.model_dump(mode="json")})


@router.post("/readiness/history", response_model=ApiDataEnvelope)
def post_player_readiness_history_snapshot(source: str = "player_dashboard") -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, snapshot)
        history_snapshot = record_player_readiness_snapshot(session, readiness, source=source)
    return ApiDataEnvelope(data={"snapshot": history_snapshot.model_dump(mode="json")})


@router.get("/readiness/history", response_model=None)
def get_player_readiness_history(format: str = "json", limit: int = 10) -> ApiDataEnvelope | Response:
    init_db()
    with db_session.SessionLocal() as session:
        history = list_player_readiness_history(session, limit=limit)
    if format == "markdown":
        return Response(
            content=render_player_readiness_history_markdown(history),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_readiness_history.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_readiness_history_csv(history),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_readiness_history.csv"'},
        )
    return ApiDataEnvelope(data={"history": history.model_dump(mode="json")})


@router.get("/freshness-annotations", response_model=ApiDataEnvelope)
def get_player_freshness_annotations() -> ApiDataEnvelope:
    graph = get_graph()
    return ApiDataEnvelope(
        data={"annotations": [item.model_dump(mode="json") for item in build_data_freshness_annotations(graph)]}
    )


@router.get("/gateway-incidents", response_model=ApiDataEnvelope)
def get_player_gateway_incidents(limit: int = 20) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        timeline = build_gateway_incident_timeline(session, limit=limit)
    return ApiDataEnvelope(data={"gateway_incident_timeline": timeline.model_dump(mode="json")})


@router.get("/account-holdings", response_model=ApiDataEnvelope)
def get_player_account_holdings(include_holdings: bool = True) -> ApiDataEnvelope:
    graph = get_graph()
    holding_index = build_account_holding_index(graph, include_holdings=include_holdings)
    return ApiDataEnvelope(data={"account_holding_index": holding_index.model_dump(mode="json")})


@router.get("/account-value", response_model=None)
def get_player_account_value(
    format: str = "json",
    stale_price_hours: int = 48,
) -> ApiDataEnvelope | Response:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = build_account_value_snapshot(graph, session, stale_price_hours=max(1, stale_price_hours))
    if format == "markdown":
        return Response(
            content=render_account_value_snapshot_markdown(snapshot),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="account_value_snapshot.md"'},
        )
    if format == "csv":
        return Response(
            content=render_account_value_snapshot_csv(snapshot),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="account_value_snapshot.csv"'},
        )
    return ApiDataEnvelope(data={"account_value_snapshot": snapshot.model_dump(mode="json")})


@router.post("/account-value/history", response_model=ApiDataEnvelope)
def post_player_account_value_history_snapshot(source: str = "player_dashboard") -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = build_account_value_snapshot(graph, session)
        history_snapshot = record_account_value_history_snapshot(session, snapshot, source=source)
    return ApiDataEnvelope(data={"snapshot": history_snapshot.model_dump(mode="json")})


@router.get("/account-value/history", response_model=None)
def get_player_account_value_history(format: str = "json", limit: int = 10) -> ApiDataEnvelope | Response:
    init_db()
    with db_session.SessionLocal() as session:
        history = list_account_value_history(session, limit=limit)
    if format == "markdown":
        return Response(
            content=render_account_value_history_markdown(history),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="account_value_history.md"'},
        )
    if format == "csv":
        return Response(
            content=render_account_value_history_csv(history),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="account_value_history.csv"'},
        )
    return ApiDataEnvelope(data={"history": history.model_dump(mode="json")})


@router.get("/history/correlation", response_model=None)
def get_player_history_correlation(format: str = "json", limit: int = 10) -> ApiDataEnvelope | Response:
    init_db()
    with db_session.SessionLocal() as session:
        readiness_history = list_player_readiness_history(session, limit=limit)
        account_value_history = list_account_value_history(session, limit=limit)
        correlation = build_player_history_correlation(readiness_history, account_value_history)
    if format == "markdown":
        return Response(
            content=render_player_history_correlation_markdown(correlation),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_history_correlation.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_history_correlation_csv(correlation),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_history_correlation.csv"'},
        )
    return ApiDataEnvelope(data={"correlation": correlation.model_dump(mode="json")})


@router.get("/session-packet", response_model=None)
def get_player_session_packet(format: str = "json", limit: int = 10) -> ApiDataEnvelope | Response:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        account_value = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, account_value)
        readiness_history = list_player_readiness_history(session, limit=limit)
        account_value_history = list_account_value_history(session, limit=limit)
        correlation = build_player_history_correlation(readiness_history, account_value_history)
        packet = build_player_session_packet(
            graph,
            readiness,
            account_value,
            readiness_history,
            account_value_history,
            correlation,
        )
    if format == "markdown":
        return Response(
            content=render_player_session_packet_markdown(packet),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_session_packet.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_session_packet_csv(packet),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_session_packet.csv"'},
        )
    return ApiDataEnvelope(data={"session_packet": packet.model_dump(mode="json")})


@router.post("/session-packet/artifacts", response_model=ApiDataEnvelope)
def post_player_session_packet_artifacts(limit: int = 10) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        account_value = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, account_value)
        readiness_history = list_player_readiness_history(session, limit=limit)
        account_value_history = list_account_value_history(session, limit=limit)
        correlation = build_player_history_correlation(readiness_history, account_value_history)
        packet = build_player_session_packet(
            graph,
            readiness,
            account_value,
            readiness_history,
            account_value_history,
            correlation,
        )
    bundle = write_player_session_packet_artifacts(packet)
    return ApiDataEnvelope(data={"artifact_bundle": bundle.model_dump(mode="json")})


@router.get("/session-packet/artifacts", response_model=ApiDataEnvelope)
def get_player_session_packet_artifacts(limit: int = 20) -> ApiDataEnvelope:
    bundles = list_player_session_packet_artifacts(limit=limit)
    return ApiDataEnvelope(data={"artifact_bundles": [bundle.model_dump(mode="json") for bundle in bundles]})


@router.get("/session-packet/artifacts/{artifact_id}/{file_name}", response_model=None)
def get_player_session_packet_artifact_file(artifact_id: str, file_name: str) -> Response:
    path = resolve_player_session_packet_artifact_path(artifact_id, file_name)
    if path is None:
        raise HTTPException(status_code=404, detail="Player session packet artifact not found")
    media_type = "application/json"
    if file_name.endswith(".md"):
        media_type = "text/markdown; charset=utf-8"
    elif file_name.endswith(".csv"):
        media_type = "text/csv; charset=utf-8"
    return Response(content=path.read_text(encoding="utf-8"), media_type=media_type)


@router.post("/support-handoff", response_model=None)
def post_player_support_handoff(
    request: PlayerSupportHandoffRequest | None = None,
    format: str = "json",
    limit: int = 10,
) -> ApiDataEnvelope | Response:
    handoff = _build_player_support_handoff(request=request, limit=limit)
    if format == "markdown":
        return Response(
            content=render_player_support_handoff_markdown(handoff),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_support_handoff_csv(handoff),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff.csv"'},
        )
    return ApiDataEnvelope(data={"support_handoff": handoff.model_dump(mode="json")})


@router.post("/support-handoff/artifacts", response_model=ApiDataEnvelope)
def post_player_support_handoff_artifacts(
    request: PlayerSupportHandoffRequest | None = None,
    limit: int = 10,
) -> ApiDataEnvelope:
    handoff = _build_player_support_handoff(request=request, limit=limit)
    artifact_bundle = write_player_support_handoff_artifacts(handoff)
    return ApiDataEnvelope(data={"artifact_bundle": artifact_bundle.model_dump(mode="json")})


@router.get("/support-handoff/artifacts", response_model=ApiDataEnvelope)
def get_player_support_handoff_artifacts(limit: int = 20) -> ApiDataEnvelope:
    bundles = list_player_support_handoff_artifacts(limit=limit)
    return ApiDataEnvelope(data={"artifact_bundles": [bundle.model_dump(mode="json") for bundle in bundles]})


@router.get("/support-handoff/artifacts/bundle", response_model=None)
def get_player_support_handoff_artifact_bundle(
    format: str = Query(default="zip", pattern="^(zip|manifest)$"),
) -> ApiDataEnvelope | Response:
    _ensure_player_support_handoff_artifact()
    try:
        manifest, bundle_bytes = build_player_support_handoff_zip_bundle()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if format == "manifest":
        return ApiDataEnvelope(data={"support_handoff_zip_bundle": manifest.model_dump(mode="json")})
    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{manifest.filename}"',
            "X-Checksum-SHA256": manifest.checksum_sha256,
        },
    )


@router.post("/support-handoff/artifacts/bundle/verify", response_model=ApiDataEnvelope)
def post_player_support_handoff_artifact_bundle_verify(
    bundle: bytes | None = Body(default=None, media_type="application/zip"),
    expected_checksum_sha256: str | None = Query(default=None),
) -> ApiDataEnvelope:
    if bundle is None or len(bundle) == 0:
        _ensure_player_support_handoff_artifact()
        manifest, bundle = build_player_support_handoff_zip_bundle()
        expected_checksum_sha256 = expected_checksum_sha256 or manifest.checksum_sha256
    verification = verify_player_support_handoff_zip_bundle(
        bundle,
        expected_checksum_sha256=expected_checksum_sha256,
    )
    return ApiDataEnvelope(data={"support_handoff_zip_verification": verification.model_dump(mode="json")})


@router.post("/support-handoff/artifacts/bundle/verification-audit", response_model=ApiDataEnvelope)
def post_player_support_handoff_artifact_bundle_verification_audit(
    request: PlayerSupportHandoffZipVerificationAuditRequest,
) -> ApiDataEnvelope:
    _ensure_player_support_handoff_artifact()
    record = record_player_support_handoff_zip_verification_audit(request)
    return ApiDataEnvelope(data={"support_handoff_zip_verification_audit_record": record.model_dump(mode="json")})


@router.post("/support-handoff/artifacts/bundle/verification-audit/upload", response_model=ApiDataEnvelope)
def post_player_support_handoff_artifact_bundle_verification_audit_upload(
    bundle: bytes = Body(media_type="application/zip"),
    reviewer: str = Query(default="support"),
    expected_checksum_sha256: str | None = Query(default=None),
) -> ApiDataEnvelope:
    request = PlayerSupportHandoffZipVerificationAuditRequest(
        reviewer=reviewer,
        expected_checksum_sha256=expected_checksum_sha256,
        notes=["Support handoff zip verification audit recorded from uploaded zip bytes."],
    )
    record = record_player_support_handoff_zip_verification_audit(request, bundle_bytes=bundle)
    return ApiDataEnvelope(data={"support_handoff_zip_verification_audit_record": record.model_dump(mode="json")})


@router.get("/support-handoff/artifacts/bundle/verification-audit", response_model=None)
def get_player_support_handoff_artifact_bundle_verification_audit(
    reviewer: str | None = None,
    limit: int = 20,
    format: str = "json",
) -> ApiDataEnvelope | Response:
    audit = list_player_support_handoff_zip_verification_audits(reviewer=reviewer, limit=limit)
    if format == "markdown":
        return Response(
            content=render_player_support_handoff_zip_verification_audit_markdown(audit),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_zip_verification_audit.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_support_handoff_zip_verification_audit_csv(audit),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_zip_verification_audit.csv"'},
        )
    return ApiDataEnvelope(data={"support_handoff_zip_verification_audit": audit.model_dump(mode="json")})


@router.get("/support-handoff/readiness-checklist", response_model=None)
def get_player_support_handoff_readiness_checklist(format: str = "json") -> ApiDataEnvelope | Response:
    _ensure_player_support_handoff_artifact()
    if not list_player_support_handoff_zip_verification_audits(limit=1).records:
        record_player_support_handoff_zip_verification_audit(
            PlayerSupportHandoffZipVerificationAuditRequest(
                reviewer="system",
                notes=["System recorded support handoff readiness verification audit."],
            )
        )
    checklist = build_player_support_handoff_readiness_checklist()
    if format == "markdown":
        return Response(
            content=render_player_support_handoff_readiness_checklist_markdown(checklist),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_readiness_checklist.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_support_handoff_readiness_checklist_csv(checklist),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_readiness_checklist.csv"'},
        )
    return ApiDataEnvelope(data={"support_handoff_readiness_checklist": checklist.model_dump(mode="json")})


@router.get("/support-handoff/operator-packet", response_model=None)
def get_player_support_handoff_operator_packet(format: str = "json") -> ApiDataEnvelope | Response:
    _ensure_player_support_handoff_artifact()
    if not list_player_support_handoff_zip_verification_audits(limit=1).records:
        record_player_support_handoff_zip_verification_audit(
            PlayerSupportHandoffZipVerificationAuditRequest(
                reviewer="system",
                notes=["System recorded support handoff operator packet verification audit."],
            )
        )
    packet = build_player_support_handoff_operator_packet()
    if format == "markdown":
        return Response(
            content=render_player_support_handoff_operator_packet_markdown(packet),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_operator_packet.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_support_handoff_operator_packet_csv(packet),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_operator_packet.csv"'},
        )
    return ApiDataEnvelope(data={"support_handoff_operator_packet": packet.model_dump(mode="json")})


@router.get("/support-handoff/dashboard", response_model=None)
def get_player_support_handoff_dashboard(format: str = "json") -> ApiDataEnvelope | Response:
    _ensure_player_support_handoff_artifact()
    if not list_player_support_handoff_zip_verification_audits(limit=1).records:
        record_player_support_handoff_zip_verification_audit(
            PlayerSupportHandoffZipVerificationAuditRequest(
                reviewer="system",
                notes=["System recorded support handoff dashboard verification audit."],
            )
        )
    dashboard = build_player_support_handoff_dashboard()
    if format == "markdown":
        return Response(
            content=render_player_support_handoff_dashboard_markdown(dashboard),
            media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_dashboard.md"'},
        )
    if format == "csv":
        return Response(
            content=render_player_support_handoff_dashboard_csv(dashboard),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="player_support_handoff_dashboard.csv"'},
        )
    return ApiDataEnvelope(data={"support_handoff_dashboard": dashboard.model_dump(mode="json")})


@router.post("/support-handoff/final-archive", response_model=ApiDataEnvelope)
def post_player_support_handoff_final_archive() -> ApiDataEnvelope:
    _ensure_player_support_handoff_artifact()
    if not list_player_support_handoff_zip_verification_audits(limit=1).records:
        record_player_support_handoff_zip_verification_audit(
            PlayerSupportHandoffZipVerificationAuditRequest(
                reviewer="system",
                notes=["System recorded support handoff final archive verification audit."],
            )
        )
    archive = write_player_support_handoff_final_archive()
    return ApiDataEnvelope(data={"support_handoff_final_archive": archive.model_dump(mode="json")})


@router.get("/support-handoff/final-archive", response_model=ApiDataEnvelope)
def get_player_support_handoff_final_archives(limit: int = 20) -> ApiDataEnvelope:
    archives = list_player_support_handoff_final_archives(limit=limit)
    return ApiDataEnvelope(data={"support_handoff_final_archives": [archive.model_dump(mode="json") for archive in archives]})


@router.get("/support-handoff/final-archive/bundle", response_model=None)
def get_player_support_handoff_final_archive_bundle(
    format: str = Query(default="zip", pattern="^(zip|manifest)$"),
) -> ApiDataEnvelope | Response:
    if not list_player_support_handoff_final_archives(limit=1):
        _ensure_player_support_handoff_artifact()
        if not list_player_support_handoff_zip_verification_audits(limit=1).records:
            record_player_support_handoff_zip_verification_audit(
                PlayerSupportHandoffZipVerificationAuditRequest(
                    reviewer="system",
                    notes=["System recorded support handoff final archive bundle verification audit."],
                )
            )
        write_player_support_handoff_final_archive()
    try:
        manifest, bundle_bytes = build_player_support_handoff_final_archive_zip_bundle()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if format == "manifest":
        return ApiDataEnvelope(data={"support_handoff_final_archive_zip_bundle": manifest.model_dump(mode="json")})
    return Response(
        content=bundle_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{manifest.filename}"',
            "X-Checksum-SHA256": manifest.checksum_sha256,
        },
    )


@router.post("/support-handoff/final-archive/bundle/verify", response_model=ApiDataEnvelope)
def post_player_support_handoff_final_archive_bundle_verify(
    bundle: bytes | None = Body(default=None, media_type="application/zip"),
    expected_checksum_sha256: str | None = Query(default=None),
) -> ApiDataEnvelope:
    if bundle is None or len(bundle) == 0:
        if not list_player_support_handoff_final_archives(limit=1):
            _ensure_player_support_handoff_artifact()
            write_player_support_handoff_final_archive()
        manifest, bundle = build_player_support_handoff_final_archive_zip_bundle()
        expected_checksum_sha256 = expected_checksum_sha256 or manifest.checksum_sha256
    verification = verify_player_support_handoff_final_archive_zip_bundle(
        bundle,
        expected_checksum_sha256=expected_checksum_sha256,
    )
    return ApiDataEnvelope(data={"support_handoff_final_archive_zip_verification": verification.model_dump(mode="json")})


@router.get("/support-handoff/final-archive/{archive_id}/{file_name}", response_model=None)
def get_player_support_handoff_final_archive_file(archive_id: str, file_name: str) -> Response:
    path = resolve_player_support_handoff_final_archive_path(archive_id, file_name)
    if path is None:
        raise HTTPException(status_code=404, detail="Player support handoff final archive file not found")
    media_type = "application/json"
    if file_name.endswith(".md"):
        media_type = "text/markdown; charset=utf-8"
    elif file_name.endswith(".csv"):
        media_type = "text/csv; charset=utf-8"
    return Response(content=path.read_text(encoding="utf-8"), media_type=media_type)


@router.get("/support-handoff/artifacts/{artifact_id}/{file_name}", response_model=None)
def get_player_support_handoff_artifact_file(artifact_id: str, file_name: str) -> Response:
    path = resolve_player_support_handoff_artifact_path(artifact_id, file_name)
    if path is None:
        raise HTTPException(status_code=404, detail="Player support handoff artifact not found")
    media_type = "application/json"
    if file_name.endswith(".md"):
        media_type = "text/markdown; charset=utf-8"
    elif file_name.endswith(".csv"):
        media_type = "text/csv; charset=utf-8"
    return Response(content=path.read_text(encoding="utf-8"), media_type=media_type)


def _build_player_support_handoff(
    *,
    request: PlayerSupportHandoffRequest | None = None,
    limit: int = 10,
):
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        account_value = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, account_value)
        readiness_history = list_player_readiness_history(session, limit=limit)
        account_value_history = list_account_value_history(session, limit=limit)
        correlation = build_player_history_correlation(readiness_history, account_value_history)
        packet = build_player_session_packet(
            graph,
            readiness,
            account_value,
            readiness_history,
            account_value_history,
            correlation,
        )
    artifact_bundle = write_player_session_packet_artifacts(packet)
    handoff = build_player_support_handoff_bundle(
        session_artifact_bundle=artifact_bundle,
        debug_bundle=request.debug_bundle if request else None,
    )
    return handoff


def _ensure_player_support_handoff_artifact() -> None:
    if list_player_support_handoff_artifacts(limit=1):
        return
    handoff = _build_player_support_handoff(request=None, limit=10)
    write_player_support_handoff_artifacts(handoff)
