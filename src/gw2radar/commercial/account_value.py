from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import LegendaryGoalModel, MarketSnapshotModel
from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.graph_layers import GraphLayer


TP_TOTAL_FEE_RATE = 0.15
DEFAULT_STALE_PRICE_HOURS = 48


class AccountHolding(BaseModel):
    holding_id: str
    account_id: str
    entity_id: str
    item_id: int | None = None
    canonical_name: str
    quantity: float
    location_type: str
    location_ref: str | None = None
    graph_layer: GraphLayer = GraphLayer.PRIVATE_PLAYER_STATE
    valuation_status: str = "pending_price"
    tradable: bool | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    privacy_boundary: str = "private_summary_only"


class AccountHoldingCoverageGap(BaseModel):
    module_id: str
    label: str
    required_permissions: list[str]
    player_message: str


class AccountHoldingIndex(BaseModel):
    schema_version: str = "gw2radar.account_holding_index.v1"
    account_id: str | None
    holding_count: int
    location_counts: dict[str, int] = Field(default_factory=dict)
    holdings: list[AccountHolding] = Field(default_factory=list)
    coverage_gaps: list[AccountHoldingCoverageGap] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)


class AccountValueHolding(BaseModel):
    holding_id: str
    entity_id: str
    item_id: int | None = None
    canonical_name: str
    quantity: float
    location_type: str
    valuation_status: str
    buy_price_copper: int = 0
    sell_price_copper: int = 0
    value_buy_copper: int = 0
    value_sell_copper: int = 0
    net_sell_value_copper: int = 0
    reserved_quantity: float = 0.0
    sellable_surplus_quantity: float = 0.0
    reserved_for_goal_ids: list[str] = Field(default_factory=list)
    price_observed_at: datetime | None = None
    warning_codes: list[str] = Field(default_factory=list)


class AccountValueSummary(BaseModel):
    total_value_buy_copper: int = 0
    total_value_sell_copper: int = 0
    net_sell_value_copper: int = 0
    priced_holding_count: int = 0
    unpriced_holding_count: int = 0
    account_bound_holding_count: int = 0
    stale_price_holding_count: int = 0
    reserved_holding_count: int = 0
    coverage_gap_count: int = 0
    latest_price_observed_at: datetime | None = None


class AccountValueBreakdownRow(BaseModel):
    key: str
    label: str
    holding_count: int = 0
    value_buy_copper: int = 0
    value_sell_copper: int = 0
    net_sell_value_copper: int = 0
    percentage_of_buy_value: float = 0.0


class AccountValueWarning(BaseModel):
    warning_code: str
    severity: str
    player_message: str
    holding_id: str | None = None
    entity_id: str | None = None


class AccountValueSourceInsight(BaseModel):
    key: str
    label: str
    holding_count: int = 0
    priced_holding_count: int = 0
    unpriced_holding_count: int = 0
    account_bound_holding_count: int = 0
    stale_price_holding_count: int = 0
    reserved_holding_count: int = 0
    value_buy_copper: int = 0
    net_sell_value_copper: int = 0
    price_coverage_percent: float = 0.0
    readiness_label: str = "needs_data"
    action_hint: str = "Sync account data and refresh price observations before relying on this source."


class AccountValueRemediationAction(BaseModel):
    action_id: str
    priority: str
    label: str
    reason: str
    related_warning_codes: list[str] = Field(default_factory=list)
    ui_action: str | None = None


class AccountValueDiagnostics(BaseModel):
    schema_version: str = "gw2radar.account_value_diagnostics.v1"
    value_coverage_percent: float = 0.0
    price_coverage_percent: float = 0.0
    freshness_label: str = "unknown"
    source_insights: list[AccountValueSourceInsight] = Field(default_factory=list)
    remediation_actions: list[AccountValueRemediationAction] = Field(default_factory=list)
    visualization_notes: list[str] = Field(default_factory=list)


