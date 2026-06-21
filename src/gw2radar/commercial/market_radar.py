from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import MarketSnapshotModel, MarketWatchlistModel, utc_now
from gw2radar.graph.graph_query import GraphData
from gw2radar.commercial.account_value import (
    AccountValueEvidenceBridge,
    AccountValueSnapshot,
    build_account_holding_index,
    build_account_value_evidence_bridge,
    build_account_value_snapshot,
    build_goal_reservation_index,
    render_account_value_evidence_bridge_markdown,
)
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.inference.goal_gap import calculate_goal_gap


DEFAULT_USER_ID = "local-user"

FORBIDDEN_MARKET_LANGUAGE = [
    "guaranteed profit",
    "must buy now",
    "sure win",
    "arbitrage exploit",
    "automated order",
    "market manipulation",
    "rmt",
]


class MarketSignalType(StrEnum):
    OBSERVE = "observe"
    HOLD = "hold"
    CONSIDER_SELL_SURPLUS = "consider_sell_surplus"
    BUY_WAIT = "buy_wait"


class PriceSnapshotInput(BaseModel):
    item_id: str
    item_name: str
    buy_price_copper: int
    sell_price_copper: int
    volume: int = 0
    source: str = "manual_snapshot"


class PriceSnapshot(BaseModel):
    snapshot_id: str
    item_id: str
    item_name: str
    buy_price_copper: int
    sell_price_copper: int
    volume: int
    source: str
    observed_at: datetime


class PriceTrend(BaseModel):
    item_id: str
    item_name: str
    latest_sell_price_copper: int
    average_sell_price_copper: float
    delta_from_average_percent: float
    direction: str
    volatility_score: float
    liquidity_score: float


class ItemWatch(BaseModel):
    watch_id: str
    user_id: str
    item_id: str
    item_name: str
    reason: str
    created_at: datetime


class GoalCostIndex(BaseModel):
    goal_id: str
    goal_name: str
    total_missing_cost_copper: int
    priced_items: list[str]
    unpriced_items: list[str]


class MarketSignal(BaseModel):
    item_id: str
    item_name: str
    signal_type: MarketSignalType
    explanation: str
    valuation_status: str | None = None
    value_buy_copper: int = 0
    net_sell_value_copper: int = 0
    reserved_quantity: float = 0.0
    sellable_surplus_quantity: float = 0.0
    reserved_for_goal_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class MarketRadarReport(BaseModel):
    watchlist: list[ItemWatch]
    trends: list[PriceTrend]
    goal_cost_index: GoalCostIndex | None = None
    signals: list[MarketSignal]
    account_value_evidence: AccountValueEvidenceBridge | None = None


class OfficialPriceRefreshResult(BaseModel):
    schema_version: str = "gw2radar.official_price_refresh.v1"
    status: str
    requested_item_count: int
    refreshed_item_count: int
    skipped_item_count: int
    chunks: int
    source: str = "official_commerce_api"
    warnings: list[str] = Field(default_factory=list)
    boundary: str = "Official price refresh stores public price observations only; it does not trade or inspect private payloads."


