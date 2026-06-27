from dataclasses import dataclass, field
from typing import Any

from gw2radar.bors.business_kpi import BusinessKPI, BusinessKPICalculator
from gw2radar.bors.business_risk import BusinessRisk, BusinessRiskModel
from gw2radar.bors.decision_engine import DecisionEngine, DecisionRecord
from gw2radar.bors.value_graph import ValueGraph


@dataclass
class SimulationScenario:
    name: str
    qa_gate_result: dict | None = None
    compliance_report: dict | None = None
    evidence_chain_intact: bool = True
    calibration_passed: bool = True
    action_total: int = 0
    action_failed: int = 0


@dataclass
class SimulationResult:
    name: str
    kpis: list[BusinessKPI] = field(default_factory=list)
    risks: list[BusinessRisk] = field(default_factory=list)
    decisions: list[DecisionRecord] = field(default_factory=list)


class BORSSimulator:
    def __init__(self) -> None:
        self._kpi_calc = BusinessKPICalculator()
        self._risk_model = BusinessRiskModel()
        self._decision_engine = DecisionEngine()

    def simulate(self, scenario: SimulationScenario) -> SimulationResult:
        sources: dict[str, Any] = {}

        if scenario.qa_gate_result is not None:
            sources["qa_gate"] = scenario.qa_gate_result
        if scenario.compliance_report is not None:
            sources["compliance"] = scenario.compliance_report
        sources["evidence"] = {"chain_intact": scenario.evidence_chain_intact}
        sources["action_history"] = {
            "total": scenario.action_total,
            "failed": scenario.action_failed,
        }

        kpis = self._kpi_calc.calculate_all(**sources)
        risks = self._risk_model.assess_all(**sources)
        decision = self._decision_engine.decide(scenario.name, kpis=kpis, risks=risks)

        return SimulationResult(
            name=scenario.name,
            kpis=kpis,
            risks=risks,
            decisions=[decision],
        )

    def compare(self, scenarios: list[SimulationScenario]) -> list[dict]:
        results: list[dict] = []
        for scenario in scenarios:
            result = self.simulate(scenario)
            for d in result.decisions:
                results.append({
                    "scenario": scenario.name,
                    "decision": d.decision.value,
                    "score": d.score,
                    "reason": d.reason,
                })
        return results