class AccountValueEvidenceBridge(BaseModel):
    schema_version: str = "gw2radar.account_value_evidence_bridge.v1"
    value_coverage_percent: float = 0.0
    price_coverage_percent: float = 0.0
    freshness_label: str = "unknown"
    source_summary: list[str] = Field(default_factory=list)
    remediation_summary: list[str] = Field(default_factory=list)
    do_not_sell_note_count: int = 0
    warning_count: int = 0
    boundary: str = "Account value evidence is summary-only planning context; it excludes raw API keys and private source payloads."


class AccountValueSnapshot(BaseModel):
    schema_version: str = "gw2radar.account_value_snapshot.v1"
    account_id: str | None
    summary: AccountValueSummary
    by_location: list[AccountValueBreakdownRow] = Field(default_factory=list)
    by_status: list[AccountValueBreakdownRow] = Field(default_factory=list)
    top_holdings: list[AccountValueHolding] = Field(default_factory=list)
    warnings: list[AccountValueWarning] = Field(default_factory=list)
    diagnostics: AccountValueDiagnostics = Field(default_factory=AccountValueDiagnostics)
    assumptions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)


MODULE_LOCATION_MAP = {
    "wallet_value": {"wallet"},
    "material_value": {"materials"},
    "bank_value": {"bank", "shared_inventory"},
    "character_inventory_and_gear": {"character", "character_equipment"},
    "tradingpost_orders": {"tradingpost"},
}


def build_account_holding_index(
    graph: GraphData,
    *,
    permission_report: dict | None = None,
    include_holdings: bool = True,
) -> AccountHoldingIndex:
    holdings = [_holding_from_state(graph, state) for state in graph.player_state if state.graph_layer is GraphLayer.PRIVATE_PLAYER_STATE]
    holdings = [holding for holding in holdings if holding is not None]
    location_counts: dict[str, int] = {}
    for holding in holdings:
        location_counts[holding.location_type] = location_counts.get(holding.location_type, 0) + 1
    coverage_gaps = _coverage_gaps(permission_report)
    assumptions = []
    if not graph.player_state:
        assumptions.append("No synced private account snapshot is available yet.")
    if coverage_gaps:
        assumptions.append("Missing API permissions create holding coverage gaps; do not infer absent items are unowned.")
    return AccountHoldingIndex(
        account_id=graph.account_id,
        holding_count=len(holdings),
        location_counts=location_counts,
        holdings=holdings if include_holdings else [],
        coverage_gaps=coverage_gaps,
        assumptions=assumptions,
        safety_boundaries=[
            "Holdings are derived private summaries, not raw GW2 API payloads.",
            "Raw API keys are never included in the holding index.",
            "Value and sellability require a separate price snapshot and do-not-sell policy review.",
        ],
    )


def build_account_value_snapshot(
    graph: GraphData,
    session: Session,
    *,
    permission_report: dict | None = None,
    stale_price_hours: int = DEFAULT_STALE_PRICE_HOURS,
    top_limit: int = 10,
) -> AccountValueSnapshot:
    index = build_account_holding_index(graph, permission_report=permission_report)
    latest_prices = _latest_market_snapshots(session)
    reservations = build_goal_reservation_index(session, graph)
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_price_hours)
    value_holdings = [
        _value_holding(holding, latest_prices, stale_cutoff, reservations)
        for holding in index.holdings
    ]
    summary = _value_summary(value_holdings, index.coverage_gaps)
    warnings = _value_warnings(value_holdings, index.coverage_gaps, stale_price_hours)
    diagnostics = _value_diagnostics(value_holdings, warnings, summary)
    top_holdings = sorted(value_holdings, key=lambda item: item.value_buy_copper, reverse=True)[:top_limit]
    assumptions = list(index.assumptions)
    assumptions.extend(
        [
            "Prices come from the latest stored market snapshot for each item.",
            "Net sell value applies a conservative 15 percent trading post fee.",
            "Unpriced, account-bound, and stale-price holdings are not inferred or auto-sold.",
        ]
    )
    return AccountValueSnapshot(
        account_id=index.account_id,
        summary=summary,
        by_location=_breakdown(value_holdings, key_attr="location_type", total_buy=summary.total_value_buy_copper),
        by_status=_breakdown(value_holdings, key_attr="valuation_status", total_buy=summary.total_value_buy_copper),
        top_holdings=top_holdings,
        warnings=warnings,
        diagnostics=diagnostics,
        assumptions=assumptions,
        safety_boundaries=[
            "Account value is informational planning guidance only.",
            "GW2Radar never places orders, never automates trades, and never guarantees returns.",
            "Private account payloads and raw API keys are excluded from this snapshot.",
            "Review active goals and do-not-sell reservations before considering any manual sale.",
        ],
    )


def build_goal_reservation_index(session: Session, graph: GraphData) -> dict[str, dict]:
    goal_ids = _active_goal_ids(session, graph)
    reservation_index: dict[str, dict] = {}
    for goal_id in goal_ids:
        if goal_id not in graph.entities:
            continue
        gap = calculate_goal_gap(graph, goal_id)
        for item in gap.completed_requirements + gap.missing_requirements:
            entry = reservation_index.setdefault(
                item.entity_id,
                {
                    "name": item.name,
                    "total_required_quantity": 0.0,
                    "owned_quantity": graph.quantity_owned(item.entity_id),
                    "reserved_quantity": 0.0,
                    "reserved_for_goal_ids": [],
                },
            )
            entry["total_required_quantity"] += item.required_quantity
            entry["owned_quantity"] = graph.quantity_owned(item.entity_id)
            if goal_id not in entry["reserved_for_goal_ids"]:
                entry["reserved_for_goal_ids"].append(goal_id)
    for entry in reservation_index.values():
        entry["reserved_quantity"] = min(entry["owned_quantity"], entry["total_required_quantity"])
        entry["sellable_surplus_quantity"] = max(entry["owned_quantity"] - entry["total_required_quantity"], 0.0)
    return reservation_index


def render_account_value_snapshot_markdown(snapshot: AccountValueSnapshot) -> str:
    lines = [
        "# Account Value Snapshot",
        "",
        "## Summary",
        f"- Total buy value: {snapshot.summary.total_value_buy_copper} copper",
        f"- Total sell value: {snapshot.summary.total_value_sell_copper} copper",
        f"- Net sell value after TP fee: {snapshot.summary.net_sell_value_copper} copper",
        f"- Priced holdings: {snapshot.summary.priced_holding_count}",
        f"- Unpriced holdings: {snapshot.summary.unpriced_holding_count}",
        f"- Account-bound holdings: {snapshot.summary.account_bound_holding_count}",
        f"- Stale-price holdings: {snapshot.summary.stale_price_holding_count}",
        f"- Value coverage: {snapshot.diagnostics.value_coverage_percent}%",
        f"- Price coverage: {snapshot.diagnostics.price_coverage_percent}%",
        f"- Freshness: {snapshot.diagnostics.freshness_label}",
        "",
        "## Location Breakdown",
        *[
            f"- {row.label}: {row.value_buy_copper} copper across {row.holding_count} holdings"
            for row in snapshot.by_location
        ],
        "",
        *render_account_value_evidence_bridge_markdown(build_account_value_evidence_bridge(snapshot)),
        "",
        "## Source Diagnostics",
        *[
            f"- {row.label}: {row.readiness_label}, {row.price_coverage_percent}% priced, {row.action_hint}"
            for row in snapshot.diagnostics.source_insights
        ],
        "",
        "## Remediation Actions",
        *([f"- {action.priority}: {action.label} - {action.reason}" for action in snapshot.diagnostics.remediation_actions] or ["- None"]),
        "",
        "## Warnings",
        *([f"- {warning.severity}: {warning.player_message}" for warning in snapshot.warnings] or ["- None"]),
        "",
        "## Boundaries",
        *[f"- {boundary}" for boundary in snapshot.safety_boundaries],
    ]
    return "\n".join(lines) + "\n"


