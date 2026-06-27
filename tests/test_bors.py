from gw2radar.bors.bors_compiler import BORSCompiler
from gw2radar.bors.bors_dashboard import BORSDashboard
from gw2radar.bors.bors_report import BORSReportGenerator
from gw2radar.bors.bors_simulator import BORSSimulator, SimulationScenario
from gw2radar.bors.business_entity import BusinessEntityType, entity_factory
from gw2radar.bors.business_kpi import BusinessKPICalculator, BusinessKPIType
from gw2radar.bors.business_risk import BusinessRiskModel, BusinessRiskType, RiskLevel
from gw2radar.bors.decision_engine import Decision, DecisionEngine
from gw2radar.bors.value_graph import ValueGraph


def test_entity_factory() -> None:
    entity = entity_factory(BusinessEntityType.QUALITY_SCORE, "src:qa", value=0.95)
    assert entity.entity_type == BusinessEntityType.QUALITY_SCORE
    assert entity.value == 0.95
    assert entity.source_id == "src:qa"


def test_kpi_calculator_qa() -> None:
    calc = BusinessKPICalculator()
    kpis = calc.calculate_all(
        qa_gate={"passed": 4, "total": 5, "confidence": 0.9},
    )
    quality_kpis = [k for k in kpis if k.kpi_type == BusinessKPIType.QUALITY]
    assert len(quality_kpis) >= 1
    assert quality_kpis[0].value == 0.8


def test_kpi_calculator_all_sources() -> None:
    calc = BusinessKPICalculator()
    kpis = calc.calculate_all(
        qa_gate={"passed": 5, "total": 5, "confidence": 0.9},
        compliance={"passed": 3, "total": 3, "confidence": 0.85},
        evidence={"chain_intact": True, "confidence": 1.0},
        action_history={"total": 100, "failed": 5},
        tool_stats={"tool_a": {"success_rate": 0.95}, "tool_b": {"success_rate": 0.85}},
    )
    assert len(kpis) == 5
    assert all(0.0 <= k.value <= 1.0 for k in kpis)


def test_risk_model_qa_pass() -> None:
    model = BusinessRiskModel()
    risks = model.assess_all(qa_gate={"passed": 5, "total": 5})
    quality = [r for r in risks if r.risk_type == BusinessRiskType.QUALITY]
    assert len(quality) >= 1
    assert quality[0].level == RiskLevel.NONE


def test_risk_model_qa_fail() -> None:
    model = BusinessRiskModel()
    risks = model.assess_all(qa_gate={"passed": 1, "total": 5, "failures": ["check1", "check2"]})
    quality = [r for r in risks if r.risk_type == BusinessRiskType.QUALITY]
    assert quality[0].level in (RiskLevel.HIGH, RiskLevel.MEDIUM)


def test_risk_model_evidence_broken() -> None:
    model = BusinessRiskModel()
    risks = model.assess_all(evidence={"chain_intact": False})
    evidence_risks = [r for r in risks if r.risk_type == BusinessRiskType.EVIDENCE]
    assert len(evidence_risks) >= 1
    assert evidence_risks[0].level == RiskLevel.CRITICAL


def test_risk_model_all_sources() -> None:
    model = BusinessRiskModel()
    risks = model.assess_all(
        qa_gate={"passed": 3, "total": 5, "failures": ["f1"]},
        compliance={"failures": ["violation1"]},
        evidence={"chain_intact": False},
        action_history={"total": 10, "failed": 6},
    )
    assert len(risks) >= 4


def test_decision_approve() -> None:
    engine = DecisionEngine(threshold=0.6)
    record = engine.decide("publish_report")
    assert record.decision in (Decision.APPROVE, Decision.REJECT, Decision.DEFER)


def test_decision_with_kpis_and_risks() -> None:
    engine = DecisionEngine(threshold=0.6)
    kpis = [
        type("KPI", (), {"name": "quality", "value": 0.95})(),
        type("KPI", (), {"name": "compliance", "value": 0.90})(),
    ]
    risks = [
        type("Risk", (), {"name": "quality_risk", "score": 0.1})(),
    ]
    record = engine.decide("publish_report", kpis=kpis, risks=risks)
    assert record.score > 0
    assert record.reason


def test_decision_reason_is_present() -> None:
    engine = DecisionEngine(threshold=0.6)
    record = engine.decide("test")
    assert record.reason != ""
    assert "score" in record.reason


def test_decision_all_factors_recorded() -> None:
    engine = DecisionEngine()
    kpis = [type("KPI", (), {"name": "k1", "value": 0.5})()]
    risks = [type("Risk", (), {"name": "r1", "score": 0.8})()]
    record = engine.decide("test", kpis=kpis, risks=risks)
    assert len(record.factors) == 2
    assert any("kpi:k1" in f.name for f in record.factors)
    assert any("risk:r1" in f.name for f in record.factors)


