from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.oosk.constraint_engine import ConstraintEngine
from gw2radar.oosk.evidence_binder import EvidenceBinder
from gw2radar.oosk.evolution_engine import EvolutionEngine
from gw2radar.oosk.memory_graph import EpisodicMemory, MemoryGraph, ToolMemory
from gw2radar.oosk.policy_engine import PolicyDef, PolicyEngine
from gw2radar.oosk.runtime_mapper import RuntimeMapper
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.oosk.tool_registry import AgentToolLayer, ToolGraph, ToolRegistry
from gw2radar.ontology.schemas import Entity, Evidence, FreshnessStatus, QAStatus, Relation


def _make_store() -> RuntimeStore:
    graph = build_mock_graph()
    return RuntimeStore(graph)


def test_runtime_store_add_get_entity() -> None:
    store = _make_store()
    entity = store.get_entity("mock:account:lee")
    assert entity is not None
    assert entity.canonical_name == "Mock Account Lee"


def test_runtime_store_search() -> None:
    store = _make_store()
    results = store.search("legendary")
    assert isinstance(results, list)


def test_runtime_store_trace() -> None:
    store = _make_store()
    trace_result = store.trace("mock:goal:legendary:001", depth=2)
    assert trace_result["entity_id"] == "mock:goal:legendary:001"
    assert isinstance(trace_result["relations"], list)


def test_runtime_store_get_neighbors() -> None:
    store = _make_store()
    neighbors = store.get_neighbors("mock:account:00001")
    assert isinstance(neighbors, list)


def test_runtime_mapper() -> None:
    from gw2radar.domain_graph.domain_engine import DomainGraphEngine
    from pathlib import Path

    store = RuntimeStore()
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path("tests/data/gw2_ontology.yaml")))
    mapper = RuntimeMapper()
    mapper.map_domain_to_store(dg, store)
    assert store.get_entity("dg:Evidence") is not None
    assert store.get_entity("dg:Scene") is None


def test_runtime_mapper_extract_state() -> None:
    store = _make_store()
    mapper = RuntimeMapper()
    state = mapper.extract_runtime_state(store.graph)
    assert "entities" in state
    assert "relations" in state
    assert "evidence" in state


def test_constraint_engine_l1() -> None:
    store = _make_store()
    engine = ConstraintEngine()
    results = engine.evaluate(store.graph)
    l1 = [r for r in results if r.layer == "L1_STATIC"]
    assert len(l1) >= 1


def test_constraint_engine_l2() -> None:
    store = _make_store()
    engine = ConstraintEngine()
    results = engine.evaluate(store.graph)
    l2 = [r for r in results if r.layer == "L2_RUNTIME"]
    assert len(l2) >= 2


def test_constraint_engine_l3() -> None:
    from gw2radar.ontology.entity_types import EntityType
    store = _make_store()

    orphan_goal = Entity(
        id="goal:orphan", type=EntityType.GOAL,
        canonical_name="orphan_goal",
    )
    store.add_entity(orphan_goal)

    engine = ConstraintEngine()
    results = engine.evaluate(store.graph)
    l3 = [r for r in results if r.layer == "L3_GOVERNANCE"]
    assert len(l3) >= 1


def test_constraint_engine_summary() -> None:
    store = _make_store()
    engine = ConstraintEngine()
    results = engine.evaluate(store.graph)
    summary = engine.summary(results)
    assert summary["total"] > 0
    assert summary["by_layer"]["L1_STATIC"]["total"] >= 1


def test_tool_registry_register_and_execute() -> None:
    reg = ToolRegistry()

    def mock_handler(**kwargs: object) -> dict:
        return {"result": "ok", "args": dict(kwargs)}

    reg.register("test_tool", mock_handler, input_schema={"x": "str"})
    result = reg.execute("test_tool", {"x": "hello"})
    assert result["result"] == "ok"