def build_account_value_evidence_bridge(snapshot: AccountValueSnapshot) -> AccountValueEvidenceBridge:
    return AccountValueEvidenceBridge(
        value_coverage_percent=snapshot.diagnostics.value_coverage_percent,
        price_coverage_percent=snapshot.diagnostics.price_coverage_percent,
        freshness_label=snapshot.diagnostics.freshness_label,
        source_summary=[
            f"{source.label}: {source.readiness_label}, {source.price_coverage_percent}% priced, {source.holding_count} holdings"
            for source in snapshot.diagnostics.source_insights[:6]
        ],
        remediation_summary=[
            f"{action.priority} {action.label}: {action.reason}"
            for action in snapshot.diagnostics.remediation_actions[:6]
        ],
        do_not_sell_note_count=snapshot.summary.reserved_holding_count,
        warning_count=len(snapshot.warnings),
    )


def render_account_value_evidence_bridge_markdown(bridge: AccountValueEvidenceBridge) -> list[str]:
    return [
        "## Account Value Evidence Bridge",
        f"- Value coverage: {bridge.value_coverage_percent}%",
        f"- Price coverage: {bridge.price_coverage_percent}%",
        f"- Freshness: {bridge.freshness_label}",
        f"- Do-not-sell note count: {bridge.do_not_sell_note_count}",
        f"- Warning count: {bridge.warning_count}",
        "- Source summary:",
        *([f"  - {line}" for line in bridge.source_summary] or ["  - No source summary available."]),
        "- Remediation summary:",
        *([f"  - {line}" for line in bridge.remediation_summary] or ["  - No remediation summary available."]),
        f"- Boundary: {bridge.boundary}",
    ]


