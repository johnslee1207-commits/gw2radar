from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, PlayerState, Relation


def sync_account_snapshot(graph: GraphData, gateway: Gw2ApiGateway, *, api_key: str) -> dict:
    account = gateway.get("/v2/account", api_key=api_key, priority="P1")
    wallet = gateway.get("/v2/account/wallet", api_key=api_key, priority="P1")
    materials = gateway.get("/v2/account/materials", api_key=api_key, priority="P1")
    achievements = gateway.get("/v2/account/achievements", api_key=api_key, priority="P1")
    results = [account, wallet, materials, achievements]
    if any(result.status != GatewayStatus.OK for result in results):
        return {"status": "refresh_pending", "updated_player_state": 0}

    account_id = f"gw2:account:{account.payload.get('name', 'unknown')}"
    graph.account_id = account_id
    graph.add_entity(
        Entity(
            id=account_id,
            type=EntityType.ACCOUNT,
            canonical_name=account.payload.get("name", "GW2 Account"),
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            properties={"world": account.payload.get("world")},
        )
    )

    count = 0
    for entry in wallet.payload:
        entity_id = f"gw2:currency:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.CURRENCY, f"Currency {entry['id']}")
        _add_private_state(graph, account_id, entity_id, float(entry.get("value", 0)), "wallet")
        count += 1
    for entry in materials.payload:
        entity_id = f"gw2:item:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ITEM, f"Item {entry['id']}")
        _add_private_state(graph, account_id, entity_id, float(entry.get("count", 0)), "materials")
        count += 1
    for entry in achievements.payload:
        entity_id = f"gw2:achievement:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ACHIEVEMENT, f"Achievement {entry['id']}")
        current = float(entry.get("current", 0))
        max_value = float(entry.get("max", 1) or 1)
        _add_private_state(graph, account_id, entity_id, current / max_value, "achievements")
        count += 1
    return {"status": "synced", "account_id": account_id, "updated_player_state": count}


def _ensure_entity(graph: GraphData, entity_id: str, entity_type: EntityType, name: str) -> None:
    if entity_id not in graph.entities:
        graph.add_entity(
            Entity(
                id=entity_id,
                type=entity_type,
                canonical_name=name,
                graph_layer=GraphLayer.PUBLIC_GAME,
            )
        )


def _add_private_state(
    graph: GraphData,
    account_id: str,
    entity_id: str,
    quantity: float,
    location: str,
) -> None:
    graph.add_player_state(
        PlayerState(
            id=f"state:{account_id}:{entity_id}",
            account_id=account_id,
            entity_id=entity_id,
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            quantity=quantity,
            location=location,
        )
    )
    relation_id = f"rel:{account_id}:owns:{entity_id}"
    if not any(relation.id == relation_id for relation in graph.relations):
        graph.add_relation(
            Relation(
                id=relation_id,
                subject_id=account_id,
                predicate=RelationType.OWNED_BY,
                object_id=entity_id,
                graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
                properties={"quantity": quantity, "location": location},
            )
        )
