import time
from pathlib import Path

from gw2radar.audit import AuditTrail
from gw2radar.bors.bors_compiler import BORSCompiler
from gw2radar.bors.bors_report import BORSReportGenerator
from gw2radar.bors.business_kpi import BusinessKPICalculator
from gw2radar.bors.business_risk import BusinessRiskModel
from gw2radar.bors.dashboard_trends import TrendTracker
from gw2radar.bors.decision_engine import DecisionEngine
from gw2radar.bors.value_graph import ValueGraph
from gw2radar.domain_graph.domain_engine import DomainGraphEngine
from gw2radar.oosk.action_bridge import OOSKActionBridge
from gw2radar.oosk.constraint_engine import ConstraintEngine
from gw2radar.oosk.runtime_mapper import RuntimeMapper
from gw2radar.oosk.runtime_store import RuntimeStore


class ThreeLayerPipeline:
    def __init__(self) -> None:
        self._dg_engine = DomainGraphEngine()
        self._dg = None
        self._store = RuntimeStore()
        self._mapper = RuntimeMapper()
        self._bors_compiler = BORSCompiler()
        self._kpi_calc = BusinessKPICalculator()
        self._risk_model = BusinessRiskModel()
        self._decision_engine = DecisionEngine()
        self._value_graph = ValueGraph()
        self._report_gen = BORSReportGenerator()
        self._audit = AuditTrail()
        self._trends = TrendTracker()
        self._action_bridge: OOSKActionBridge | None = None

    @property
    def audit(self) -> AuditTrail:
        return self._audit

    @property
    def trends(self) -> TrendTracker:
        return self._trends

    @property
    def action_bridge(self) -> OOSKActionBridge | None:
        return self._action_bridge

    def load_domain(self, yaml_path: str) -> dict:
        t0 = time.time()
        self._dg = self._dg_engine.load_file(yaml_path)
        errors = self._dg_engine.validate(self._dg)
        result = {
            "domain": self._dg.domain,
            "version": self._dg.version,
            "validation_errors": errors,
            "validation_passed": len(errors) == 0,
            "entity_count": len(self._dg.nodes),
            "relation_count": len(self._dg.edges),
            "event_count": len(self._dg.events),
            "rule_count": len(self._dg.rules),
        }
        self._audit.record("DGSK", "load_domain", duration_ms=(time.time() - t0) * 1000,
                           success=len(errors) == 0, input_summary=yaml_path,
                           output_summary=f"{len(self._dg.nodes)} nodes")
        return result

    def map_to_oosk(self) -> dict:
        if self._dg is None:
            raise RuntimeError("No domain loaded. Call load_domain() first.")
        t0 = time.time()
        self._mapper.map_domain_to_store(self._dg, self._store)
        self._action_bridge = OOSKActionBridge(store=self._store)
        entities = list(self._store.graph.entities.values())
        result = {
            "entities_mapped": len(entities),
            "relations_mapped": len(self._store.graph.relations),
        }
        self._audit.record("OOSK", "map_to_oosk", duration_ms=(time.time() - t0) * 1000,
                           success=True, output_summary=f"{len(entities)} entities")
        return result

    def evaluate_constraints(self) -> dict:
        t0 = time.time()
        engine = ConstraintEngine()
        results = engine.evaluate(self._store.graph)
        summary = engine.summary(results)
        self._audit.record("OOSK", "evaluate_constraints",
                           duration_ms=(time.time() - t0) * 1000,
                           success=summary["failed"] == 0,
                           output_summary=f"{summary['passed']}/{summary['total']} passed")
        return summary

    def decide(self, runtime_state: dict | None = None) -> dict:
        if runtime_state is None:
            runtime_state = {}
        t0 = time.time()

        state = self._mapper.extract_runtime_state(self._store.graph)
        kpis = self._kpi_calc.calculate_all(**runtime_state)
        risks = self._risk_model.assess_all(**runtime_state)

        bors_entities = self._bors_compiler.compile_all(state["entities"])

        decision = self._decision_engine.decide(
            "pipeline_decision",
            kpis=kpis,
            risks=risks,
            entities=bors_entities,
        )

        self._value_graph.build(entities=bors_entities, kpis=kpis, risks=risks)
        self._trends.record(kpis, risks, [decision])

        report = self._report_gen.generate(kpis, risks, [decision])
        result = {
            "decision": decision.decision.value,
            "score": decision.score,
            "reason": decision.reason,
            "kpi_count": len(kpis),
            "risk_count": len(risks),
            "entity_count": len(bors_entities),
            "report": report.to_dict(),
        }
        self._audit.record("BORS", "decide", duration_ms=(time.time() - t0) * 1000,
                           success=True,
                           output_summary=f"{decision.decision.value} (score={decision.score:.2f})")
        return result

    def run_full_pipeline(self, yaml_path: str, runtime_state: dict | None = None) -> dict:
        t0 = time.time()
        load_result = self.load_domain(yaml_path)
        oosk_result = self.map_to_oosk()
        constraint_result = self.evaluate_constraints()
        decision_result = self.decide(runtime_state)
        total_ms = (time.time() - t0) * 1000
        self._audit.record("PIPELINE", "full_pipeline", duration_ms=total_ms,
                           success=True,
                           input_summary=yaml_path,
                           output_summary=decision_result.get("decision", "unknown"))
        return {
            "load": load_result,
            "oosk": oosk_result,
            "constraints": constraint_result,
            "bors": decision_result,
            "audit": self._audit.summary(),
            "trends": self._trends.summary(),
        }
