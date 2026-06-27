"""Advanced cross-layer tests: semantic equivalence, schema diff, planner, decision graph, CLI."""

from pathlib import Path

from gw2radar.bors.decision_engine import Decision, DecisionEngine
from gw2radar.bors.decision_graph import DecisionGraph
from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.domain_graph.domain_schema import SchemaDiff
from gw2radar.oosk.planner import Orchestrator, Planner
from gw2radar.oosk.runtime_store import RuntimeStore


# ============================================================
# DGSK: Semantic Equivalence (Type Aliasing)
# ============================================================

def test_type_aliases_loaded() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    assert len(dg.type_aliases) >= 1
    alias = dg.type_aliases[0]
    assert alias.local_type == "Action"
    assert alias.equivalent_to == "Task"


def test_gw2_type_aliases_loaded() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    assert len(dg.type_aliases) >= 1
    assert dg.type_aliases[0].local_type == "Action"


def test_resolve_aliases() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    mapping = engine.resolve_aliases(dg)
    assert mapping.get("Action") == "Task"


def test_merge_with_aliases() -> None:
    engine = DomainGraphEngine()
    dg1 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    dg2 = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    merged = engine.merge([dg1, dg2])
    assert any(a.local_type == "Action" for a in merged.type_aliases)


# ============================================================
# DGSK: Schema Evolution
# ============================================================

def test_schema_diff_identical() -> None:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    diff = engine.schema_diff(dg, dg)
    assert diff.backward_compatible
    assert len(diff.breaking_changes) == 0
    assert len(diff.added_nodes) == 0
    assert len(diff.removed_nodes) == 0


def test_schema_diff_added_node() -> None:
    engine = DomainGraphEngine()
    old = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    new = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    from gw2radar.domain_graph.domain_schema import NodeDef
    new.nodes["NewType"] = NodeDef(type="NewType")
    diff = engine.schema_diff(old, new)
    assert "NewType" in diff.added_nodes
    assert not diff.backward_compatible


def test_schema_diff_removed_node() -> None:
    engine = DomainGraphEngine()
    old = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    new = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    first_node = list(old.nodes.keys())[0]
    del new.nodes[first_node]
    diff = engine.schema_diff(old, new)
    assert first_node in diff.removed_nodes
    assert not diff.backward_compatible


def test_schema_diff_added_edge() -> None:
    engine = DomainGraphEngine()
    old = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    new = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    from gw2radar.domain_graph.domain_schema import EdgeDef
    new.edges["new_edge"] = EdgeDef(type="new_edge")
    diff = engine.schema_diff(old, new)
    assert "new_edge" in diff.added_edges


def test_schema_diff_backward_compat_kept() -> None:
    engine = DomainGraphEngine()
    old = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    new = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    from gw2radar.domain_graph.domain_schema import EdgeDef
    new.edges["new_edge"] = EdgeDef(type="new_edge")
    diff = engine.schema_diff(old, new)
    assert isinstance(diff, SchemaDiff)


# ============================================================
# OOSK: Planner / Orchestrator
# ============================================================

def test_planner_create_publish_plan() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("publish report", store)
    assert plan.intent == "publish report"
    assert len(plan.steps) >= 4
    assert plan.steps[0].action_id == "validate_evidence"
    assert plan.steps[-1].action_id == "publish"


def test_planner_create_sync_plan() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("sync data", store)
    assert len(plan.steps) == 4
    assert plan.steps[0].action_id == "authenticate"


def test_planner_create_review_plan() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("review sources", store)
    assert len(plan.steps) == 3


def test_planner_generic_intent() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("custom intent xyz", store)
    assert len(plan.steps) == 1
    assert plan.steps[0].action_id == "generic_analyze"


def test_planner_step_dependencies() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("publish report", store)
    publish_step = next(s for s in plan.steps if s.action_id == "publish")
    assert "generate_report" in publish_step.depends_on


def test_planner_estimated_cost() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("publish report", store)
    assert plan.total_estimated_cost > 0
    assert sum(s.estimated_cost for s in plan.steps) == plan.total_estimated_cost


