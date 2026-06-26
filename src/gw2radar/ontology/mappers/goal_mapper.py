from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, FreshnessStatus, ObjectRef, QAStatus, ReviewStatus


def enrich_goal_entities(graph: GraphData) -> GraphData:
    for eid, entity in list(graph.entities.items()):
        if entity.type != EntityType.GOAL:
            continue
        requires = graph.find_relations(subject_id=eid, predicate=RelationType.REQUIRES)
        if entity.freshness_status == FreshnessStatus.UNKNOWN:
            entity.freshness_status = FreshnessStatus.FRESH
        if entity.review_status == ReviewStatus.PENDING:
            entity.review_status = ReviewStatus.NEEDS_REVIEW if len(requires) > 0 else ReviewStatus.PENDING
        if entity.qa_status == QAStatus.UNTESTED:
            entity.qa_status = QAStatus.UNTESTED
        entity.properties["requirement_count"] = len(requires)
        missing_refs = {req.object_id for req in requires}
        known = {eid for eid in missing_refs if eid in graph.entities}
        entity.properties["known_requirement_count"] = len(known)
        entity.properties["unknown_requirement_count"] = len(missing_refs - known)
        has_source = any(ref.source == "goal_mapper" for ref in entity.source_refs)
        if not has_source:
            entity.source_refs.append(
                ObjectRef(source="goal_mapper", ref_id=eid, privacy_scope="public")
            )
    return graph
