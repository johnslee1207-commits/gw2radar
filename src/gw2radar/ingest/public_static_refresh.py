from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.evidence_writer import EvidenceWriter
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity

PUBLIC_STATIC_ENDPOINT_TYPES = {
    "/v2/items": EntityType.ITEM,
    "/v2/achievements": EntityType.ACHIEVEMENT,
    "/v2/currencies": EntityType.CURRENCY,
    "/v2/recipes": EntityType.RECIPE,
}

PUBLIC_STATIC_ID_PREFIXES = {
    "/v2/items": "gw2:item",
    "/v2/achievements": "gw2:achievement",
    "/v2/currencies": "gw2:currency",
    "/v2/recipes": "gw2:recipe",
}


def refresh_public_static(
    graph: GraphData,
    gateway: Gw2ApiGateway,
    *,
    endpoint: str,
    ids: list[int],
    chunk_size: int = 200,
) -> dict:
    if endpoint not in PUBLIC_STATIC_ENDPOINT_TYPES:
        raise ValueError(f"Unsupported public static endpoint: {endpoint}")
    normalized_ids = sorted(set(int(item_id) for item_id in ids))
    updated = 0
    evidence_ids: list[str] = []
    chunks = list(_chunks(normalized_ids, chunk_size))
    for chunk in chunks:
        result = gateway.get_batch(endpoint, ids=chunk, priority="P3")
        if result.status != GatewayStatus.OK and result.status != GatewayStatus.CACHE_HIT:
            return {
                "status": result.status.value,
                "updated_entities": updated,
                "chunks": len(chunks),
                "evidence_ids": evidence_ids,
            }
        if result.evidence_id:
            evidence_writer = getattr(gateway, "evidence_writer", EvidenceWriter())
            graph.add_evidence(evidence_writer.from_api_payload(
                evidence_id=result.evidence_id,
                endpoint=endpoint,
                payload={"endpoint": endpoint, "ids": chunk, "payload": result.payload},
            ))
            evidence_ids.append(result.evidence_id)
        for payload in result.payload:
            graph.add_entity(_entity_from_payload(endpoint, payload, evidence_id=result.evidence_id))
            updated += 1
    return {
        "status": "synced",
        "updated_entities": updated,
        "chunks": len(chunks),
        "evidence_ids": evidence_ids,
    }


def refresh_public_items(graph: GraphData, gateway: Gw2ApiGateway, *, item_ids: list[int]) -> dict:
    return refresh_public_static(graph, gateway, endpoint="/v2/items", ids=item_ids)


def _entity_from_payload(endpoint: str, payload: dict, *, evidence_id: str | None) -> Entity:
    entity_type = PUBLIC_STATIC_ENDPOINT_TYPES[endpoint]
    entity_prefix = PUBLIC_STATIC_ID_PREFIXES[endpoint]
    entity_id = f"{entity_prefix}:{payload['id']}"
    properties = {key: value for key, value in payload.items() if key not in {"id", "name"}}
    if evidence_id:
        properties["evidence_id"] = evidence_id
    return Entity(
        id=entity_id,
        type=entity_type,
        canonical_name=payload.get("name", f"{entity_type.value.title()} {payload['id']}"),
        graph_layer=GraphLayer.PUBLIC_GAME,
        external_id=str(payload["id"]),
        properties=properties,
    )


def _chunks(ids: list[int], chunk_size: int):
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive.")
    for index in range(0, len(ids), chunk_size):
        yield ids[index : index + chunk_size]
