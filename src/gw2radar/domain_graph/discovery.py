"""Auto-discover DomainGraph from existing ontology enum definitions."""

from gw2radar.domain_graph.domain_schema import (
    DomainGraph,
    DomainRule,
    EdgeDef,
    NodeDef,
    NodeProperty,
    StateMachine,
    StateTransition,
    TypeAlias,
)
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType


def discover_from_enums(domain_name: str = "GW2Radar") -> DomainGraph:
    dg = DomainGraph(
        domain=domain_name,
        version="1.0",
        description="Auto-discovered from existing ontology enums",
    )
    for et in EntityType:
        clean_name = _clean(et.value)
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

        if et == EntityType.ACCOUNT:
            nd = NodeDef(
                type=clean_name,
                description="Player account entity",
                properties=props,
                lifecycle=StateMachine(
                    states=["active", "frozen", "closed"],
                    initial_state="active",
                    transitions=[
                        StateTransition(from_state="active", to_state="frozen", trigger="freeze"),
                        StateTransition(from_state="frozen", to_state="active", trigger="unfreeze"),
                        StateTransition(from_state="active", to_state="closed", trigger="close"),
                    ],
                    invariants=["closed is terminal"],
                ),
            )
        else:
            nd = NodeDef(
                type=clean_name,
                description=f"Entity type: {et.value}",
                properties=props,
            )
        dg.nodes[clean_name] = nd

    for rt in RelationType:
        clean_name = _clean(rt.value)
        dg.edges[clean_name] = EdgeDef(
            type=clean_name,
            description=f"Relation type: {rt.value}",
            cardinality="N:N",
        )

    dg.type_aliases = [
        TypeAlias(local_type="Action", equivalent_to="Task",
                  source_domain="GW2Radar", confidence=0.85),
    ]

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


def _clean(v: str) -> str:
    return v.replace("_", " ").title().replace(" ", "")


def discover_graph_layers() -> list[dict]:
    return [
        {"name": layer.value, "description": layer.name.replace("_", " ").title()}
        for layer in GraphLayer
    ]
