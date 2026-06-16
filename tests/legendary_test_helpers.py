from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity


def add_second_legendary_goal(graph: GraphData) -> None:
    aurora = graph.entities["gw2:goal:aurora"]
    requirements = [
        dict(aurora.properties["requirements"][0]),
        dict(aurora.properties["requirements"][2]),
    ]
    requirements[0]["required_quantity"] = 150
    requirements[1]["required_quantity"] = 5000
    graph.add_entity(
        Entity(
            id="gw2:goal:vision",
            type=EntityType.GOAL,
            canonical_name="Vision",
            graph_layer=GraphLayer.PUBLIC_GAME,
            properties={"goal_type": "legendary_trinket", "requirements": requirements},
        )
    )
