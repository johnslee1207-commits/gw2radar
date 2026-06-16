from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.schemas import Relation


def add_relation(graph: GraphData, relation: Relation) -> Relation:
    return graph.add_relation(relation)