def record_price_snapshot(session: Session, snapshot: PriceSnapshotInput) -> PriceSnapshot:
    row = MarketSnapshotModel(
        snapshot_id=f"market_snapshot_{uuid4().hex}",
        item_id=snapshot.item_id,
        item_name=snapshot.item_name,
        buy_price_copper=snapshot.buy_price_copper,
        sell_price_copper=snapshot.sell_price_copper,
        volume=snapshot.volume,
        source=snapshot.source,
        observed_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _snapshot_from_model(row)


def refresh_official_price_snapshots_for_account(
    session: Session,
    graph: GraphData,
    gateway,
    *,
    chunk_size: int = 200,
) -> OfficialPriceRefreshResult:
    holding_index = build_account_holding_index(graph, include_holdings=True)
    item_ids = sorted({holding.item_id for holding in holding_index.holdings if holding.item_id is not None})
    warnings: list[str] = []
    if not item_ids:
        return OfficialPriceRefreshResult(
            status="idle",
            requested_item_count=0,
            refreshed_item_count=0,
            skipped_item_count=0,
            chunks=0,
            warnings=["No item holdings are available for price refresh."],
        )
    refreshed = 0
    chunks = 0
    for chunk in _chunks(item_ids, max(1, chunk_size)):
        chunks += 1
        result = gateway.get_batch("/v2/commerce/prices", ids=chunk, priority="P2")
        if result.status not in {GatewayStatus.OK, GatewayStatus.CACHE_HIT}:
            warnings.append(f"Chunk {chunks} returned {result.status.value}; retry later.")
            continue
        rows = result.payload if isinstance(result.payload, list) else [result.payload]
        for row in rows:
            if not isinstance(row, dict) or row.get("id") is None:
                continue
            item_id = int(row["id"])
            buys = row.get("buys") if isinstance(row.get("buys"), dict) else {}
            sells = row.get("sells") if isinstance(row.get("sells"), dict) else {}
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id=f"gw2:item:{item_id}",
                    item_name=graph.entity_name(f"gw2:item:{item_id}"),
                    buy_price_copper=int(buys.get("unit_price") or 0),
                    sell_price_copper=int(sells.get("unit_price") or 0),
                    volume=int(buys.get("quantity") or 0) + int(sells.get("quantity") or 0),
                    source="official_commerce_api",
                ),
            )
            refreshed += 1
    return OfficialPriceRefreshResult(
        status="succeeded" if refreshed else "refresh_pending",
        requested_item_count=len(item_ids),
        refreshed_item_count=refreshed,
        skipped_item_count=max(len(item_ids) - refreshed, 0),
        chunks=chunks,
        warnings=warnings,
    )


