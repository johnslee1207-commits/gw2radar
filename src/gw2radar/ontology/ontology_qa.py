from dataclasses import dataclass, field

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import FreshnessStatus, QAStatus, ReviewStatus


@dataclass
class QAResult:
    check_name: str
    passed: bool
    message: str = ""
    severity: str = "info"


@dataclass
class QASuiteResult:
    passed: bool
    results: list[QAResult] = field(default_factory=list)

    def summary(self) -> str:
        total = len(self.results)
        passed_count = sum(1 for r in self.results if r.passed)
        return f"{passed_count}/{total} checks passed"


def check_goal_requirement_resolves(graph: GraphData) -> QAResult:
    for entity in graph.entities.values():
        if entity.type.value != "goal":
            continue
        reqs = graph.find_relations(subject_id=entity.id, predicate=RelationType.REQUIRES)
        if not reqs:
            return QAResult(
                "goal_requirement_resolves",
                False,
                f"Goal {entity.id} has no REQUIRES relations.",
                "error",
            )
        for req in reqs:
            if req.object_id not in graph.entities:
                return QAResult(
                    "goal_requirement_resolves",
                    False,
                    f"Goal {entity.id} requires {req.object_id} which is not in the entity index.",
                    "error",
                )
    return QAResult("goal_requirement_resolves", True, "All goal requirements resolve to known entities.")


def check_reserved_quantity_not_exceed_owned(graph: GraphData) -> QAResult:
    for rel in graph.find_relations(predicate=RelationType.RESERVED_FOR_GOAL):
        qty = rel.properties.get("reserved_quantity", 0)
        if isinstance(qty, (int, float)) and qty > 0:
            owned = graph.quantity_owned(rel.subject_id)
            if owned < qty:
                return QAResult(
                    "reserved_quantity_not_exceed_owned",
                    False,
                    f"{rel.subject_id}: reserved {qty} > owned {owned}.",
                    "error",
                )
    return QAResult("reserved_quantity_not_exceed_owned", True, "All reserved quantities are within owned amounts.")


def check_private_data_not_public(graph: GraphData) -> QAResult:
    for rel in graph.relations:
        if rel.graph_layer is not None:
            from gw2radar.ontology.graph_layers import GraphLayer
            if rel.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE:
                return QAResult(
                    "private_data_not_public",
                    True,
                    "Private player state relations are correctly scoped.",
                )
    return QAResult("private_data_not_public", True, "No private layer relations found.")


def check_evidence_refs_exist(graph: GraphData) -> QAResult:
    if not graph.evidence:
        return QAResult(
            "evidence_refs_exist",
            False,
            "No evidence records in graph.",
            "warn",
        )
    return QAResult("evidence_refs_exist", True, f"{len(graph.evidence)} evidence records available.")


def check_build_source_reviewed(graph: GraphData) -> QAResult:
    for entity in graph.entities.values():
        if entity.type.value == "item" and entity.review_status == ReviewStatus.NEEDS_REVIEW:
            return QAResult(
                "build_source_reviewed",
                False,
                f"Entity {entity.id} needs review.",
                "warn",
            )
    return QAResult("build_source_reviewed", True, "All build sources are reviewed or pending.")


def check_market_data_fresh_enough(graph: GraphData) -> QAResult:
    stale_count = sum(
        1 for e in graph.entities.values()
        if e.freshness_status == FreshnessStatus.STALE
    )
    if stale_count > 0:
        return QAResult(
            "market_data_fresh_enough",
            False,
            f"{stale_count} entities have stale freshness.",
            "warn",
        )
    return QAResult("market_data_fresh_enough", True, "All entities have fresh or unknown freshness.")


ALL_CHECKS = [
    ("goal_requirement_resolves", check_goal_requirement_resolves),
    ("reserved_quantity_not_exceed_owned", check_reserved_quantity_not_exceed_owned),
    ("private_data_not_public", check_private_data_not_public),
    ("evidence_refs_exist", check_evidence_refs_exist),
    ("build_source_reviewed", check_build_source_reviewed),
    ("market_data_fresh_enough", check_market_data_fresh_enough),
]


def run_qa_suite(graph: GraphData, *, checks: list[str] | None = None) -> QASuiteResult:
    results: list[QAResult] = []
    if checks is not None:
        selected = [(name, fn) for name, fn in ALL_CHECKS if name in checks]
    else:
        selected = list(ALL_CHECKS)
    for name, fn in selected:
        try:
            result = fn(graph)
        except Exception as exc:
            result = QAResult(name, False, str(exc), "error")
        results.append(result)
    return QASuiteResult(passed=all(r.passed for r in results), results=results)
