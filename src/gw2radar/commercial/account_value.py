from pydantic import BaseModel, Field

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.graph_layers import GraphLayer


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
    if location_type in {"wallet", "tradingpost"}:
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
