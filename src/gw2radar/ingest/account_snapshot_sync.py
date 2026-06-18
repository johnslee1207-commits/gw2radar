from urllib.parse import quote

from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, PlayerState, Relation


def sync_account_snapshot(graph: GraphData, gateway: Gw2ApiGateway, *, api_key: str) -> dict:
    account = gateway.get("/v2/account", api_key=api_key, priority="P1")
    characters = gateway.get("/v2/characters", api_key=api_key, priority="P1")
    wallet = gateway.get("/v2/account/wallet", api_key=api_key, priority="P1")
    materials = gateway.get("/v2/account/materials", api_key=api_key, priority="P1")
    bank = gateway.get("/v2/account/bank", api_key=api_key, priority="P1")
    achievements = gateway.get("/v2/account/achievements", api_key=api_key, priority="P1")
    results = [account, characters, wallet, materials, bank, achievements]
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
    for name in characters.payload:
        entity_id = f"gw2:character:{name}"
        detail = _fetch_character_detail(gateway, str(name), api_key)
        properties = _character_properties(detail) if detail else {"sync_detail_status": "name_only"}
        _ensure_entity(graph, entity_id, EntityType.CHARACTER, str(name), GraphLayer.PRIVATE_PLAYER_STATE, properties)
        _add_private_state(graph, account_id, entity_id, 1.0, "characters")
        if detail:
            _add_character_equipment_state(graph, account_id, entity_id, detail)
        count += 1
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
    for entry in bank.payload:
        if entry is None:
            continue
        entity_id = f"gw2:item:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ITEM, f"Item {entry['id']}")
        _add_private_state(graph, account_id, entity_id, float(entry.get("count", 0)), "bank")
        count += 1
    for entry in achievements.payload:
        entity_id = f"gw2:achievement:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ACHIEVEMENT, f"Achievement {entry['id']}")
        current = float(entry.get("current", 0))
        max_value = float(entry.get("max", 1) or 1)
        _add_private_state(graph, account_id, entity_id, current / max_value, "achievements")
        count += 1
    return {"status": "synced", "account_id": account_id, "updated_player_state": count}


def _ensure_entity(
    graph: GraphData,
    entity_id: str,
    entity_type: EntityType,
    name: str,
    graph_layer: GraphLayer = GraphLayer.PUBLIC_GAME,
    properties: dict | None = None,
) -> None:
    if entity_id not in graph.entities:
        graph.add_entity(
            Entity(
                id=entity_id,
                type=entity_type,
                canonical_name=name,
                graph_layer=graph_layer,
                properties=properties or {},
            )
        )
    elif properties:
        graph.entities[entity_id].properties.update(properties)


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


def _fetch_character_detail(gateway: Gw2ApiGateway, character_name: str, api_key: str) -> dict | None:
    endpoint = f"/v2/characters/{quote(character_name, safe='')}"
    try:
        result = gateway.get(endpoint, api_key=api_key, priority="P1")
    except Exception:
        return None
    return result.payload if result.status == GatewayStatus.OK and isinstance(result.payload, dict) else None


def _character_properties(detail: dict) -> dict:
    return {
        "profession": detail.get("profession"),
        "level": detail.get("level"),
        "race": detail.get("race"),
        "gender": detail.get("gender"),
        "equipment": [_equipment_properties(item) for item in detail.get("equipment", []) if isinstance(item, dict)],
        "sync_detail_status": "detail_synced",
    }


def _equipment_properties(item: dict) -> dict:
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    return {
        "slot": item.get("slot"),
        "item_id": item.get("id"),
        "item_name": item.get("name") or f"Item {item.get('id', 'unknown')}",
        "stat_combo": item.get("stat_combo") or stats.get("name") or (f"stat:{stats.get('id')}" if stats.get("id") else "Unknown"),
    }


def _add_character_equipment_state(graph: GraphData, account_id: str, character_id: str, detail: dict) -> None:
    for item in detail.get("equipment", []):
        if not isinstance(item, dict) or item.get("id") is None:
            continue
        equipment = _equipment_properties(item)
        entity_id = f"gw2:item:{equipment['item_id']}"
        _ensure_entity(
            graph,
            entity_id,
            EntityType.ITEM,
            equipment["item_name"],
            GraphLayer.PRIVATE_PLAYER_STATE,
            {"equipment_slot": equipment["slot"], "stat_combo": equipment["stat_combo"]},
        )
        _add_private_state(graph, account_id, entity_id, 1.0, f"character_equipment:{character_id}")
        relation_id = f"rel:{character_id}:owns:{entity_id}:{equipment['slot']}"
        if not any(relation.id == relation_id for relation in graph.relations):
            graph.add_relation(
                Relation(
                    id=relation_id,
                    subject_id=character_id,
                    predicate=RelationType.OWNED_BY,
                    object_id=entity_id,
                    graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
                    properties={"quantity": 1, "location": "character_equipment", "slot": equipment["slot"]},
                )
            )
