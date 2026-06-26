from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import QAStatus, ReviewStatus


class ImpactReport:
    def __init__(
        self,
        *,
        target: str,
        operation: str,
        risk: str = "low",
        affected_goals: list[str] | None = None,
        affected_reports: list[str] | None = None,
        warnings: list[str] | None = None,
        recommendations: list[str] | None = None,
    ):
        self.target = target
        self.operation = operation
        self.risk = risk
        self.affected_goals = affected_goals or []
        self.affected_reports = affected_reports or []
        self.warnings = warnings or []
        self.recommendations = recommendations or []


def analyze_sell_item(graph: GraphData, item_id: str) -> ImpactReport:
    affected_goals: set[str] = set()
    warnings: list[str] = []
    recommendations: list[str] = []
    risk = "low"

    reservations = graph.find_relations(
        subject_id=item_id,
        predicate=RelationType.RESERVED_FOR_GOAL,
    )
    for res in reservations:
        gid = res.object_id
        affected_goals.add(gid)
        qty = res.properties.get("reserved_quantity", 0)
        warnings.append(f"Reserved for {gid} (quantity: {qty}).")

    required_by = graph.find_relations(
        predicate=RelationType.REQUIRES,
        object_id=item_id,
    )
    for req in required_by:
        affected_goals.add(req.subject_id)
        qty = req.properties.get("required_quantity", 0)
        warnings.append(f"Required by {req.subject_id} (quantity: {qty}).")

    owned = graph.quantity_owned(item_id)
    reserved_qty = sum(
        r.properties.get("reserved_quantity", 0) or 0
        for r in reservations
    )
    safe_surplus = max(owned - reserved_qty, 0)

    if affected_goals:
        risk = "high"
        if safe_surplus > 0:
            recommendations.append(
                f"Only {safe_surplus:.0f} of {owned:.0f} owned is safe surplus; "
                f"do not sell the reserved quantity ({reserved_qty:.0f})."
            )
        else:
            recommendations.append(
                "All owned quantity is reserved for active goals. Do not sell."
            )
    else:
        owned_qty = graph.quantity_owned(item_id)
        if owned_qty > 0:
            risk = "low"
            recommendations.append(
                f"Item is not reserved for any goal. Safe surplus: {owned_qty:.0f}."
            )

    return ImpactReport(
        target=item_id,
        operation="sell_item",
        risk=risk,
        affected_goals=sorted(affected_goals),
        warnings=warnings,
        recommendations=recommendations,
    )


def analyze_goal_change(graph: GraphData, goal_id: str) -> ImpactReport:
    warnings: list[str] = []
    recs: list[str] = []
    risk = "low"

    reservations = graph.find_relations(
        predicate=RelationType.RESERVED_FOR_GOAL,
        object_id=goal_id,
    )
    for res in reservations:
        item_name = graph.entity_name(res.subject_id)
        qty = res.properties.get("reserved_quantity", 0)
        warnings.append(
            f"Removing/altering {goal_id} releases reservation: {item_name} (qty: {qty})."
        )
        risk = "medium"

    reqs = graph.find_relations(
        subject_id=goal_id,
        predicate=RelationType.REQUIRES,
    )
    for req in reqs:
        recs.append(f"Consider whether {graph.entity_name(req.object_id)} is still needed.")

    return ImpactReport(
        target=goal_id,
        operation="goal_change",
        risk=risk,
        affected_goals=[goal_id],
        warnings=warnings,
        recommendations=recs,
    )


def analyze_build_source_stale(graph: GraphData, build_id: str) -> ImpactReport:
    warnings: list[str] = []
    risk = "low"

    build_entity = graph.entities.get(build_id)
    if not build_entity:
        return ImpactReport(
            target=build_id,
            operation="build_source_stale",
            risk="low",
            warnings=["Build not found in graph."],
        )

    if build_entity.review_status == ReviewStatus.REVIEWED:
        risk = "medium"
        warnings.append("Build source is marked reviewed but may be stale.")

    if build_entity.review_status == ReviewStatus.NEEDS_REVIEW:
        risk = "high"
        warnings.append("Build source needs review; stale data may affect Build Fit reports.")
        recommendations = ["Trigger a source review before relying on Build Fit results from this build."]
    else:
        recommendations = ["Review build source freshness before using in paid reports."]

    return ImpactReport(
        target=build_id,
        operation="build_source_stale",
        risk=risk,
        warnings=warnings,
        recommendations=recommendations,
    )


def analyze_report_publish(graph: GraphData, report_entity_id: str) -> ImpactReport:
    warnings: list[str] = []
    risk = "low"

    entity = graph.entities.get(report_entity_id)
    if not entity:
        return ImpactReport(
            target=report_entity_id,
            operation="report_publish",
            risk="high",
            warnings=["Report entity not found in graph."],
        )

    if entity.freshness_status.value == "stale":
        warnings.append("Report data is stale; refresh before publishing.")
        risk = "high"

    if entity.review_status != ReviewStatus.REVIEWED:
        warnings.append(f"Report review status is {entity.review_status.value}; reviewed reports recommended for publication.")
        if risk != "high":
            risk = "medium"

    if entity.qa_status != QAStatus.PASS:
        warnings.append(f"Report QA status is {entity.qa_status.value}; QA must pass before publication.")
        risk = "high"

    evidence_refs = entity.properties.get("evidence_count", 0)
    if evidence_refs == 0:
        warnings.append("Report cites no evidence; verify data sources.")

    recommendations = [
        "Run QA gate before publishing.",
        "Ensure all evidence refs are valid and fresh.",
    ]

    return ImpactReport(
        target=report_entity_id,
        operation="report_publish",
        risk=risk,
        warnings=warnings,
        recommendations=recommendations,
    )
