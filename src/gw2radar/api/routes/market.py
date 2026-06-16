from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.market_radar import (
    DEFAULT_USER_ID,
    PriceSnapshotInput,
    add_watchlist_item,
    build_market_radar_report,
    calculate_goal_cost_index,
    infer_market_signals,
    list_watchlist,
    record_price_snapshot,
    render_market_report,
)
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/market", tags=["market"])


class WatchlistRequest(BaseModel):
    item_id: str
    item_name: str
    reason: str


class MarketReportRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"
    format: ReportExportFormat = ReportExportFormat.MARKDOWN


@router.get("/watchlist", response_model=ApiDataEnvelope)
def get_market_watchlist() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        watchlist = [item.model_dump(mode="json") for item in list_watchlist(session, DEFAULT_USER_ID)]
    return ApiDataEnvelope(data={"watchlist": watchlist})


@router.post("/watchlist", response_model=ApiDataEnvelope)
def post_market_watchlist(request: WatchlistRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        item = add_watchlist_item(session, request.item_id, request.item_name, request.reason, DEFAULT_USER_ID)
    return ApiDataEnvelope(data={"watch": item.model_dump(mode="json")})


@router.post("/snapshots", response_model=ApiDataEnvelope)
def post_market_snapshot(request: PriceSnapshotInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        snapshot = record_price_snapshot(session, request)
    return ApiDataEnvelope(data={"snapshot": snapshot.model_dump(mode="json")})


@router.get("/goal-cost-index", response_model=ApiDataEnvelope)
def get_market_goal_cost_index(goal_id: str = "gw2:goal:aurora") -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        index = calculate_goal_cost_index(session, graph, goal_id)
    return ApiDataEnvelope(data={"goal_cost_index": index.model_dump(mode="json")})


@router.get("/signals", response_model=ApiDataEnvelope)
def get_market_signals(goal_id: str = "gw2:goal:aurora") -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        signals = [signal.model_dump(mode="json") for signal in infer_market_signals(session, graph, goal_id)]
    return ApiDataEnvelope(data={"signals": signals})


@router.post("/report", response_model=ApiDataEnvelope)
def post_market_report(request: MarketReportRequest) -> ApiDataEnvelope:
    graph = get_graph()
    if request.goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    init_db()
    with db_session.SessionLocal() as session:
        report = build_market_radar_report(session, graph, request.goal_id, DEFAULT_USER_ID)
        markdown = render_market_report(report)
        try:
            job = generate_report_job(
                session,
                graph,
                user_id=DEFAULT_USER_ID,
                product_id="market_snapshot_report",
                goal_id=request.goal_id,
                export_format=request.format,
                markdown_override=markdown,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"job": job.model_dump(mode="json")})
