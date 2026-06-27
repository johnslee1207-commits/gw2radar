"""FastAPI routes for DGSK / OOSK / BORS three-layer ontology."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.bors.bors_compiler import BORSCompiler
from gw2radar.bors.business_kpi import BusinessKPICalculator
from gw2radar.bors.business_risk import BusinessRiskModel
from gw2radar.bors.decision_engine import DecisionEngine
from gw2radar.bors.decision_graph import DecisionGraph
from gw2radar.bors.value_graph import ValueGraph
from gw2radar.bors.weight_calibrator import WeightCalibrator
from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.oosk.constraint_engine import ConstraintEngine
from gw2radar.oosk.planner import Orchestrator, Planner
from gw2radar.oosk.policy_engine import PolicyDef, PolicyEngine
from gw2radar.oosk.runtime_mapper import RuntimeMapper
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.pipeline import ThreeLayerPipeline

router = APIRouter(prefix="/api/v1/layers", tags=["layers"])


@router.post("/dgsk/load", response_model=ApiDataEnvelope)
def post_dgsk_load(domain_path: str = "tests/data/gw2_ontology.yaml") -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    path = str(Path(domain_path))
    try:
        dg = engine.load_file(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Domain file not found: {path}")
    errors = engine.validate(dg)
    return ApiDataEnvelope(data={
        "domain": dg.domain,
        "version": dg.version,
        "nodes": len(dg.nodes),
        "edges": len(dg.edges),
        "events": len(dg.events),
        "rules": len(dg.rules),
        "valid": len(errors) == 0,
        "validation_errors": errors,
    })


@router.post("/dgsk/compile/oosk", response_model=ApiDataEnvelope)
def post_dgsk_compile_oosk(domain_path: str = "tests/data/gw2_ontology.yaml") -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path(domain_path)))
    registry = engine.compile_to_oosk(dg)
    return ApiDataEnvelope(data={
        "domain_types": registry.domain_types,
        "relation_types": registry.relation_types,
        "action_types": registry.action_types,
        "constraint_rules": registry.constraint_rules,
    })


@router.post("/dgsk/compile/bors", response_model=ApiDataEnvelope)
def post_dgsk_compile_bors(domain_path: str = "tests/data/gw2_ontology.yaml") -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path(domain_path)))
    mappings = engine.compile_to_bors(dg)
    return ApiDataEnvelope(data={
        "mappings": [
            {"domain_type": m.domain_type, "bors_type": m.bors_type}
            for m in mappings
        ],
    })


@router.post("/dgsk/diff", response_model=ApiDataEnvelope)
def post_dgsk_diff(old_path: str, new_path: str) -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    old = engine.load_file(str(Path(old_path)))
    new = engine.load_file(str(Path(new_path)))
    diff = engine.schema_diff(old, new)
    return ApiDataEnvelope(data={
        "backward_compatible": diff.backward_compatible,
        "breaking_changes": diff.breaking_changes,
        "added_nodes": diff.added_nodes,
        "removed_nodes": diff.removed_nodes,
        "added_edges": diff.added_edges,
        "removed_edges": diff.removed_edges,
        "changed_properties": diff.changed_properties,
    })


@router.post("/oosk/map", response_model=ApiDataEnvelope)
def post_oosk_map(domain_path: str = "tests/data/gw2_ontology.yaml") -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path(domain_path)))
    store = RuntimeStore()
    mapper = RuntimeMapper()
    mapper.map_domain_to_store(dg, store)
    state = mapper.extract_runtime_state(store.graph)
    return ApiDataEnvelope(data={
        "entity_count": len(state["entities"]),
        "relation_count": len(state["relations"]),
        "entity_ids": [e.id for e in state["entities"]],
    })


@router.post("/oosk/constraints", response_model=ApiDataEnvelope)
def post_oosk_constraints(domain_path: str = "tests/data/gw2_ontology.yaml") -> ApiDataEnvelope:
    engine = DomainGraphEngine()
    dg = engine.load_file(str(Path(domain_path)))
    store = RuntimeStore()
    mapper = RuntimeMapper()
    mapper.map_domain_to_store(dg, store)
    ce = ConstraintEngine()
    results = ce.evaluate(store.graph)
    return ApiDataEnvelope(data=ce.summary(results))


@router.post("/oosk/plan", response_model=ApiDataEnvelope)
def post_oosk_plan(intent: str) -> ApiDataEnvelope:
    store = RuntimeStore()
    planner = Planner()
    plan = planner.create_plan(intent, store)
    return ApiDataEnvelope(data={
        "plan_id": plan.plan_id,
        "intent": plan.intent,
        "steps": [
            {"action_id": s.action_id, "description": s.description,
             "depends_on": s.depends_on, "cost": s.estimated_cost}
            for s in plan.steps
        ],
        "total_cost": plan.total_estimated_cost,
    })


@router.post("/oosk/policy/evaluate", response_model=ApiDataEnvelope)
def post_oosk_policy() -> ApiDataEnvelope:
    engine = PolicyEngine()
    engine.add(PolicyDef(
        name="data_freshness", severity="error",
        check_fn=lambda ctx: ctx.get("fresh", False),
    ))
    engine.add(PolicyDef(
        name="evidence_required", severity="error",
        check_fn=lambda ctx: ctx.get("has_evidence", False),
    ))
    results = engine.evaluate({"fresh": True, "has_evidence": True})
    return ApiDataEnvelope(data={
        "results": [
            {"name": r.name, "passed": r.passed, "severity": r.severity}
            for r in results
        ],
    })


@router.post("/bors/decide", response_model=ApiDataEnvelope)
def post_bors_decide(
    qa_passed: int = 5, qa_total: int = 5,
    chain_intact: bool = True,
) -> ApiDataEnvelope:
    calc = BusinessKPICalculator()
    risk_model = BusinessRiskModel()
    engine = DecisionEngine()

    kpis = calc.calculate_all(
        qa_gate={"passed": qa_passed, "total": qa_total},
        evidence={"chain_intact": chain_intact},
    )
    risks = risk_model.assess_all(
        qa_gate={"passed": qa_passed, "total": qa_total},
        evidence={"chain_intact": chain_intact},
    )

    compiler = BORSCompiler()
    entities = compiler.compile_from_mapping({"Report": "ReportValue"})

    decision = engine.decide("api_decision", kpis=kpis, risks=risks, entities=entities)
    return ApiDataEnvelope(data={
        "decision": decision.decision.value,
        "score": decision.score,
        "confidence": decision.confidence,
        "reason": decision.reason,
        "factors": [
            {"name": f.name, "value": f.value, "weight": f.weight, "impact": f.impact}
            for f in decision.factors
        ],
    })


@router.post("/bors/calibrate", response_model=ApiDataEnvelope)
def post_bors_calibrate() -> ApiDataEnvelope:
    wc = WeightCalibrator(learning_rate=0.15)
    engine = DecisionEngine()
    for _ in range(5):
        kpis = [type("KPI", (), {"name": "q", "value": 0.9})()]
        record = engine.decide("train", kpis=kpis)
        wc.record(record)
    return ApiDataEnvelope(data=wc.summary())


@router.post("/bors/decision-graph", response_model=ApiDataEnvelope)
def post_bors_decision_graph() -> ApiDataEnvelope:
    dg = DecisionGraph()
    engine = DecisionEngine()

    kpis = [type("KPI", (), {"name": "q", "value": 0.95})()]
    r1 = engine.decide("gate_1", kpis=kpis)
    dg.add_decision(r1, decision_id="gate_1")

    r2 = engine.decide("gate_2", kpis=kpis)
    dg.add_decision(r2, decision_id="gate_2", parent_id="gate_1")

    r3 = engine.decide("publish", kpis=kpis)
    dg.add_decision(r3, decision_id="final", parent_id="gate_2")

    return ApiDataEnvelope(data={
        "nodes": [
            {"id": n.decision_id, "decision": n.decision.value, "score": n.score}
            for n in dg.all_decisions()
        ],
        "trace": dg.trace("final"),
        "reversal_impact": dg.impact_of_reversal("gate_1"),
    })


@router.post("/pipeline", response_model=ApiDataEnvelope)
def post_pipeline(
    domain_path: str = "tests/data/gw2_ontology.yaml",
) -> ApiDataEnvelope:
    pipeline = ThreeLayerPipeline()
    result = pipeline.run_full_pipeline(
        str(Path(domain_path)),
        runtime_state={
            "qa_gate": {"passed": 5, "total": 5, "confidence": 0.95},
            "evidence": {"chain_intact": True},
        },
    )
    return ApiDataEnvelope(data=result)