def render_account_value_snapshot_csv(snapshot: AccountValueSnapshot) -> str:
    lines = ["holding_id,entity_id,name,location,status,quantity,buy_price_copper,sell_price_copper,value_buy_copper,value_sell_copper,net_sell_value_copper"]
    for holding in snapshot.top_holdings:
        lines.append(
            ",".join(
                [
                    _csv(holding.holding_id),
                    _csv(holding.entity_id),
                    _csv(holding.canonical_name),
                    _csv(holding.location_type),
                    _csv(holding.valuation_status),
                    str(holding.quantity),
                    str(holding.buy_price_copper),
                    str(holding.sell_price_copper),
                    str(holding.value_buy_copper),
                    str(holding.value_sell_copper),
                    str(holding.net_sell_value_copper),
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _holding_from_state(graph: GraphData, state) -> AccountHolding | None:
    entity = graph.entities.get(state.entity_id)
    if entity is None:
        return None
    location_type, location_ref = _split_location(state.location)
    item_id = _entity_item_id(state.entity_id)
    return AccountHolding(
        holding_id=f"holding:{state.account_id}:{state.entity_id}:{state.location or 'unknown'}",
        account_id=state.account_id,
        entity_id=state.entity_id,
        item_id=item_id,
        canonical_name=entity.canonical_name,
        quantity=state.quantity,
        location_type=location_type,
        location_ref=location_ref,
        tradable=_initial_tradable(location_type, entity.properties),
        evidence_refs=_evidence_refs_for_entity(graph, state.entity_id),
    )


def _split_location(location: str | None) -> tuple[str, str | None]:
    if not location:
        return "unknown", None
    if ":" not in location:
        return location, None
    location_type, location_ref = location.split(":", 1)
    return location_type, location_ref or None


def _entity_item_id(entity_id: str) -> int | None:
    if not entity_id.startswith("gw2:item:"):
        return None
    try:
        return int(entity_id.removeprefix("gw2:item:"))
    except ValueError:
        return None


def _initial_tradable(location_type: str, properties: dict) -> bool | None:
    if location_type in {"wallet", "tradingpost", "tradingpost_buy", "tradingpost_sell"}:
        return True
    if location_type == "character_equipment":
        return False
    if properties.get("binding") or properties.get("binding_status"):
        return False
    return None


def _evidence_refs_for_entity(graph: GraphData, entity_id: str) -> list[str]:
    refs = [
        relation.evidence_id
        for relation in graph.relations
        if relation.object_id == entity_id and relation.evidence_id
    ]
    return sorted(set(ref for ref in refs if ref))


def _coverage_gaps(permission_report: dict | None) -> list[AccountHoldingCoverageGap]:
    if not permission_report:
        return []
    gaps: list[AccountHoldingCoverageGap] = []
    for module in permission_report.get("blocked_analysis_modules", []):
        module_id = module.get("module_id")
        if module_id not in MODULE_LOCATION_MAP:
            continue
        gaps.append(
            AccountHoldingCoverageGap(
                module_id=module_id,
                label=module.get("label", module_id),
                required_permissions=list(module.get("required_permissions", [])),
                player_message=module.get("player_message", "Missing permissions limit account holding coverage."),
            )
        )
    return gaps


def _latest_market_snapshots(session: Session) -> dict[str, MarketSnapshotModel]:
    rows = session.query(MarketSnapshotModel).order_by(MarketSnapshotModel.observed_at).all()
    latest: dict[str, MarketSnapshotModel] = {}
    for row in rows:
        latest[row.item_id] = row
    return latest


def _value_holding(
    holding: AccountHolding,
    latest_prices: dict[str, MarketSnapshotModel],
    stale_cutoff: datetime,
    reservations: dict[str, dict],
) -> AccountValueHolding:
    warning_codes: list[str] = []
    reservation = reservations.get(holding.entity_id, {})
    reserved_quantity = float(reservation.get("reserved_quantity", 0.0) or 0.0)
    sellable_surplus_quantity = max(float(holding.quantity) - reserved_quantity, 0.0)
    reserved_for_goal_ids = list(reservation.get("reserved_for_goal_ids", []))
    if reserved_quantity > 0:
        warning_codes.append("reserved_for_goal")
    if holding.location_type == "wallet":
        value = int(holding.quantity)
        return AccountValueHolding(
            holding_id=holding.holding_id,
            entity_id=holding.entity_id,
            item_id=holding.item_id,
            canonical_name=holding.canonical_name,
            quantity=holding.quantity,
            location_type=holding.location_type,
            valuation_status="priced",
            buy_price_copper=1,
            sell_price_copper=1,
            value_buy_copper=value,
            value_sell_copper=value,
            net_sell_value_copper=value,
            reserved_quantity=reserved_quantity,
            sellable_surplus_quantity=sellable_surplus_quantity,
            reserved_for_goal_ids=reserved_for_goal_ids,
            warning_codes=warning_codes,
        )
    if holding.tradable is False:
        return AccountValueHolding(
            holding_id=holding.holding_id,
            entity_id=holding.entity_id,
            item_id=holding.item_id,
            canonical_name=holding.canonical_name,
            quantity=holding.quantity,
            location_type=holding.location_type,
            valuation_status="account_bound",
            reserved_quantity=reserved_quantity,
            sellable_surplus_quantity=sellable_surplus_quantity,
            reserved_for_goal_ids=reserved_for_goal_ids,
            warning_codes=[*warning_codes, "account_bound"],
        )
    snapshot = latest_prices.get(holding.entity_id)
    if snapshot is None and holding.item_id is not None:
        snapshot = latest_prices.get(f"gw2:item:{holding.item_id}") or latest_prices.get(str(holding.item_id))
    if snapshot is None:
        return AccountValueHolding(
            holding_id=holding.holding_id,
            entity_id=holding.entity_id,
            item_id=holding.item_id,
            canonical_name=holding.canonical_name,
            quantity=holding.quantity,
            location_type=holding.location_type,
            valuation_status="unpriced",
            reserved_quantity=reserved_quantity,
            sellable_surplus_quantity=sellable_surplus_quantity,
            reserved_for_goal_ids=reserved_for_goal_ids,
            warning_codes=[*warning_codes, "missing_price"],
        )
    observed_at = _aware(snapshot.observed_at)
    if observed_at < stale_cutoff:
        warning_codes.append("stale_price")
    buy_value = int(holding.quantity * snapshot.buy_price_copper)
    sell_value = int(holding.quantity * snapshot.sell_price_copper)
    return AccountValueHolding(
        holding_id=holding.holding_id,
        entity_id=holding.entity_id,
        item_id=holding.item_id,
        canonical_name=holding.canonical_name,
        quantity=holding.quantity,
        location_type=holding.location_type,
        valuation_status="stale_price" if "stale_price" in warning_codes else "priced",
        buy_price_copper=snapshot.buy_price_copper,
        sell_price_copper=snapshot.sell_price_copper,
        value_buy_copper=buy_value,
        value_sell_copper=sell_value,
        net_sell_value_copper=int(sell_value * (1 - TP_TOTAL_FEE_RATE)),
        reserved_quantity=reserved_quantity,
        sellable_surplus_quantity=sellable_surplus_quantity,
        reserved_for_goal_ids=reserved_for_goal_ids,
        price_observed_at=observed_at,
        warning_codes=warning_codes,
    )


def _value_summary(
    holdings: list[AccountValueHolding],
    coverage_gaps: list[AccountHoldingCoverageGap],
) -> AccountValueSummary:
    priced = [holding for holding in holdings if holding.valuation_status in {"priced", "stale_price"}]
    latest = [holding.price_observed_at for holding in holdings if holding.price_observed_at is not None]
    return AccountValueSummary(
        total_value_buy_copper=sum(holding.value_buy_copper for holding in priced),
        total_value_sell_copper=sum(holding.value_sell_copper for holding in priced),
        net_sell_value_copper=sum(holding.net_sell_value_copper for holding in priced),
        priced_holding_count=sum(1 for holding in holdings if holding.valuation_status == "priced"),
        unpriced_holding_count=sum(1 for holding in holdings if holding.valuation_status == "unpriced"),
        account_bound_holding_count=sum(1 for holding in holdings if holding.valuation_status == "account_bound"),
        stale_price_holding_count=sum(1 for holding in holdings if holding.valuation_status == "stale_price"),
        reserved_holding_count=sum(1 for holding in holdings if holding.reserved_quantity > 0),
        coverage_gap_count=len(coverage_gaps),
        latest_price_observed_at=max(latest) if latest else None,
    )


def _breakdown(
    holdings: list[AccountValueHolding],
    *,
    key_attr: str,
    total_buy: int,
) -> list[AccountValueBreakdownRow]:
    rows: dict[str, AccountValueBreakdownRow] = {}
    for holding in holdings:
        key = str(getattr(holding, key_attr))
        row = rows.setdefault(key, AccountValueBreakdownRow(key=key, label=_label(key)))
        row.holding_count += 1
        row.value_buy_copper += holding.value_buy_copper
        row.value_sell_copper += holding.value_sell_copper
        row.net_sell_value_copper += holding.net_sell_value_copper
    for row in rows.values():
        row.percentage_of_buy_value = round(row.value_buy_copper / total_buy * 100, 2) if total_buy else 0.0
    return sorted(rows.values(), key=lambda item: item.value_buy_copper, reverse=True)


def _value_diagnostics(
    holdings: list[AccountValueHolding],
    warnings: list[AccountValueWarning],
    summary: AccountValueSummary,
) -> AccountValueDiagnostics:
    total_holdings = len(holdings)
    priced_like = sum(1 for holding in holdings if holding.valuation_status in {"priced", "stale_price"})
    fresh_priced = sum(1 for holding in holdings if holding.valuation_status == "priced")
    actionable_holdings = sum(1 for holding in holdings if holding.valuation_status != "account_bound")
    source_insights = _source_insights(holdings)
    warning_codes = {warning.warning_code for warning in warnings}
    latest = _aware(summary.latest_price_observed_at) if summary.latest_price_observed_at else None
    freshness_label = "no_prices"
    if latest is not None:
        age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
        freshness_label = "fresh" if age_hours <= DEFAULT_STALE_PRICE_HOURS else "stale"
    return AccountValueDiagnostics(
        value_coverage_percent=round(priced_like / total_holdings * 100, 2) if total_holdings else 0.0,
        price_coverage_percent=round(fresh_priced / actionable_holdings * 100, 2) if actionable_holdings else 0.0,
        freshness_label=freshness_label,
        source_insights=source_insights,
        remediation_actions=_remediation_actions(warning_codes, summary),
        visualization_notes=[
            "Value coverage counts holdings with any usable price, including stale observations.",
            "Price coverage counts fresh priced holdings and excludes account-bound holdings from the denominator.",
            "Source diagnostics are private summaries only and do not expose raw GW2 API payloads.",
        ],
    )


def _source_insights(holdings: list[AccountValueHolding]) -> list[AccountValueSourceInsight]:
    rows: dict[str, AccountValueSourceInsight] = {}
    for holding in holdings:
        row = rows.setdefault(
            holding.location_type,
            AccountValueSourceInsight(key=holding.location_type, label=_label(holding.location_type)),
        )
        row.holding_count += 1
        row.value_buy_copper += holding.value_buy_copper
        row.net_sell_value_copper += holding.net_sell_value_copper
        if holding.valuation_status == "priced":
            row.priced_holding_count += 1
        elif holding.valuation_status == "unpriced":
            row.unpriced_holding_count += 1
        elif holding.valuation_status == "account_bound":
            row.account_bound_holding_count += 1
        elif holding.valuation_status == "stale_price":
            row.stale_price_holding_count += 1
        if holding.reserved_quantity > 0:
            row.reserved_holding_count += 1
    for row in rows.values():
        actionable = max(row.holding_count - row.account_bound_holding_count, 0)
        fresh_priced = row.priced_holding_count
        row.price_coverage_percent = round(fresh_priced / actionable * 100, 2) if actionable else 0.0
        row.readiness_label = _source_readiness(row)
        row.action_hint = _source_action_hint(row)
    return sorted(rows.values(), key=lambda item: (item.value_buy_copper, item.holding_count), reverse=True)


def _source_readiness(row: AccountValueSourceInsight) -> str:
    if row.holding_count == 0:
        return "empty"
    if row.unpriced_holding_count == 0 and row.stale_price_holding_count == 0:
        return "ready"
    if row.priced_holding_count > 0 or row.stale_price_holding_count > 0:
        return "partial"
    return "needs_price"


def _source_action_hint(row: AccountValueSourceInsight) -> str:
    if row.unpriced_holding_count > 0:
        return "Refresh official prices, then add manual snapshots for non-tradable or symbolic ids."
    if row.stale_price_holding_count > 0:
        return "Refresh official prices before expensive crafting or sell decisions."
    if row.reserved_holding_count > 0:
        return "Review active goals before treating this source as sellable surplus."
    return "Ready for planning review; still treat this as informational guidance only."


def _remediation_actions(
    warning_codes: set[str],
    summary: AccountValueSummary,
) -> list[AccountValueRemediationAction]:
    actions: list[AccountValueRemediationAction] = []
    if "missing_permission" in warning_codes:
        actions.append(
            AccountValueRemediationAction(
                action_id="check_api_permissions",
                priority="P0",
                label="Check API key permissions",
                reason="Missing permissions mean some account sources are absent from value analysis.",
                related_warning_codes=["missing_permission"],
                ui_action="apiKeyPermissions",
            )
        )
    if "missing_price" in warning_codes:
        actions.append(
            AccountValueRemediationAction(
                action_id="refresh_official_prices",
                priority="P1",
                label="Refresh official prices",
                reason=f"{summary.unpriced_holding_count} holdings are excluded from value totals until priced.",
                related_warning_codes=["missing_price"],
                ui_action="refreshOfficialPrices",
            )
        )
    if "stale_price" in warning_codes:
        actions.append(
            AccountValueRemediationAction(
                action_id="refresh_stale_prices",
                priority="P1",
                label="Refresh stale prices",
                reason=f"{summary.stale_price_holding_count} holdings use older price observations.",
                related_warning_codes=["stale_price"],
                ui_action="refreshOfficialPrices",
            )
        )
    if "reserved_for_goal" in warning_codes:
        actions.append(
            AccountValueRemediationAction(
                action_id="review_do_not_sell",
                priority="P2",
                label="Review do-not-sell reservations",
                reason=f"{summary.reserved_holding_count} holdings are reserved by active goals.",
                related_warning_codes=["reserved_for_goal"],
            )
        )
    if not actions:
        actions.append(
            AccountValueRemediationAction(
                action_id="review_value_sources",
                priority="P3",
                label="Review value source mix",
                reason="No blocking value warnings are present; compare sources before manual planning decisions.",
            )
        )
    return actions


def _value_warnings(
    holdings: list[AccountValueHolding],
    coverage_gaps: list[AccountHoldingCoverageGap],
    stale_price_hours: int,
) -> list[AccountValueWarning]:
    warnings: list[AccountValueWarning] = []
    for gap in coverage_gaps:
        warnings.append(
            AccountValueWarning(
                warning_code="missing_permission",
                severity="warn",
                player_message=f"{gap.label} is unavailable until permissions include {', '.join(gap.required_permissions)}.",
            )
        )
    for holding in holdings:
        if "missing_price" in holding.warning_codes:
            warnings.append(
                AccountValueWarning(
                    warning_code="missing_price",
                    severity="info",
                    player_message=f"{holding.canonical_name} has no stored price snapshot, so it is excluded from value totals.",
                    holding_id=holding.holding_id,
                    entity_id=holding.entity_id,
                )
            )
        if "account_bound" in holding.warning_codes:
            warnings.append(
                AccountValueWarning(
                    warning_code="account_bound",
                    severity="info",
                    player_message=f"{holding.canonical_name} is treated as account-bound or non-sellable.",
                    holding_id=holding.holding_id,
                    entity_id=holding.entity_id,
                )
            )
        if "stale_price" in holding.warning_codes:
            warnings.append(
                AccountValueWarning(
                    warning_code="stale_price",
                    severity="warn",
                    player_message=f"{holding.canonical_name} uses a price snapshot older than {stale_price_hours} hours.",
                    holding_id=holding.holding_id,
                    entity_id=holding.entity_id,
                )
            )
        if "reserved_for_goal" in holding.warning_codes:
            warnings.append(
                AccountValueWarning(
                    warning_code="reserved_for_goal",
                    severity="warn",
                    player_message=f"{holding.canonical_name} is reserved for active goals and should not be treated as sellable surplus.",
                    holding_id=holding.holding_id,
                    entity_id=holding.entity_id,
                )
            )
    return warnings[:50]


def _active_goal_ids(session: Session, graph: GraphData) -> list[str]:
    rows = (
        session.query(LegendaryGoalModel)
        .filter(LegendaryGoalModel.active.is_(True))
        .order_by(LegendaryGoalModel.priority, LegendaryGoalModel.created_at)
        .all()
    )
    goal_ids = [row.graph_goal_id for row in rows if row.graph_goal_id in graph.entities]
    if goal_ids:
        return goal_ids
    return ["gw2:goal:aurora"] if "gw2:goal:aurora" in graph.entities else []


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _label(value: str) -> str:
    return value.replace("_", " ").title()


def _csv(value: object) -> str:
    text = "" if value is None else str(value)
    escaped = text.replace('"', '""')
    return f'"{escaped}"'
