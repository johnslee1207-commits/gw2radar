from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, FreshnessStatus, ObjectRef, QAStatus, ReviewStatus


def enrich_account_entities(graph: GraphData) -> GraphData:
    for eid, entity in list(graph.entities.items()):
        if entity.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE:
            _enrich_private_entity(entity)
        if entity.type == EntityType.ACCOUNT:
            _enrich_account_entity(entity, graph)
    return graph


def _enrich_private_entity(entity: Entity) -> None:
    if entity.freshness_status == FreshnessStatus.UNKNOWN:
        entity.freshness_status = FreshnessStatus.FRESH
    if entity.review_status == ReviewStatus.PENDING:
        entity.review_status = ReviewStatus.PENDING
    if entity.qa_status == QAStatus.UNTESTED:
        entity.qa_status = QAStatus.UNTESTED
    has_source = any(ref.source == "private_player_state" for ref in entity.source_refs)
    if not has_source:
        entity.source_refs.append(
            ObjectRef(source="private_player_state", ref_id=None, privacy_scope="private_summary_only")
        )


def _enrich_account_entity(entity: Entity, graph: GraphData) -> None:
    holdings = [
        ps for ps in graph.player_state
        if ps.account_id == entity.id and ps.location in {"materials", "currencies"}
    ]
    location_count = len({h.location for h in holdings if h.location})
    if location_count > 0:
        if entity.freshness_status == FreshnessStatus.UNKNOWN:
            entity.freshness_status = FreshnessStatus.FRESH
        entity.properties["holding_location_count"] = location_count
        entity.properties["holding_count"] = len(holdings)