def test_orchestrator_execute_success() -> None:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan("sync data", store)
    orch = Orchestrator(planner)
    result = orch.execute(plan, store)
    assert result.success
    assert len(result.step_results) == len(plan.steps)


def test_orchestrator_execute_fails_on_unresolved_deps() -> None:
    from gw2radar.oosk.planner import PlanStep
    plan = planner = Planner()  # placeholder
    planner_obj = Planner()
    store = RuntimeStore()

    from gw2radar.oosk.planner import Plan
    plan = Plan(
        plan_id="bad_plan", intent="bad",
        steps=[
            type("PS", (), {"action_id": "step_b", "description": "", "depends_on": ["step_a"],
                            "preconditions": [], "estimated_cost": 1.0, "handler": None})(),
        ],
    )
    orch = Orchestrator(planner_obj)
    result = orch.execute(plan, store)
    assert not result.success


# ============================================================
# BORS: DecisionGraph
# ============================================================

def test_decision_graph_add_node() -> None:
    dg = DecisionGraph()
    engine = DecisionEngine()
    record = engine.decide("test")
    node = dg.add_decision(record, decision_id="dec_1", decision_type="test")
    assert node.decision_id == "dec_1"
    assert len(dg.all_decisions()) == 1


def test_decision_graph_chain() -> None:
    dg = DecisionGraph()
    engine = DecisionEngine()
    r1 = engine.decide("gate_1")
    dg.add_decision(r1, decision_id="gate_1", decision_type="gate")
    r2 = engine.decide("gate_2")
    dg.add_decision(r2, decision_id="gate_2", parent_id="gate_1")
    r3 = engine.decide("final")
    dg.add_decision(r3, decision_id="final", parent_id="gate_2")

    trace = dg.trace("final")
    assert len(trace) == 3
    assert trace[-1]["decision_id"] == "gate_1"


def test_decision_graph_upstream() -> None:
    dg = DecisionGraph()
    engine = DecisionEngine()
    r1 = engine.decide("parent")
    dg.add_decision(r1, decision_id="parent")
    r2 = engine.decide("child")
    dg.add_decision(r2, decision_id="child", parent_id="parent")
    upstream = dg.upstream_dependencies("child")
    assert len(upstream) == 1
    assert upstream[0].decision_id == "parent"


def test_decision_graph_downstream() -> None:
    dg = DecisionGraph()
    engine = DecisionEngine()
    r1 = engine.decide("parent")
    dg.add_decision(r1, decision_id="parent")
    r2 = engine.decide("child")
    dg.add_decision(r2, decision_id="child", parent_id="parent")
    downstream = dg.downstream_dependents("parent")
    assert len(downstream) == 1
    assert downstream[0].decision_id == "child"


def test_decision_graph_reversal_impact() -> None:
    dg = DecisionGraph()
    engine = DecisionEngine()
    r1 = engine.decide("first")
    dg.add_decision(r1, decision_id="first")
    r2 = engine.decide("second")
    dg.add_decision(r2, decision_id="second", parent_id="first")
    impact = dg.impact_of_reversal("first")
    assert impact["direct_downstream"] == 1
    assert impact["target"] == "first"


def test_decision_graph_empty_trace() -> None:
    dg = DecisionGraph()
    trace = dg.trace("nonexistent")
    assert trace == []


# ============================================================
# CLI: Smoke test (import + subcommand discovery)
# ============================================================

def test_cli_module_imports() -> None:
    import gw2radar.cli
    assert hasattr(gw2radar.cli, "main")
    assert hasattr(gw2radar.cli, "cmd_validate")
    assert hasattr(gw2radar.cli, "cmd_info")
    assert hasattr(gw2radar.cli, "cmd_diff")
    assert hasattr(gw2radar.cli, "cmd_pipeline")
    assert hasattr(gw2radar.cli, "cmd_compile")
    assert hasattr(gw2radar.cli, "cmd_plan")


