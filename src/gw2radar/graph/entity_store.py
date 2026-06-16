from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.schemas import Entity


def upsert_entity(graph: GraphData, entity: Entity) -> Entity:
    return graph.add_entity(entity)