def add_watchlist_item(
    session: Session,
    item_id: str,
    item_name: str,
    reason: str,
    user_id: str = DEFAULT_USER_ID,
) -> ItemWatch:
    existing = (
        session.query(MarketWatchlistModel)
        .filter(MarketWatchlistModel.user_id == user_id, MarketWatchlistModel.item_id == item_id)
        .first()
    )
    if existing is not None:
        existing.reason = reason
        session.commit()
        return _watch_from_model(existing)
    row = MarketWatchlistModel(
        watch_id=f"watch_{uuid4().hex}",
        user_id=user_id,
        item_id=item_id,
        item_name=item_name,
        reason=reason,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _watch_from_model(row)


def list_watchlist(session: Session, user_id: str = DEFAULT_USER_ID) -> list[ItemWatch]:
    rows = (
        session.query(MarketWatchlistModel)
        .filter(MarketWatchlistModel.user_id == user_id)
        .order_by(MarketWatchlistModel.item_name)
        .all()
    )
    return [_watch_from_model(row) for row in rows]


def calculate_price_trends(session: Session, item_ids: list[str] | None = None) -> list[PriceTrend]:
    query = session.query(MarketSnapshotModel)
    if item_ids:
        query = query.filter(MarketSnapshotModel.item_id.in_(item_ids))
    rows = query.order_by(MarketSnapshotModel.item_id, MarketSnapshotModel.observed_at).all()
    by_item: dict[str, list[MarketSnapshotModel]] = {}
    for row in rows:
        by_item.setdefault(row.item_id, []).append(row)
    return [_trend_for_rows(item_rows) for item_rows in by_item.values() if item_rows]


def calculate_goal_cost_index(session: Session, graph: GraphData, goal_id: str) -> GoalCostIndex:
    gap = calculate_goal_gap(graph, goal_id)
    latest_by_item = _latest_snapshot_by_item(session)
    total = 0
    priced: list[str] = []
    unpriced: list[str] = []
    for item in gap.missing_requirements:
        latest = latest_by_item.get(item.entity_id)
        if latest is None:
            unpriced.append(item.entity_id)
            continue
        total += int(item.missing_quantity * latest.sell_price_copper)
        priced.append(item.entity_id)
    return GoalCostIndex(
        goal_id=goal_id,
        goal_name=gap.goal_name,
        total_missing_cost_copper=total,
        priced_items=priced,
        unpriced_items=unpriced,
    )


def infer_market_signals(
    session: Session,
    graph: GraphData,
    goal_id: str,
    value_snapshot: AccountValueSnapshot | None = None,
) -> list[MarketSignal]:
    trends = {trend.item_id: trend for trend in calculate_price_trends(session)}
    value_snapshot = value_snapshot or build_account_value_snapshot(graph, session, top_limit=10000)
    value_by_entity = {
        holding.entity_id: holding
        for holding in value_snapshot.top_holdings
    }
    reservations = build_goal_reservation_index(session, graph)
    gap = calculate_goal_gap(graph, goal_id)
    required_ids = {item.entity_id for item in gap.completed_requirements + gap.missing_requirements}
    reserved_ids = {entity_id for entity_id, reservation in reservations.items() if reservation.get("reserved_quantity", 0) > 0}
    missing_ids = {item.entity_id for item in gap.missing_requirements}
    signals: list[MarketSignal] = []
    for item_id in sorted(required_ids):
        trend = trends.get(item_id)
        name = graph.entity_name(item_id)
        if item_id in missing_ids:
            if trend and trend.delta_from_average_percent > 20:
                signals.append(
                    _checked_signal(
                        item_id,
                        name,
                        MarketSignalType.BUY_WAIT,
                        f"{name} is required by the active goal and is above recent average; consider observing before manual purchase.",
                        list(graph.evidence.keys()),
                        value_by_entity.get(item_id),
                        reservations.get(item_id),
                    )
                )
            else:
                signals.append(
                    _checked_signal(
                        item_id,
                        name,
                        MarketSignalType.OBSERVE,
                        f"{name} is required by the active goal; observe price movement before manual action.",
                        list(graph.evidence.keys()),
                        value_by_entity.get(item_id),
                        reservations.get(item_id),
                    )
                )
        else:
            signals.append(
                _checked_signal(
                    item_id,
                    name,
                    MarketSignalType.HOLD,
                    f"{name} is required by an active goal; hold required quantities.",
                    list(graph.evidence.keys()),
                    value_by_entity.get(item_id),
                    reservations.get(item_id),
                )
            )

    for state in graph.player_state:
        if state.entity_id in required_ids or state.entity_id in reserved_ids or state.quantity <= 0:
            continue
        entity = graph.entities.get(state.entity_id)
        if entity and entity.properties.get("tradable", False):
            value_holding = value_by_entity.get(state.entity_id)
            surplus_quantity = value_holding.sellable_surplus_quantity if value_holding else state.quantity
            if surplus_quantity <= 0:
                continue
            signals.append(
                _checked_signal(
                    state.entity_id,
                    entity.canonical_name,
                    MarketSignalType.CONSIDER_SELL_SURPLUS,
                    f"{entity.canonical_name} is not reserved for active goals; consider only true surplus after manual review.",
                    list(graph.evidence.keys()),
                    value_holding,
                    reservations.get(state.entity_id),
                )
            )
    return signals


def build_market_radar_report(
    session: Session,
    graph: GraphData,
    goal_id: str = "gw2:goal:aurora",
    user_id: str = DEFAULT_USER_ID,
) -> MarketRadarReport:
    watchlist = list_watchlist(session, user_id)
    watch_ids = [item.item_id for item in watchlist] or None
    trends = calculate_price_trends(session, watch_ids)
    value_snapshot = build_account_value_snapshot(graph, session, top_limit=10000)
    return MarketRadarReport(
        watchlist=watchlist,
        trends=trends,
        goal_cost_index=calculate_goal_cost_index(session, graph, goal_id),
        signals=infer_market_signals(session, graph, goal_id, value_snapshot),
        account_value_evidence=build_account_value_evidence_bridge(value_snapshot),
    )


def render_market_report(report: MarketRadarReport) -> str:
    lines = [
        "# Market Radar Report",
        "",
        "## Watchlist",
        *([f"- {item.item_name}: {item.reason}" for item in report.watchlist] or ["- None"]),
        "",
        "## Price Trends",
        *(
            [
                f"- {trend.item_name}: {trend.direction}, latest {trend.latest_sell_price_copper} copper, average {trend.average_sell_price_copper:.1f} copper"
                for trend in report.trends
            ]
            or ["- No trend data available."]
        ),
        "",
        "## Goal Cost Index",
        f"- Total missing cost: {report.goal_cost_index.total_missing_cost_copper if report.goal_cost_index else 0} copper",
        "",
        "## Market Signals",
        *[
            f"- {signal.item_name}: {signal.explanation}{_signal_context(signal)}"
            for signal in report.signals
        ],
        "",
        *(
            [*render_account_value_evidence_bridge_markdown(report.account_value_evidence), ""]
            if report.account_value_evidence
            else []
        ),
        "## Boundaries",
        "- Recommendations are observation and planning guidance only.",
        "- This report never places orders, never automates trades, and never supports real-money exchange.",
    ]
    text = "\n".join(lines) + "\n"
    validate_market_language(text)
    return text


def _signal_context(signal: MarketSignal) -> str:
    details = []
    if signal.reserved_quantity > 0:
        details.append(f"reserved {signal.reserved_quantity:g}")
    if signal.sellable_surplus_quantity > 0:
        details.append(f"surplus {signal.sellable_surplus_quantity:g}")
    if signal.valuation_status:
        details.append(f"value status {signal.valuation_status}")
    return f" ({'; '.join(details)})" if details else ""


def validate_market_language(text: str) -> None:
    lower = text.lower()
    for phrase in FORBIDDEN_MARKET_LANGUAGE:
        if phrase in lower:
            raise ValueError(f"Forbidden market language detected: {phrase}")


def _trend_for_rows(rows: list[MarketSnapshotModel]) -> PriceTrend:
    latest = rows[-1]
    average = sum(row.sell_price_copper for row in rows) / len(rows)
    delta = ((latest.sell_price_copper - average) / average * 100) if average else 0.0
    direction = "up" if delta > 5 else "down" if delta < -5 else "flat"
    spread_values = [abs(row.sell_price_copper - average) for row in rows]
    volatility = min((sum(spread_values) / len(spread_values) / average) if average else 0.0, 1.0)
    liquidity = min(latest.volume / 10000, 1.0)
    return PriceTrend(
        item_id=latest.item_id,
        item_name=latest.item_name,
        latest_sell_price_copper=latest.sell_price_copper,
        average_sell_price_copper=round(average, 2),
        delta_from_average_percent=round(delta, 2),
        direction=direction,
        volatility_score=round(volatility, 3),
        liquidity_score=round(liquidity, 3),
    )


def _latest_snapshot_by_item(session: Session) -> dict[str, MarketSnapshotModel]:
    rows = session.query(MarketSnapshotModel).order_by(MarketSnapshotModel.observed_at).all()
    latest: dict[str, MarketSnapshotModel] = {}
    for row in rows:
        latest[row.item_id] = row
    return latest


def _checked_signal(
    item_id: str,
    item_name: str,
    signal_type: MarketSignalType,
    explanation: str,
    evidence_refs: list[str],
    value_holding=None,
    reservation: dict | None = None,
) -> MarketSignal:
    validate_market_language(explanation)
    reservation = reservation or {}
    return MarketSignal(
        item_id=item_id,
        item_name=item_name,
        signal_type=signal_type,
        explanation=explanation,
        valuation_status=value_holding.valuation_status if value_holding else None,
        value_buy_copper=value_holding.value_buy_copper if value_holding else 0,
        net_sell_value_copper=value_holding.net_sell_value_copper if value_holding else 0,
        reserved_quantity=float(reservation.get("reserved_quantity", 0.0) or 0.0),
        sellable_surplus_quantity=float(reservation.get("sellable_surplus_quantity", 0.0) or 0.0),
        reserved_for_goal_ids=list(reservation.get("reserved_for_goal_ids", [])),
        evidence_refs=evidence_refs,
    )


def _snapshot_from_model(row: MarketSnapshotModel) -> PriceSnapshot:
    return PriceSnapshot(
        snapshot_id=row.snapshot_id,
        item_id=row.item_id,
        item_name=row.item_name,
        buy_price_copper=row.buy_price_copper,
        sell_price_copper=row.sell_price_copper,
        volume=row.volume,
        source=row.source,
        observed_at=row.observed_at,
    )


def _watch_from_model(row: MarketWatchlistModel) -> ItemWatch:
    return ItemWatch(
        watch_id=row.watch_id,
        user_id=row.user_id,
        item_id=row.item_id,
        item_name=row.item_name,
        reason=row.reason,
        created_at=row.created_at,
    )


def _chunks(values: list[int], chunk_size: int):
    for index in range(0, len(values), chunk_size):
        yield values[index:index + chunk_size]
