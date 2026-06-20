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
    shared_inventory = gateway.get("/v2/account/inventory", api_key=api_key, priority="P1")
    achievements = gateway.get("/v2/account/achievements", api_key=api_key, priority="P1")
    tradingpost_buys = gateway.get("/v2/commerce/transactions/current/buys", api_key=api_key, priority="P2")
    tradingpost_sells = gateway.get("/v2/commerce/transactions/current/sells", api_key=api_key, priority="P2")
    results = [account, characters, wallet, materials, bank, shared_inventory, achievements]
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
        equipment_metadata = _fetch_equipment_metadata(gateway, detail) if detail else _empty_equipment_metadata()
        properties = _character_properties(detail, equipment_metadata) if detail else {"sync_detail_status": "name_only"}
        _ensure_entity(graph, entity_id, EntityType.CHARACTER, str(name), GraphLayer.PRIVATE_PLAYER_STATE, properties)
        _add_private_state(graph, account_id, entity_id, 1.0, "characters")
        if detail:
            _add_character_equipment_state(graph, account_id, entity_id, detail, equipment_metadata)
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
        _add_private_state(
            graph,
            account_id,
            entity_id,
            float(entry.get("count", 0)),
            "bank",
            properties={"binding": entry.get("binding")},
        )
        count += 1
    for slot_index, entry in enumerate(shared_inventory.payload):
        if entry is None:
            continue
        entity_id = f"gw2:item:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ITEM, f"Item {entry['id']}")
        _add_private_state(
            graph,
            account_id,
            entity_id,
            float(entry.get("count", 0)),
            f"shared_inventory:{slot_index}",
            properties={"binding": entry.get("binding")},
        )
        count += 1
    for entry in achievements.payload:
        entity_id = f"gw2:achievement:{entry['id']}"
        _ensure_entity(graph, entity_id, EntityType.ACHIEVEMENT, f"Achievement {entry['id']}")
        current = float(entry.get("current", 0))
        max_value = float(entry.get("max", 1) or 1)
        _add_private_state(graph, account_id, entity_id, current / max_value, "achievements")
        count += 1
    if tradingpost_buys.status == GatewayStatus.OK:
        count += _add_tradingpost_orders(graph, account_id, tradingpost_buys.payload, "tradingpost_buy")
    if tradingpost_sells.status == GatewayStatus.OK:
        count += _add_tradingpost_orders(graph, account_id, tradingpost_sells.payload, "tradingpost_sell")
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
    properties: dict | None = None,
) -> None:
    graph.add_player_state(
        PlayerState(
            id=f"state:{account_id}:{entity_id}:{_safe_state_id(location)}",
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
                properties={"quantity": quantity, "location": location, **(properties or {})},
            )
        )


def _fetch_character_detail(gateway: Gw2ApiGateway, character_name: str, api_key: str) -> dict | None:
    endpoint = f"/v2/characters/{quote(character_name, safe='')}"
    try:
        result = gateway.get(endpoint, api_key=api_key, priority="P1")
    except Exception:
        return None
    return result.payload if result.status == GatewayStatus.OK and isinstance(result.payload, dict) else None


def _add_tradingpost_orders(graph: GraphData, account_id: str, orders: list | None, location: str) -> int:
    count = 0
    if not isinstance(orders, list):
        return count
    for index, order in enumerate(orders):
        if not isinstance(order, dict):
            continue
        item_id = order.get("item_id")
        quantity = float(order.get("quantity", 0) or 0)
        if item_id is None or quantity <= 0:
            continue
        entity_id = f"gw2:item:{item_id}"
        _ensure_entity(graph, entity_id, EntityType.ITEM, f"Item {item_id}")
        _add_private_state(
            graph,
            account_id,
            entity_id,
            quantity,
            f"{location}:{index}",
            properties={"price": order.get("price")},
        )
        count += 1
    return count


def _safe_state_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "unknown"


def _character_properties(detail: dict, equipment_metadata: dict[str, dict[int, dict]]) -> dict:
    return {
        "profession": detail.get("profession"),
        "level": detail.get("level"),
        "race": detail.get("race"),
        "gender": detail.get("gender"),
        "equipment": _equipment_entries(detail, equipment_metadata),
        "sync_detail_status": "detail_synced",
    }


def _equipment_entries(detail: dict, equipment_metadata: dict[str, dict[int, dict]]) -> list[dict]:
    entries: list[dict] = []
    for item in detail.get("equipment", []):
        if not isinstance(item, dict):
            continue
        entries.append(_equipment_properties(item, equipment_metadata))
        entries.extend(_upgrade_equipment_properties(item, equipment_metadata))
    return entries


