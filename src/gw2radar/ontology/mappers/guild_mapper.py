from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, FreshnessStatus, ObjectRef, QAStatus, ReviewStatus


def enrich_guild_entities(graph: GraphData) -> GraphData:
    present = {e.id for e in graph.entities.values()}
    for ps in graph.player_state:
        if ps.location not in {"materials", "currencies"}:
            continue
        if ps.entity_id not in present:
            graph.add_entity(
                Entity(
                    id=ps.entity_id,
                    type=_entity_type_for_location(ps.location),
                    canonical_name=ps.entity_id,
                    graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
                    freshness_status=FreshnessStatus.FRESH,
                    review_status=ReviewStatus.PENDING,
                    qa_status=QAStatus.UNTESTED,
                    source_refs=[
                        ObjectRef(source="guild_mapper", ref_id=ps.entity_id, privacy_scope="private_summary_only"),
                    ],
                    properties={
                        "quantity": ps.quantity,
                        "location": ps.location,
                    },
                )
            )
        else:
            existing = graph.entities[ps.entity_id]
            if existing.freshness_status == FreshnessStatus.UNKNOWN:
                existing.freshness_status = FreshnessStatus.FRESH
            existing.properties["quantity"] = ps.quantity
            existing.properties["location"] = ps.location
    return graph


def compute_member_readiness_from_graph(member_user_id: str, graph: GraphData) -> float:
    total = 0.0
    count = 0
    for ps in graph.player_state:
        if ps.account_id == member_user_id and ps.location in {"materials", "currencies"}:
            total += min(ps.quantity / 1000, 1.0) if ps.location == "currencies" else min(ps.quantity / 250, 1.0)
            count += 1
    if count == 0:
        return 0.0
    return round(min(total / count, 1.0), 2)


def _entity_type_for_location(location: str) -> EntityType:
    mapping = {
        "materials": EntityType.MATERIAL,
        "currencies": EntityType.CURRENCY,
    }
    return mapping.get(location, EntityType.ITEM)
