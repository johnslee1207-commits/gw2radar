from fastapi import APIRouter
from fastapi.responses import Response

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
    build_player_readiness_summary,
    list_player_readiness_history,
    record_player_readiness_snapshot,
    render_player_history_correlation_csv,
    render_player_history_correlation_markdown,
    render_player_session_packet_csv,
    render_player_session_packet_markdown,
    render_player_readiness_history_csv,
    render_player_readiness_history_markdown,
    render_player_readiness_csv,
    render_player_readiness_markdown,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/player", tags=["player-dashboard"])


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
