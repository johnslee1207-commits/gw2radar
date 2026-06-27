"""Cross-layer end-to-end pipeline test: DGSK → OOSK → BORS."""

from pathlib import Path

from gw2radar.bors.bors_compiler import BORSCompiler
from gw2radar.bors.business_risk import BusinessRiskModel, BusinessRiskType, RiskLevel
from gw2radar.bors.decision_engine import Decision, DecisionEngine
from gw2radar.bors.weight_calibrator import WeightCalibrator
from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.domain_graph.domain_schema import StateMachine, StateTransition
from gw2radar.oosk.concurrency import ConcurrentActionRegistry, LockManager
from gw2radar.oosk.runtime_mapper import RuntimeMapper
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.pipeline import ThreeLayerPipeline


# ============================================================
# DGSK: State Machine Tests
# ============================================================

def test_node_lifecycle_parsed() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    execution_run = dg.nodes.get("ExecutionRun")
    assert execution_run is not None
    assert execution_run.lifecycle is not None
    assert execution_run.lifecycle.initial_state == "pending"
    assert len(execution_run.lifecycle.states) == 4
    assert len(execution_run.lifecycle.transitions) == 3


def test_node_lifecycle_transitions() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    sm = dg.nodes["ExecutionRun"].lifecycle
    assert sm is not None
    t_from_pending = [t for t in sm.transitions if t.from_state == "pending"]
    assert len(t_from_pending) == 1
    assert t_from_pending[0].to_state == "running"
    assert t_from_pending[0].trigger == "start_run"


def test_node_lifecycle_invariants() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    sm = dg.nodes["ExecutionRun"].lifecycle
    assert sm is not None
    assert len(sm.invariants) == 1
    assert "terminal" in sm.invariants[0]


def test_state_machine_validation_passes() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    errors = engine.validate(dg)
    lifecycle_errors = [e for e in errors if "lifecycle" in e]
    assert lifecycle_errors == [], f"State machine validation errors: {lifecycle_errors}"


def test_state_machine_validation_detects_bad_state() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    er = dg.nodes["ExecutionRun"]
    assert er.lifecycle is not None
    er.lifecycle.transitions.append(
        StateTransition(from_state="nonexistent", to_state="running", trigger="bad")
    )
    errors = engine.validate(dg)
    lifecycle_errors = [e for e in errors if "lifecycle" in e]
    assert len(lifecycle_errors) >= 1
    assert "nonexistent" in lifecycle_errors[0]


def test_gw2_account_lifecycle() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/gw2_player_progress/domain.yaml")))
    account = dg.nodes.get("Account")
    assert account is not None
    assert account.lifecycle is not None
    assert account.lifecycle.initial_state == "active"
    close_transitions = [t for t in account.lifecycle.transitions if t.to_state == "closed"]
    assert len(close_transitions) == 2
    errors = engine.validate(dg)
    lifecycle_errors = [e for e in errors if "lifecycle" in e]
    assert lifecycle_errors == [], f"GW2 account lifecycle validation errors: {lifecycle_errors}"


# ============================================================
# DGSK: Property Constraint Tests
# ============================================================

def test_property_min_max_parsed() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/gw2_player_progress/domain.yaml")))
    account = dg.nodes["Account"]
    level_prop = next(p for p in account.properties if p.name == "level")
    assert level_prop.constraints is not None
    assert level_prop.constraints.min_value == 1.0
    assert level_prop.constraints.max_value == 80.0


def test_property_no_constraints_by_default() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    scene = dg.nodes["Scene"]
    id_prop = next(p for p in scene.properties if p.name == "id")
    assert id_prop.constraints is None


# ============================================================
# OOSK: Concurrency Control Tests (Patch 5)
# ============================================================

def test_lock_manager_acquire_release() -> None:
    lm = LockManager()
    with lm.acquire(["entity_a", "entity_b"], "test_owner"):
        assert lm.is_locked("entity_a")
        assert lm.is_locked("entity_b")
        assert lm.locked_by("entity_a") == "test_owner"
    assert not lm.is_locked("entity_a")
    assert not lm.is_locked("entity_b")


def test_lock_manager_ordering_prevents_deadlock() -> None:
    lm = LockManager()
    with lm.acquire(["z_entity", "a_entity"]):
        assert lm.is_locked("a_entity")
        assert lm.is_locked("z_entity")


def test_concurrent_action_registry() -> None:
    registry = {"test_action": {"name": "test"}}
    car = ConcurrentActionRegistry(registry)
    with car.execute("test_action", ["entity_1"]):
        assert car.lock_manager().is_locked("entity_1")
    assert not car.lock_manager().is_locked("entity_1")


