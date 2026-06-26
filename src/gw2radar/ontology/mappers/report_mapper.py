from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.schemas import Entity, FreshnessStatus, ObjectRef, QAStatus, ReviewStatus


def enrich_report_entities(
    graph: GraphData,
    *,
    report_id: str,
    report_type: str,
    evidence_ids: list[str] | None = None,
) -> GraphData:
    eid = report_id if report_id.startswith("gw2:report:") else f"gw2:report:{report_id}"
    if eid in graph.entities:
        return graph
    graph.add_entity(
        Entity(
            id=eid,
            type=EntityType.EVIDENCE,
            canonical_name=f"Report: {report_type}",
            freshness_status=FreshnessStatus.FRESH,
            review_status=ReviewStatus.PENDING,
            qa_status=QAStatus.UNTESTED,
            source_refs=[
                ObjectRef(source="report_engine", ref_id=eid, privacy_scope="private_summary_only"),
            ],
            properties={
                "report_type": report_type,
                "evidence_count": len(evidence_ids or []),
            },
        )
    )
    return graph
