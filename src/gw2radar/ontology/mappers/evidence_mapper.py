from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.schemas import Entity, FreshnessStatus, ObjectRef, QAStatus, ReviewStatus


def enrich_evidence_entities(graph: GraphData) -> GraphData:
    for eid, evidence in list(graph.evidence.items()):
        if eid in graph.entities:
            existing = graph.entities[eid]
            if existing.freshness_status == FreshnessStatus.UNKNOWN:
                existing.freshness_status = FreshnessStatus.FRESH
            if existing.review_status == ReviewStatus.PENDING:
                existing.review_status = ReviewStatus.PENDING
            if existing.qa_status == QAStatus.UNTESTED:
                existing.qa_status = QAStatus.UNTESTED
            continue
        graph.add_entity(
            Entity(
                id=eid,
                type=EntityType.EVIDENCE,
                canonical_name=f"Evidence: {evidence.source}",
                graph_layer=evidence.graph_layer,
                freshness_status=FreshnessStatus.FRESH,
                review_status=ReviewStatus.PENDING,
                qa_status=QAStatus.UNTESTED,
                source_refs=[
                    ObjectRef(source=evidence.source, ref_id=eid, privacy_scope="public"),
                ],
                properties={
                    "source_type": evidence.source_type,
                    "confidence": evidence.confidence,
                },
            )
        )
    return graph
