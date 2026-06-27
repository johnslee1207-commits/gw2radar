"""Bridge between OOSK and existing ontology action_registry + impact_analyzer."""

from typing import Any

from sqlalchemy.orm import Session

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.action_registry import (
    ActionEffect as OntologyActionEffect,
    REGISTRY as ONTOLOGY_REGISTRY,
    check_preconditions,
    generate_do_not_sell,
    generate_legendary_plan,
    list_registry,
    reserve_material_for_goal,
    run_qa_hooks,
)
from gw2radar.ontology.impact_analyzer import (
    ImpactReport,
    analyze_build_source_stale,
    analyze_goal_change,
    analyze_report_publish,
    analyze_sell_item,
)
from gw2radar.ontology.ontology_qa import run_qa_suite
from gw2radar.oosk.runtime_store import RuntimeStore


class OOSKActionBridge:
    def __init__(self, store: RuntimeStore | None = None, session: Session | None = None) -> None:
        self._store = store
        self._session = session

    @property
    def graph(self) -> GraphData:
        if self._store:
            return self._store.graph
        from gw2radar.graph.graph_builder import build_mock_graph
        return build_mock_graph()

    def list_actions(self) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for key, entry in ONTOLOGY_REGISTRY.items():
            result[key] = {
                "title": entry.title,
                "description": entry.description,
                "preconditions": entry.preconditions,
                "effects": entry.effects,
                "qa_hooks": entry.qa_hooks,
            }
        return result

    def check_preconditions(self, action_id: str, **kwargs: Any) -> list[str]:
        entry = ONTOLOGY_REGISTRY.get(action_id)
        if not entry:
            return [f"Action '{action_id}' not found"]
        return check_preconditions(entry, self.graph, self._session, **kwargs)

    def run_qa(self, action_id: str) -> list[str]:
        entry = ONTOLOGY_REGISTRY.get(action_id)
        if not entry:
            return [f"Action '{action_id}' not found"]
        return run_qa_hooks(entry, self.graph)

    def reserve_material(self, item_id: str, goal_id: str, quantity: float) -> dict:
        effect = reserve_material_for_goal(
            self.graph, self._session,
            item_id=item_id, goal_id=goal_id, quantity=quantity,
        )
        return {"description": effect.description, "affected": effect.affected_entity_ids}

    def generate_do_not_sell(self, goal_id: str) -> dict:
        effect = generate_do_not_sell(self.graph, self._session, goal_id)
        return {"description": effect.description, "affected": effect.affected_entity_ids}

    def generate_legendary_plan(self, goal_id: str) -> dict:
        effect = generate_legendary_plan(self.graph, self._session, goal_id)
        return {"description": effect.description, "affected": effect.affected_entity_ids}

    def analyze_impact_sell(self, item_id: str) -> dict:
        report = analyze_sell_item(self.graph, item_id)
        return self._impact_to_dict(report)

    def analyze_impact_goal(self, goal_id: str) -> dict:
        report = analyze_goal_change(self.graph, goal_id)
        return self._impact_to_dict(report)

    def analyze_impact_build(self, build_id: str) -> dict:
        report = analyze_build_source_stale(self.graph, build_id)
        return self._impact_to_dict(report)

    def analyze_impact_report(self, report_id: str) -> dict:
        report = analyze_report_publish(self.graph, report_id)
        return self._impact_to_dict(report)

    def run_qa_suite(self, checks: list[str] | None = None) -> dict:
        suite = run_qa_suite(self.graph, checks=checks)
        return {
            "passed": suite.passed,
            "summary": suite.summary(),
            "results": [
                {"name": r.check_name, "passed": r.passed, "message": r.message, "severity": r.severity}
                for r in suite.results
            ],
        }

    def _impact_to_dict(self, report: ImpactReport) -> dict:
        return {
            "target": report.target,
            "operation": report.operation,
            "risk": report.risk,
            "affected_goals": report.affected_goals,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }
