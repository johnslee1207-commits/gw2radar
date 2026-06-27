"""Tests for auto-discovery, serialization, bridges, trends, and audit."""

from pathlib import Path

from gw2radar.audit import AuditTrail
from gw2radar.bors.business_kpi import BusinessKPICalculator
from gw2radar.bors.business_risk import BusinessRiskModel
from gw2radar.bors.dashboard_trends import TrendTracker
from gw2radar.bors.decision_engine import DecisionEngine
from gw2radar.domain_graph.discovery import discover_from_enums, discover_graph_layers
from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.domain_graph.serializer import domain_graph_to_dict, serialize
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.oosk.action_bridge import OOSKActionBridge
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.pipeline import ThreeLayerPipeline


# ============================================================
# DGSK: Auto-discovery from existing enums
# ============================================================

def test_discover_from_enums() -> None:
    dg = discover_from_enums("TestDomain")
    assert dg.domain == "TestDomain"
    assert len(dg.nodes) >= 10
    assert "Account" in dg.nodes
    assert "Item" in dg.nodes
    assert "Goal" in dg.nodes
    assert len(dg.edges) >= 10
    assert len(dg.rules) >= 2


def test_discover_graph_layers() -> None:
    layers = discover_graph_layers()
    assert len(layers) >= 3
    names = [l["name"] for l in layers]
    assert "public_game" in names
    assert "private_player_state" in names


def test_discover_validate() -> None:
    dg = discover_from_enums("ValidateTest")
    engine = DomainGraphEngine()
    errors = engine.validate(dg)
    assert errors == [], f"Discovery validation errors: {errors}"


def test_discover_compile_to_oosk() -> None:
    dg = discover_from_enums("OOSKTest")
    engine = DomainGraphEngine()
    registry = engine.compile_to_oosk(dg)
    assert len(registry.domain_types) >= 10
    assert len(registry.relation_types) >= 10


# ============================================================
# DGSK: Serialization round-trip
# ============================================================

def test_serialize_round_trip() -> None:
    engine = DomainGraphEngine()
    original = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    data = domain_graph_to_dict(original)
    assert data["domain"] == "RF Simulation"
    assert len(data["nodes"]) >= 6
    assert len(data["edges"]) >= 6


def test_serialize_then_reload() -> None:
    import tempfile
    engine = DomainGraphEngine()
    original = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        tmp_path = f.name
    try:
        serialize(original, tmp_path)
        reloaded = engine.load_file(tmp_path)
        assert reloaded.domain == original.domain
        assert len(reloaded.nodes) == len(original.nodes)
        assert len(reloaded.edges) == len(original.edges)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def test_serialize_gw2_domain() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/gw2_player_progress/domain.yaml")))
    data = domain_graph_to_dict(dg)
    assert data["domain"] == "GW2 Player Progress"
    assert any("lifecycle" in n for n in data["nodes"])


def test_serialize_discovered_domain() -> None:
    dg = discover_from_enums("SerializedDiscovery")
    data = domain_graph_to_dict(dg)
    assert data["domain"] == "SerializedDiscovery"
    assert len(data["nodes"]) >= 10


# ============================================================
# OOSK: Action Bridge
# ============================================================

def test_action_bridge_list_actions() -> None:
    bridge = OOSKActionBridge()
    actions = bridge.list_actions()
    assert len(actions) >= 3
    assert "reserve_material_for_goal" in actions
    assert "generate_legendary_plan" in actions


def test_action_bridge_check_preconditions() -> None:
    bridge = OOSKActionBridge()
    failures = bridge.check_preconditions("nonexistent_action")
    assert len(failures) >= 1
    assert "not found" in failures[0]


def test_action_bridge_qa_suite() -> None:
    bridge = OOSKActionBridge()
    result = bridge.run_qa_suite()
    assert "passed" in result
    assert "summary" in result
    assert "results" in result


def test_action_bridge_impact_sell() -> None:
    bridge = OOSKActionBridge()
    graph = build_mock_graph()
    with_store = OOSKActionBridge(store=RuntimeStore(graph))
    item_ids = [eid for eid in graph.entities.keys() if eid.startswith("gw2:item:")]
    if item_ids:
        result = with_store.analyze_impact_sell(item_ids[0])
        assert "target" in result
        assert "risk" in result


def test_action_bridge_impact_goal() -> None:
    bridge = OOSKActionBridge()
    graph = build_mock_graph()
    with_store = OOSKActionBridge(store=RuntimeStore(graph))
    goal_ids = [eid for eid in graph.entities if eid.startswith("gw2:goal:")]
    if goal_ids:
        result = with_store.analyze_impact_goal(goal_ids[0])
        assert "target" in result


# ============================================================
# BORS: Dashboard Trends
# ============================================================

