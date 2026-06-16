from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity


def refresh_public_items(graph: GraphData, gateway: Gw2ApiGateway, *, item_ids: list[int]) -> dict:
    result = gateway.get_batch("/v2/items", ids=item_ids, priority="P3")
    if result.status != GatewayStatus.OK:
        return {"status": result.status.value, "updated_entities": 0}
    updated = 0
    for item in result.payload:
        entity_id = f"gw2:item:{item['id']}"
        graph.add_entity(
            Entity(
                id=entity_id,
                type=EntityType.ITEM,
                canonical_name=item.get("name", f"Item {item['id']}"),
                graph_layer=GraphLayer.PUBLIC_GAME,
                external_id=str(item["id"]),
                properties={
                    "rarity": item.get("rarity"),
                    "level": item.get("level"),
                    "type": item.get("type"),
                },
            )
        )
        updated += 1
    return {"status": "synced", "updated_entities": updated}