def test_value_graph_build() -> None:
    vg = ValueGraph()
    entities = [entity_factory(BusinessEntityType.QUALITY_SCORE, "src:qa", value=0.95)]
    kpis = [
        type("KPI", (), {"name": "quality", "value": 0.95, "kpi_type": "quality"})(),
    ]
    risks = [
        type("Risk", (), {"name": "qa_risk", "score": 0.1, "risk_type": "quality_risk"})(),
    ]
    vg.build(entities=entities, kpis=kpis, risks=risks)
    paths = vg.propagate("entity:src:qa", depth=2)
    assert isinstance(paths, list)


def test_value_graph_impact_analysis() -> None:
    vg = ValueGraph()
    vg.build()
    vg.add_node(type("Node", (), {"node_id": "A", "node_type": "entity", "value": 1.0})())
    vg.add_node(type("Node", (), {"node_id": "B", "node_type": "kpi", "value": 0.5})())
    vg.add_edge(type("Edge", (), {"source_id": "A", "target_id": "B", "weight": 0.8, "label": "affects"})())
    impact = vg.impact_analysis("A")
    assert impact["impact_count"] >= 1


def test_bors_compiler_known_type() -> None:
    compiler = BORSCompiler()
    entity = type("OOSKEntity", (), {"id": "run-001", "type": type("T", (), {"value": "ExecutionRun"})()})()
    result = compiler.compile_one(entity)
    assert result is not None
    assert result.entity_type == BusinessEntityType.SIMULATION_COST


def test_bors_compiler_unknown_type() -> None:
    compiler = BORSCompiler()
    entity = type("OOSKEntity", (), {"id": "x-001", "type": type("T", (), {"value": "UnknownType"})()})()
    result = compiler.compile_one(entity)
    assert result is None


def test_bors_compiler_all() -> None:
    compiler = BORSCompiler()
    entities = [
        type("E", (), {"id": "r1", "type": type("T", (), {"value": "ExecutionRun"})()}),
        type("E", (), {"id": "ev1", "type": type("T", (), {"value": "Evidence"})()}),
        type("E", (), {"id": "rp1", "type": type("T", (), {"value": "Report"})()}),
    ]
    results = compiler.compile_all(entities)
    assert len(results) == 3


def test_simulator_basic() -> None:
    sim = BORSSimulator()
    good = SimulationScenario(
        name="good_scenario",
        qa_gate_result={"passed": 5, "total": 5},
        evidence_chain_intact=True,
    )
    result = sim.simulate(good)
    assert len(result.kpis) >= 1
    assert len(result.decisions) >= 1
    assert result.name == "good_scenario"


def test_simulator_bad_scenario() -> None:
    sim = BORSSimulator()
    bad = SimulationScenario(
        name="bad_scenario",
        qa_gate_result={"passed": 1, "total": 5, "failures": ["f1", "f2"]},
        compliance_report={"failures": ["violation"]},
        evidence_chain_intact=False,
        action_total=10,
        action_failed=7,
    )
    result = sim.simulate(bad)
    risks = result.risks
    assert any(r.level in (RiskLevel.HIGH, RiskLevel.CRITICAL) for r in risks)


def test_simulator_compare() -> None:
    sim = BORSSimulator()
    good = SimulationScenario(name="good", qa_gate_result={"passed": 5, "total": 5})
    bad = SimulationScenario(name="bad", qa_gate_result={"passed": 1, "total": 5})
    comparison = sim.compare([good, bad])
    assert len(comparison) == 2
    assert comparison[0]["scenario"] == "good"
    assert comparison[1]["scenario"] == "bad"


def test_report_generator() -> None:
    gen = BORSReportGenerator()
    kpis = [type("KPI", (), {"name": "q", "value": 0.9, "confidence": 1.0, "unit": "score", "trend": "stable"})()]
    risks = [type("Risk", (), {"name": "qa_risk", "level": RiskLevel.LOW, "score": 0.1, "confidence": 1.0, "mitigation": ""})()]
    decisions = [type("Dec", (), {"decision": Decision.APPROVE, "score": 0.9, "confidence": 1.0, "reason": "ok"})()]
    report = gen.generate(kpis, risks, decisions)
    data = report.to_dict()
    assert "kpis" in data
    assert "risks" in data
    assert "decisions" in data
    html = report.to_html()
    assert "<html>" in html
    assert "BORS Report" in html


def test_dashboard_snapshot() -> None:
    dash = BORSDashboard()
    kpis = [type("KPI", (), {"name": "q", "value": 0.9, "trend": "stable"})()]
    risks = [type("Risk", (), {"name": "critical_risk", "level": RiskLevel.CRITICAL, "score": 0.9})()]
    decisions = [type("Dec", (), {"decision": Decision.APPROVE, "score": 0.9, "reason": "ok"})()]
    snap = dash.snapshot(kpis, risks, decisions)
    assert snap["kpi_count"] == 1
    assert snap["risk_count"] == 1
    assert len(snap["critical_risks"]) == 1
    assert snap["critical_risks"][0]["level"] == "critical"