def test_trend_tracker_records() -> None:
    tracker = TrendTracker()
    calc = BusinessKPICalculator()
    risk_model = BusinessRiskModel()
    engine = DecisionEngine()

    kpis = calc.calculate_all(qa_gate={"passed": 5, "total": 5})
    risks = risk_model.assess_all(qa_gate={"passed": 5, "total": 5})
    decision = engine.decide("test", kpis=kpis)
    tracker.record(kpis, risks, [decision])

    assert len(tracker.all_metrics()) >= 3
    assert tracker.latest() != {}


def test_trend_tracker_series() -> None:
    tracker = TrendTracker()
    calc = BusinessKPICalculator()
    engine = DecisionEngine()

    for score in [1.0, 0.8, 0.6, 0.4, 0.2]:
        kpis = calc.calculate_all(qa_gate={"passed": int(score * 5), "total": 5})
        decision = engine.decide("test", kpis=kpis)
        tracker.record(kpis, [], [decision])

    series = tracker.series("kpi:quality_score")
    assert len(series) == 5
    assert series[0]["value"] == 1.0
    assert series[-1]["value"] == 0.2


def test_trend_tracker_trend_rising() -> None:
    tracker = TrendTracker()
    calc = BusinessKPICalculator()
    for score in [0.2, 0.3, 0.5, 0.7, 0.9]:
        kpis = calc.calculate_all(qa_gate={"passed": int(score * 5), "total": 5})
        tracker.record(kpis, [], [])

    trend = tracker.trend("kpi:quality_score")
    assert trend == "rising"


def test_trend_tracker_trend_falling() -> None:
    tracker = TrendTracker()
    calc = BusinessKPICalculator()
    for score in [0.9, 0.7, 0.5, 0.3, 0.1]:
        kpis = calc.calculate_all(qa_gate={"passed": int(score * 5), "total": 5})
        tracker.record(kpis, [], [])

    trend = tracker.trend("kpi:quality_score")
    assert trend == "falling"


def test_trend_tracker_trend_insufficient() -> None:
    tracker = TrendTracker()
    assert tracker.trend("nonexistent") == "insufficient_data"


def test_trend_tracker_summary() -> None:
    tracker = TrendTracker()
    calc = BusinessKPICalculator()
    for _ in range(3):
        kpis = calc.calculate_all(qa_gate={"passed": 5, "total": 5})
        tracker.record(kpis, [], [])

    s = tracker.summary()
    assert s["point_count"] == 3
    assert s["metric_count"] >= 1


def test_trend_tracker_max_points() -> None:
    tracker = TrendTracker(max_points=5)
    calc = BusinessKPICalculator()
    for _ in range(10):
        kpis = calc.calculate_all(qa_gate={"passed": 5, "total": 5})
        tracker.record(kpis, [], [])

    assert len(tracker.series("kpi:quality_score")) == 5


# ============================================================
# Cross-layer: Audit Trail
# ============================================================

def test_audit_trail_records() -> None:
    audit = AuditTrail()
    audit.record("DGSK", "load", duration_ms=10.5, success=True)
    audit.record("OOSK", "map", duration_ms=5.2, success=True)
    audit.record("BORS", "decide", duration_ms=3.1, success=True)

    assert len(audit.get_entries()) == 3
    assert len(audit.get_entries(layer="OOSK")) == 1


def test_audit_trail_summary() -> None:
    audit = AuditTrail()
    for i in range(5):
        audit.record("LAYER_A", f"op_{i}", success=i % 2 == 0)

    summary = audit.summary()
    assert summary["total_executions"] == 5
    assert summary["failures"] == 2


def test_audit_trail_latest_by_layer() -> None:
    audit = AuditTrail()
    for i in range(10):
        audit.record("LAYER_X", f"op_{i}")
    latest = audit.latest_by_layer("LAYER_X", n=3)
    assert len(latest) == 3


def test_audit_trail_clear() -> None:
    audit = AuditTrail()
    audit.record("TEST", "op")
    assert len(audit.get_entries()) == 1
    audit.clear()
    assert len(audit.get_entries()) == 0


# ============================================================
# Pipeline: Audit integration
# ============================================================

def test_pipeline_audit_records() -> None:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path("data/domain/rf_simulation/domain.yaml")),
        runtime_state={"qa_gate": {"passed": 5, "total": 5}},
    )
    assert "audit" in result
    assert result["audit"]["total_executions"] >= 4
    assert result["audit"]["success_rate"] > 0.5


def test_pipeline_trends_integration() -> None:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path("data/domain/rf_simulation/domain.yaml")),
        runtime_state={"qa_gate": {"passed": 5, "total": 5}},
    )
    assert "trends" in result
    assert result["trends"]["point_count"] >= 1


def test_pipeline_action_bridge_available() -> None:
    pipeline = ThreeLayerPipeline()
    pipeline.load_domain(str(Path("data/domain/rf_simulation/domain.yaml")))
    pipeline.map_to_oosk()
    assert pipeline.action_bridge is not None
    actions = pipeline.action_bridge.list_actions()
    assert len(actions) >= 3