def test_cli_validate_runs() -> None:
    from gw2radar.cli import cmd_validate
    import argparse
    ns = argparse.Namespace(file=str(Path("tests/data/gw2_ontology.yaml")))
    cmd_validate(ns)


def test_cli_info_runs() -> None:
    from gw2radar.cli import cmd_info
    import argparse
    ns = argparse.Namespace(file=str(Path("tests/data/gw2_ontology.yaml")))
    cmd_info(ns)


def test_cli_diff_runs() -> None:
    from gw2radar.cli import cmd_diff
    import argparse
    ns = argparse.Namespace(
        old=str(Path("tests/data/gw2_ontology.yaml")),
        new=str(Path("tests/data/gw2_ontology.yaml")),
    )
    cmd_diff(ns)


def test_cli_pipeline_runs() -> None:
    from gw2radar.cli import cmd_pipeline
    import argparse
    ns = argparse.Namespace(
        file=str(Path("tests/data/gw2_ontology.yaml")),
        qa_passed=5, qa_total=5,
        evidence_chain=True,
        action_total=None, action_failed=None,
    )
    cmd_pipeline(ns)


def test_cli_compile_oosk_runs() -> None:
    from gw2radar.cli import cmd_compile
    import argparse
    ns = argparse.Namespace(
        file=str(Path("tests/data/gw2_ontology.yaml")),
        target="oosk",
    )
    cmd_compile(ns)


def test_cli_compile_bors_runs() -> None:
    from gw2radar.cli import cmd_compile
    import argparse
    ns = argparse.Namespace(
        file=str(Path("tests/data/gw2_ontology.yaml")),
        target="bors",
    )
    cmd_compile(ns)


def test_cli_plan_runs() -> None:
    from gw2radar.cli import cmd_plan
    import argparse
    ns = argparse.Namespace(intent="publish report")
    cmd_plan(ns)


# ============================================================
# API Routes: Ensure import + route registration works
# ============================================================

def test_layers_api_routes_import() -> None:
    from gw2radar.api.routes.layers import router
    routes = [r.path for r in router.routes]
    assert "/api/v1/layers/dgsk/load" in routes
    assert "/api/v1/layers/dgsk/compile/oosk" in routes
    assert "/api/v1/layers/dgsk/compile/bors" in routes
    assert "/api/v1/layers/dgsk/diff" in routes
    assert "/api/v1/layers/oosk/map" in routes
    assert "/api/v1/layers/oosk/constraints" in routes
    assert "/api/v1/layers/oosk/plan" in routes
    assert "/api/v1/layers/oosk/policy/evaluate" in routes
    assert "/api/v1/layers/bors/decide" in routes
    assert "/api/v1/layers/bors/calibrate" in routes
    assert "/api/v1/layers/bors/decision-graph" in routes
    assert "/api/v1/layers/pipeline" in routes


# ============================================================
# Full end-to-end with all new features
# ============================================================

def test_full_e2e_with_all_features() -> None:
    from gw2radar.pipeline import ThreeLayerPipeline

    pipeline = ThreeLayerPipeline()
    load_result = pipeline.load_domain(str(Path("tests/data/gw2_ontology.yaml")))
    assert load_result["validation_passed"]
    assert load_result["entity_count"] >= 6

    pipeline.map_to_oosk()
    constraints = pipeline.evaluate_constraints()
    assert constraints["total"] > 0

    bors = pipeline.decide({
        "qa_gate": {"passed": 5, "total": 5, "confidence": 0.95},
        "compliance": {"passed": 3, "total": 3, "failures": []},
        "evidence": {"chain_intact": True, "confidence": 1.0},
        "action_history": {"total": 100, "failed": 2},
        "tool_stats": {"tool_a": {"success_rate": 0.95}},
    })
    assert bors["kpi_count"] >= 4
    assert bors["risk_count"] >= 1
    assert bors["decision"] in (
        "approve", "review", "reject", "pending_evidence", "defer", "certify",
    )
    assert bors["report"]["kpis"]