def test_tool_graph_dependency() -> None:
    tg = ToolGraph()
    tg.add_dependency("A", "B")
    tg.add_dependency("B", "C")
    impact = tg.analyze_impact("C")
    assert "B" in impact["downstream_dependents"]
    assert "A" in impact["downstream_dependents"]


def test_agent_tool_layer_forbidden() -> None:
    reg = ToolRegistry()

    def mock_handler(**kwargs: object) -> dict:
        return {"result": "ok"}

    reg.register("dangerous", mock_handler)
    layer = AgentToolLayer(reg)
    layer.forbid_operation("dangerous")
    result = layer.call("dangerous", {})
    assert "error" in result


def test_policy_engine() -> None:
    engine = PolicyEngine()
    engine.add(PolicyDef(
        name="always_pass", severity="info",
        check_fn=lambda ctx: True, enabled=True,
    ))
    engine.add(PolicyDef(
        name="always_fail", severity="error",
        check_fn=lambda ctx: False, enabled=True,
    ))
    engine.add(PolicyDef(
        name="disabled_pol", severity="warn",
        check_fn=lambda ctx: False, enabled=False,
    ))
    results = engine.evaluate({})
    assert len(results) == 2
    assert results[0].passed
    assert not results[1].passed


def test_memory_graph_ttl() -> None:
    mg = MemoryGraph()
    mg.store("key1", "value1")
    mg.store("expires_soon", "temp", ttl=0.001)
    assert mg.get("key1") == "value1"
    import time; time.sleep(0.01)
    assert mg.get("expires_soon") is None


def test_tool_memory() -> None:
    tm = ToolMemory()
    tm.record("tool_a", True, 100.0)
    tm.record("tool_a", False, 200.0)
    tm.record("tool_b", True, 50.0)
    assert tm.success_rate("tool_a") == 0.5
    assert tm.avg_duration("tool_a") == 150.0
    assert tm.success_rate("tool_b") == 1.0
    stats = tm.stats()
    assert "tool_a" in stats
    assert stats["tool_a"]["total"] == 2


def test_tool_memory_no_calls() -> None:
    tm = ToolMemory()
    assert tm.success_rate("nonexistent") == 0.0
    assert tm.avg_duration("nonexistent") == 0.0


def test_episodic_memory_patterns() -> None:
    em = EpisodicMemory()
    for _ in range(10):
        em.record("agent1", "action_x", True)
    for _ in range(3):
        em.record("agent1", "action_y", False)
    patterns = em.detect_patterns(window=13)
    assert len(patterns) >= 2


def test_evolution_engine_low_success() -> None:
    ee = EvolutionEngine()
    snapshot = {
        "tool_stats": {"problematic_tool": {"success_rate": 0.1}},
        "action_history": [],
    }
    proposals = ee.evolve(snapshot)
    assert any(p.proposal_type == "tool_repair" for p in proposals)
    assert any("problematic_tool" in p.description for p in proposals)


def test_evolution_engine_frequent_action() -> None:
    ee = EvolutionEngine()
    snapshot = {
        "tool_stats": {},
        "action_history": [{"action_type": "frequent_action"} for _ in range(10)],
    }
    proposals = ee.evolve(snapshot)
    assert any(p.proposal_type == "index_suggestion" for p in proposals)


def test_evidence_binder_chain() -> None:
    binder = EvidenceBinder()
    chain_hash = binder.create_chain(["ev-001", "ev-002"], "prev_hash")
    result = binder.verify_chain("chain-1", ["ev-001", "ev-002"], chain_hash, "prev_hash")
    assert result.chain_intact
    assert result.total_links == 2


def test_evidence_binder_broken() -> None:
    binder = EvidenceBinder()
    chain_hash = binder.create_chain(["ev-001", "ev-002"])
    result = binder.verify_chain("chain-1", ["ev-001", "ev-003"], chain_hash)
    assert not result.chain_intact


def test_evidence_binder_sign() -> None:
    binder = EvidenceBinder()
    sig = binder.sign_evidence({"key": "value", "num": 42})
    assert isinstance(sig, str)
    assert len(sig) == 64
