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
from gw2radar.commercial.patch_freshness import (
    build_patch_freshness_report,
    market_freshness_notices,
    render_patch_freshness_section,
)
from gw2radar.commercial.report_engine import ReportExportFormat, generate_report_job
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb.kb_repository import list_rules
from gw2radar.kb.kb_source_semantics import build_source_semantic_report
from gw2radar.kb.patch_impact_review import build_patch_review_dashboard

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
        watches = list_watchlist(session, DEFAULT_USER_ID)
    notices = market_freshness_notices(watches, _patch_dashboard_items(), _source_semantics())
    return ApiDataEnvelope(
        data={
            "watchlist": [item.model_dump(mode="json") for item in watches],
            "patch_freshness_notices": [notice.model_dump(mode="json") for notice in notices],
        }
    )


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
        freshness = build_patch_freshness_report([], report.watchlist, _patch_dashboard_items(), _source_semantics())
        if freshness.notices:
            markdown = markdown.rstrip() + "\n\n" + "\n".join(render_patch_freshness_section(freshness)) + "\n"
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


@router.get("/patch-freshness", response_model=ApiDataEnvelope)
def get_market_patch_freshness() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        watches = list_watchlist(session, DEFAULT_USER_ID)
    notices = market_freshness_notices(watches, _patch_dashboard_items(), _source_semantics())
    return ApiDataEnvelope(
        data={
            "notice_count": len(notices),
            "notices": [notice.model_dump(mode="json") for notice in notices],
        }
    )


def _patch_dashboard_items():
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    return build_patch_review_dashboard(rules)


def _source_semantics():
    return build_source_semantic_report()
