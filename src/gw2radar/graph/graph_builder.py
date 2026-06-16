from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.mock_loader import load_mock_bundle
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, Evidence, PlayerState, Relation


def build_mock_graph() -> GraphData:
    bundle = load_mock_bundle()
    graph = GraphData(account_id=bundle["account"]["account_id"])
    evidence = Evidence(
        id="mock:evidence:mvp_0_1",
        source="mock_fixture",
        source_type="mock",
        raw_payload=bundle,
        payload_ref="src/gw2radar/fixtures",
        confidence=1.0,
        license_note="Mock fixture data for deterministic MVP tests.",
    )
    graph.add_evidence(evidence)

    account = bundle["account"]
    graph.add_entity(
        Entity(
            id=account["account_id"],
            type=EntityType.ACCOUNT,
            canonical_name="Mock Account Lee",
            properties={"wallet_gold": account["wallet_gold"]},
        )
    )

    _add_items(graph, bundle["items"])
    _add_goal(graph, bundle["goal"], evidence.id)
    _add_account_state(graph, account, evidence.id)
    _add_tasks(graph, bundle["tasks"], evidence.id)
    return graph


def _add_items(graph: GraphData, items: list[dict],) -> None:
    for item in items:
        entity_type = EntityType(item["type"])
        graph.add_entity(
            Entity(
                id=item["entity_id"],
                type=entity_type,
                canonical_name=item["name"],
                properties={
                    "tradable": item.get("tradable", False),
                    "legendary_related": item.get("legendary_related", False),
                },
            )
        )


def _add_goal(graph: GraphData, goal: dict, evidence_id: str) -> None:
    graph.add_entity(
        Entity(
            id=goal["goal_id"],
            type=EntityType.GOAL,
            canonical_name=goal["name"],
            properties={
                "goal_type": goal["goal_type"],
                "requirements": goal["requirements"],
            },
        )
    )
    for req in goal["requirements"]:
        graph.add_relation(
            Relation(
                id=f"rel:{goal['goal_id']}:requires:{req['entity_id']}",
                subject_id=goal["goal_id"],
                predicate=RelationType.REQUIRES,
                object_id=req["entity_id"],
                properties={
                    "required_quantity": req["required_quantity"],
                    "requirement_type": req["type"],
                },
                evidence_id=evidence_id,
            )
        )


def _add_account_state(graph: GraphData, account: dict, evidence_id: str) -> None:
    for location, values in (
        ("materials", account.get("materials", {})),
        ("currencies", account.get("currencies", {})),
        ("achievements", account.get("achievements", {})),
    ):
        for entity_id, quantity in values.items():
            graph.add_player_state(
                PlayerState(
                    id=f"state:{account['account_id']}:{entity_id}",
                    account_id=account["account_id"],
                    entity_id=entity_id,
                    quantity=float(quantity),
                    location=location,
                )
            )
            graph.add_relation(
                Relation(
                    id=f"rel:{account['account_id']}:owns:{entity_id}",
                    subject_id=account["account_id"],
                    predicate=RelationType.OWNED_BY,
                    object_id=entity_id,
                    properties={"quantity": quantity, "location": location},
                    evidence_id=evidence_id,
                )
            )


def _add_tasks(graph: GraphData, tasks: list[dict], evidence_id: str) -> None:
    for task in tasks:
        graph.add_entity(
            Entity(
                id=task["task_id"],
                type=EntityType.TASK,
                canonical_name=task["name"],
                properties={
                    "action_type": ActionType(task["action_type"]).value,
                    "estimated_minutes": task["estimated_minutes"],
                    "repeatability": task["repeatability"],
                    "requires_group": task["requires_group"],
                    "produces": task["produces"],
                },
            )
        )
        for produced in task["produces"]:
            graph.add_relation(
                Relation(
                    id=f"rel:{task['task_id']}:produces:{produced['entity_id']}",
                    subject_id=task["task_id"],
                    predicate=RelationType.PRODUCES,
                    object_id=produced["entity_id"],
                    properties={"estimated_quantity": produced["estimated_quantity"]},
                    evidence_id=evidence_id,
                )
            )
