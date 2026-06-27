from dataclasses import dataclass, field

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import FreshnessStatus, QAStatus, ReviewStatus


@dataclass
class ConstraintResult:
    name: str
    passed: bool
    message: str = ""
    severity: str = "info"
    layer: str = "L2_RUNTIME"


class ConstraintEngine:
    def evaluate(self, context: GraphData) -> list[ConstraintResult]:
        results: list[ConstraintResult] = []
        results.extend(self._l1_static(context))
        results.extend(self._l2_runtime(context))
        results.extend(self._l3_governance(context))
        return results

    def has_failures(self, results: list[ConstraintResult], min_severity: str = "error") -> bool:
        levels = {"info": 0, "warning": 1, "warn": 1, "error": 2}
        min_level = levels.get(min_severity, 2)
        for r in results:
            if not r.passed and levels.get(r.severity, 0) >= min_level:
                return True
        return False

    def summary(self, results: list[ConstraintResult]) -> dict:
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        by_layer: dict[str, dict] = {}
        for r in results:
            bl = by_layer.setdefault(r.layer, {"total": 0, "passed": 0, "failed": 0})
            bl["total"] += 1
            if r.passed:
                bl["passed"] += 1
            else:
                bl["failed"] += 1
        return {"total": total, "passed": passed, "failed": total - passed, "by_layer": by_layer}

    def _l1_static(self, ctx: GraphData) -> list[ConstraintResult]:
        results: list[ConstraintResult] = []
        missing_source = [eid for eid, e in ctx.entities.items() if not e.source_refs]
        results.append(ConstraintResult(
            "L1:all_entities_have_source_refs", not missing_source,
            f"{len(missing_source)} entities missing source refs" if missing_source else "All entities have source refs",
            "warn" if missing_source else "info", "L1_STATIC",
        ))
        return results

    def _l2_runtime(self, ctx: GraphData) -> list[ConstraintResult]:
        results: list[ConstraintResult] = []
        stale = [eid for eid, e in ctx.entities.items() if e.freshness_status == FreshnessStatus.STALE]
        results.append(ConstraintResult(
            "L2:freshness_check", not stale,
            f"{len(stale)} stale entities" if stale else "All entities fresh or unknown",
            "warn" if stale else "info", "L2_RUNTIME",
        ))
        loner_ids = set(ctx.entities.keys()) - {ctx.account_id} if ctx.account_id else set()
        for r in ctx.relations:
            loner_ids.discard(r.subject_id)
            loner_ids.discard(r.object_id)
        results.append(ConstraintResult(
            "L2:no_orphan_entities", not loner_ids,
            f"{len(loner_ids)} entities with no relations" if loner_ids else "All entities connected",
            "warn" if loner_ids else "info", "L2_RUNTIME",
        ))
        return results

    def _l3_governance(self, ctx: GraphData) -> list[ConstraintResult]:
        results: list[ConstraintResult] = []
        for entity in ctx.entities.values():
            if entity.type and entity.type.value == "goal":
                reqs = ctx.find_relations(subject_id=entity.id, predicate=RelationType.REQUIRES)
                if not reqs:
                    results.append(ConstraintResult(
                        "L3:goal_has_requirements", False,
                        f"Goal '{entity.canonical_name}' ({entity.id}) has no REQUIRES relations",
                        "error", "L3_GOVERNANCE",
                    ))
        not_reviewed = [e.id for e in ctx.entities.values() if e.review_status == ReviewStatus.NEEDS_REVIEW]
        if not_reviewed:
            results.append(ConstraintResult(
                "L3:review_status_check", False,
                f"{len(not_reviewed)} entities need review",
                "error", "L3_GOVERNANCE",
            ))
        return results