def _equipment_properties(
    item: dict,
    equipment_metadata: dict[str, dict[int, dict]] | None = None,
    *,
    slot_override: str | None = None,
    item_id_override: int | None = None,
    equipment_category_override: str | None = None,
    source_slot: str | None = None,
) -> dict:
    equipment_metadata = equipment_metadata or _empty_equipment_metadata()
    stats = item.get("stats") if isinstance(item.get("stats"), dict) else {}
    item_id = item_id_override or item.get("id")
    stat_id = stats.get("id")
    official_item = _metadata_entry(equipment_metadata.get("items", {}), item_id)
    official_stat = _metadata_entry(equipment_metadata.get("itemstats", {}), stat_id)
    item_name = item.get("name") or official_item.get("name") or f"Item {item.get('id', 'unknown')}"
    if item_id_override is not None:
        item_name = official_item.get("name") or f"Item {item_id_override}"
    stat_combo = (
        item.get("stat_combo")
        or stats.get("name")
        or official_stat.get("name")
        or _upgrade_stat_combo(official_item)
        or (f"stat:{stat_id}" if stat_id else "Unknown")
    )
    metadata_sources = []
    if official_item.get("name"):
        metadata_sources.append("official_items")
    if official_stat.get("name"):
        metadata_sources.append("official_itemstats")
    return {
        "slot": slot_override or item.get("slot"),
        "item_id": item_id,
        "item_name": item_name,
        "stat_combo": stat_combo,
        "stat_id": stat_id,
        "equipment_category": equipment_category_override or _equipment_category(item.get("slot"), official_item),
        "source_slot": source_slot or item.get("slot"),
        "metadata_sources": metadata_sources,
    }


def _upgrade_equipment_properties(item: dict, equipment_metadata: dict[str, dict[int, dict]]) -> list[dict]:
    entries: list[dict] = []
    upgrades = item.get("upgrades") if isinstance(item.get("upgrades"), list) else []
    for upgrade_id in upgrades:
        official_item = _metadata_entry(equipment_metadata.get("items", {}), upgrade_id)
        category = _equipment_category(None, official_item)
        if category not in {"rune", "sigil"}:
            continue
        entries.append(
            _equipment_properties(
                item,
                equipment_metadata,
                slot_override=category,
                item_id_override=_safe_int(upgrade_id),
                equipment_category_override=category,
                source_slot=str(item.get("slot") or ""),
            )
        )
    return entries


def _add_character_equipment_state(
    graph: GraphData,
    account_id: str,
    character_id: str,
    detail: dict,
    equipment_metadata: dict[str, dict[int, dict]],
) -> None:
    for equipment in _equipment_entries(detail, equipment_metadata):
        if equipment.get("item_id") is None:
            continue
        entity_id = f"gw2:item:{equipment['item_id']}"
        _ensure_entity(
            graph,
            entity_id,
            EntityType.ITEM,
            equipment["item_name"],
            GraphLayer.PRIVATE_PLAYER_STATE,
            {
                "equipment_slot": equipment["slot"],
                "stat_combo": equipment["stat_combo"],
                "stat_id": equipment["stat_id"],
                "equipment_category": equipment["equipment_category"],
                "source_slot": equipment["source_slot"],
                "metadata_sources": equipment["metadata_sources"],
            },
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


def _empty_equipment_metadata() -> dict[str, dict[int, dict]]:
    return {"items": {}, "itemstats": {}}


def _fetch_equipment_metadata(gateway: Gw2ApiGateway, detail: dict) -> dict[str, dict[int, dict]]:
    equipment = [item for item in detail.get("equipment", []) if isinstance(item, dict)]
    item_ids = sorted(
        {
            item_id
            for item in equipment
            for item_id in [_safe_int(item.get("id")), *_safe_upgrade_ids(item)]
            if item_id is not None
        }
    )
    stat_ids = sorted(
        {
            _safe_int(item.get("stats", {}).get("id"))
            for item in equipment
            if isinstance(item.get("stats"), dict) and _safe_int(item.get("stats", {}).get("id")) is not None
        }
    )
    return {
        "items": _fetch_public_metadata(gateway, "/v2/items", item_ids),
        "itemstats": _fetch_public_metadata(gateway, "/v2/itemstats", stat_ids),
    }


def _fetch_public_metadata(gateway: Gw2ApiGateway, endpoint: str, ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    try:
        result = gateway.get_batch(endpoint, ids=ids, priority="P2")
    except Exception:
        return {}
    if result.status != GatewayStatus.OK:
        return {}
    payload = result.payload
    rows = payload if isinstance(payload, list) else [payload]
    metadata: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_id = _safe_int(row.get("id"))
        if row_id is not None:
            metadata[row_id] = row
    return metadata


def _metadata_entry(metadata: dict[int, dict], raw_id: object) -> dict:
    row_id = _safe_int(raw_id)
    if row_id is None:
        return {}
    return metadata.get(row_id, {})


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_upgrade_ids(item: dict) -> list[int]:
    upgrades = item.get("upgrades") if isinstance(item.get("upgrades"), list) else []
    return [value for value in (_safe_int(upgrade_id) for upgrade_id in upgrades) if value is not None]


def _equipment_category(slot: object, official_item: dict) -> str:
    details = official_item.get("details") if isinstance(official_item.get("details"), dict) else {}
    detail_type = str(details.get("type") or "").lower()
    item_type = str(official_item.get("type") or "").lower()
    slot_value = str(slot or "").lower()
    if detail_type == "rune" or slot_value == "rune":
        return "rune"
    if detail_type == "sigil" or slot_value == "sigil":
        return "sigil"
    if item_type == "relic" or slot_value == "relic":
        return "relic"
    if slot_value.startswith("weapon"):
        return "weapon"
    if slot_value in {"helm", "head", "shoulders", "coat", "chest", "gloves", "hands", "leggings", "legs", "boots", "feet"}:
        return "armor"
    return "equipment"


def _upgrade_stat_combo(official_item: dict) -> str | None:
    details = official_item.get("details") if isinstance(official_item.get("details"), dict) else {}
    detail_type = details.get("type")
    if detail_type in {"Rune", "Sigil"}:
        return str(detail_type)
    if str(official_item.get("type") or "").lower() == "relic":
        return "Relic"
    return None