def test_concurrent_action_registry_not_found() -> None:
    registry: dict = {}
    car = ConcurrentActionRegistry(registry)
    try:
        with car.execute("nonexistent", ["e"]):
            pass
        assert False, "Should have raised KeyError"
    except KeyError:
        pass


# ============================================================
# BORS: WeightCalibrator Tests (Patch 4)
# ============================================================

def test_weight_calibrator_empty_history() -> None:
    wc = WeightCalibrator()
    assert wc.calibrate() == {}


def test_weight_calibrator_tracks_records() -> None:
    wc = WeightCalibrator()
    for _ in range(5):
        wc.record(type("DR", (), {
            "decision": Decision.APPROVE,
            "factors": [
                type("F", (), {"name": "kpi:quality", "value": 0.9, "weight": 0.25})(),
            ],
        })())
    cal = wc.calibrate()
    assert len(cal) > 0
    assert "kpi:quality" in cal


def test_weight_calibrator_adjusts_weight() -> None:
    wc = WeightCalibrator(learning_rate=0.2)

    for _ in range(5):
        wc.record(type("DR", (), {
            "decision": Decision.REJECT,
            "factors": [
                type("F", (), {"name": "kpi:accurate", "value": 0.1, "weight": 0.25})(),
            ],
        })())
    cal = wc.calibrate()
    assert "kpi:accurate" in cal
    assert cal["kpi:accurate"] > 0.25

    wc2 = WeightCalibrator(learning_rate=0.2)
    for _ in range(5):
        wc2.record(type("DR", (), {
            "decision": Decision.REJECT,
            "factors": [
                type("F", (), {"name": "kpi:misleading", "value": 0.9, "weight": 0.25})(),
            ],
        })())
    cal2 = wc2.calibrate()
    assert "kpi:misleading" in cal2
    assert cal2["kpi:misleading"] < 0.25


def test_weight_calibrator_factor_accuracy() -> None:
    wc = WeightCalibrator()
    wc.record(type("DR", (), {
        "decision": Decision.APPROVE,
        "factors": [
            type("F", (), {"name": "kpi:good", "value": 0.9, "weight": 0.25})(),
        ],
    })())
    wc.record(type("DR", (), {
        "decision": Decision.REJECT,
        "factors": [
            type("F", (), {"name": "kpi:good", "value": 0.2, "weight": 0.25})(),
        ],
    })())
    acc = wc.factor_accuracy("kpi:good")
    assert acc == 1.0


def test_weight_calibrator_summary() -> None:
    wc = WeightCalibrator()
    wc.record(type("DR", (), {
        "decision": Decision.APPROVE,
        "factors": [
            type("F", (), {"name": "kpi:a", "value": 0.9, "weight": 0.25})(),
            type("F", (), {"name": "risk:b", "value": 0.8, "weight": 0.25})(),
        ],
    })())
    s = wc.summary()
    assert s["total_decisions"] == 1
    assert s["factor_count"] == 2


# ============================================================
# BORS: PENDING_EVIDENCE Decision Tests
# ============================================================

def test_decision_pending_evidence() -> None:
    engine = DecisionEngine()
    risks = [
        type("Risk", (), {"name": "evidence_risk", "risk_type": "evidence_risk",
                          "score": 0.9})(),
    ]
    record = engine.decide("publish", risks=risks)
    assert record.decision == Decision.PENDING_EVIDENCE
    assert "Evidence gap" in record.reason


def test_decision_approve_when_evidence_ok() -> None:
    engine = DecisionEngine()
    kpis = [type("KPI", (), {"name": "quality", "value": 0.95})()]
    risks = [
        type("Risk", (), {"name": "evidence_risk", "risk_type": "evidence_risk",
                          "score": 0.1})(),
    ]
    record = engine.decide("publish", kpis=kpis, risks=risks)
    assert record.decision in (Decision.APPROVE, Decision.REVIEW)


def test_decision_certify_still_works() -> None:
    engine = DecisionEngine()
    kpis = [type("KPI", (), {"name": "all_good", "value": 1.0})()]
    entities = [
        type("Entity", (), {"entity_type": "report", "value": 1.0})(),
    ]
    record = engine.decide("certify", kpis=kpis, entities=entities)
    assert record.decision == Decision.APPROVE


def test_decision_pending_evidence_not_triggered_on_low_risk() -> None:
    engine = DecisionEngine()
    kpis = [type("KPI", (), {"name": "quality", "value": 0.9})()]
    risks = [
        type("Risk", (), {"name": "evidence_risk", "risk_type": "evidence_risk",
                          "score": 0.2})(),
    ]
    record = engine.decide("publish", kpis=kpis, risks=risks)
    assert record.decision != Decision.PENDING_EVIDENCE


# ============================================================
# Cross-Layer End-to-End Pipeline Test
# ============================================================

