from fastapi import APIRouter
from fastapi.responses import Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.account_value import (
    build_account_holding_index,
    build_account_value_snapshot,
    render_account_value_snapshot_csv,
    render_account_value_snapshot_markdown,
)
from gw2radar.commercial.player_intelligence import (
    build_data_freshness_annotations,
    build_player_dashboard_plan,
    build_player_readiness_summary,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/player", tags=["player-dashboard"])


@router.get("/dashboard", response_model=ApiDataEnvelope)
def get_player_dashboard() -> ApiDataEnvelope:
    graph = get_graph()
    plan = build_player_dashboard_plan(graph)
    return ApiDataEnvelope(data={"dashboard": plan.model_dump(mode="json")})


@router.get("/readiness", response_model=ApiDataEnvelope)
def get_player_readiness() -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = build_account_value_snapshot(graph, session)
        readiness = build_player_readiness_summary(graph, session, snapshot)
    return ApiDataEnvelope(data={"readiness": readiness.model_dump(mode="json")})


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
