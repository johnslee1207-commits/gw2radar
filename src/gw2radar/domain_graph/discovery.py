"""Auto-discover DomainGraph from existing ontology enum definitions."""

from gw2radar.domain_graph.domain_schema import (
    DomainGraph,
    DomainRule,
    EdgeDef,
    NodeDef,
    NodeProperty,
)
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType


def discover_from_enums(domain_name: str = "GW2Radar") -> DomainGraph:
    dg = DomainGraph(
        domain=domain_name,
        version="1.0",
        description=f"Auto-discovered from existing ontology enums",
    )
    for et in EntityType:
        clean_name = et.value.replace("_", " ").title().replace(" ", "")
        props = []
        if et == EntityType.ACCOUNT:
            props = [
                NodeProperty(name="id", prop_type="string", required=True),
                NodeProperty(name="name", prop_type="string"),
            ]
        elif et == EntityType.ITEM:
            props = [
                NodeProperty(name="id", prop_type="string", required=True),
                NodeProperty(name="name", prop_type="string"),
                NodeProperty(name="tradable", prop_type="bool"),
            ]
        elif et == EntityType.GOAL:
            props = [
                NodeProperty(name="id", prop_type="string", required=True),
                NodeProperty(name="goal_type", prop_type="string"),
            ]
        else:
            props = [NodeProperty(name="id", prop_type="string", required=True)]

        dg.nodes[clean_name] = NodeDef(
            type=clean_name,
            description=f"Entity type: {et.value}",
            properties=props,
        )

    for rt in RelationType:
        clean_name = rt.value.replace("_", " ").title().replace(" ", "")
        dg.edges[clean_name] = EdgeDef(
            type=clean_name,
            description=f"Relation type: {rt.value}",
            cardinality="N:N",
        )

    dg.rules = [
        DomainRule(
            name="data_freshness_required",
            description="Entities must have fresh data for decisions",
            rule="Entity.freshness must be fresh",
            severity="error",
        ),
        DomainRule(
            name="evidence_chain_required",
            description="Decisions require intact evidence chain",
            rule="Decision requires Evidence",
            severity="error",
        ),
        DomainRule(
            name="private_data_protected",
            description="Private player data must not leak to public layer",
            rule="Entity.layer must not be public",
            severity="error",
        ),
    ]

    return dg


def discover_graph_layers() -> list[dict]:
    return [
        {"name": layer.value, "description": layer.name.replace("_", " ").title()}
        for layer in GraphLayer
    ]