def test_pipeline_full_rf_simulation() -> None:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path("data/domain/rf_simulation/domain.yaml")),
        runtime_state={
            "qa_gate": {"passed": 5, "total": 5, "confidence": 0.95},
            "evidence": {"chain_intact": True, "confidence": 1.0},
        },
    )
    assert result["load"]["validation_passed"]
    assert result["load"]["domain"] == "RF Simulation"
    assert result["oosk"]["entities_mapped"] >= 1
    assert result["oosk"]["relations_mapped"] >= 1
    assert result["constraints"]["total"] > 0
    assert result["bors"]["kpi_count"] >= 1
    assert result["bors"]["risk_count"] >= 1
    assert result["bors"]["decision"] in ("approve", "review", "reject", "pending_evidence", "defer", "certify")
    assert result["bors"]["reason"] != ""


def test_pipeline_full_gw2_progress() -> None:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path("data/domain/gw2_player_progress/domain.yaml")),
        runtime_state={
            "qa_gate": {"passed": 3, "total": 4, "confidence": 0.8},
            "compliance": {"passed": 2, "total": 2, "failures": []},
            "evidence": {"chain_intact": True},
            "action_history": {"total": 50, "failed": 3},
        },
    )
    assert result["load"]["validation_passed"]
    assert result["load"]["domain"] == "GW2 Player Progress"
    assert result["oosk"]["entities_mapped"] >= 4
    assert result["bors"]["kpi_count"] >= 3
    assert result["bors"]["risk_count"] >= 1


def test_pipeline_incremental_steps() -> None:
    pipeline = ThreeLayerPipeline()
    load = pipeline.load_domain(str(Path("data/domain/rf_simulation/domain.yaml")))
    assert load["validation_passed"]

    oosk = pipeline.map_to_oosk()
    assert oosk["entities_mapped"] > 0

    constraints = pipeline.evaluate_constraints()
    assert constraints["total"] > 0

    bors = pipeline.decide({
        "qa_gate": {"passed": 5, "total": 5},
        "evidence": {"chain_intact": True},
    })
    assert bors["decision"] in ("approve", "review", "reject", "pending_evidence", "defer", "certify")
    assert bors["report"]["decisions"][0]["reason"] != ""


def test_pipeline_loaded_domain_keys() -> None:
    pipeline = ThreeLayerPipeline()
    load = pipeline.load_domain(str(Path("data/domain/rf_simulation/domain.yaml")))
    assert load["entity_count"] >= 6
    assert load["relation_count"] >= 6
    assert load["event_count"] >= 5
    assert load["rule_count"] >= 3


def test_pipeline_with_bad_domain_shows_errors() -> None:
    from gw2radar.domain_graph.domain_schema import EdgeDef
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    dg.edges["ghost_edge"] = EdgeDef(
        type="ghost_edge",
        source_types=["GhostType"],
        target_types=["AlsoGhost"],
    )
    errors = engine.validate(dg)
    assert len(errors) >= 2
    assert any("GhostType" in e for e in errors)


def test_pipeline_decision_reason_contains_score() -> None:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path("data/domain/rf_simulation/domain.yaml")),
        runtime_state={"qa_gate": {"passed": 1, "total": 5, "failures": ["f1", "f2"]}},
    )
    assert "score" in result["bors"]["reason"].lower() or result["bors"]["decision"] != "approve"


# ============================================================
# Cross-Layer: Manual pipeline (no pipeline helper)
# ============================================================

def test_manual_three_layer_integration() -> None:
    dg_engine = DomainGraphEngine()
    dg = dg_engine.load_file(str(Path("data/domain/rf_simulation/domain.yaml")))
    assert dg_engine.validate(dg) == []

    store = RuntimeStore()
    mapper = RuntimeMapper()
    mapper.map_domain_to_store(dg, store)
    assert len(store.graph.entities) >= 1

    compiler = BORSCompiler()
    entities = list(store.graph.entities.values())
    bors_entities = compiler.compile_all(entities)
    assert any(e is not None for e in bors_entities)

    from gw2radar.bors.business_kpi import BusinessKPICalculator
    kpis = BusinessKPICalculator().calculate_all(
        qa_gate={"passed": 5, "total": 5},
        evidence={"chain_intact": True},
    )
    assert len(kpis) >= 2

    risks = BusinessRiskModel().assess_all(
        qa_gate={"passed": 5, "total": 5},
        evidence={"chain_intact": True},
    )
    decision = DecisionEngine().decide(
        "integration_test", kpis=kpis, risks=risks, entities=bors_entities,
    )
    assert decision.decision in (Decision.APPROVE, Decision.REVIEW, Decision.REJECT)
    assert decision.reason != ""
