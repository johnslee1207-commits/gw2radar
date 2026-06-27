from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropertyConstraint:
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None


@dataclass
class NodeProperty:
    name: str
    prop_type: str = "string"
    required: bool = False
    default: Any = None
    enum_values: list[str] | None = None
    constraints: PropertyConstraint | None = None


@dataclass
class StateTransition:
    from_state: str
    to_state: str
    trigger: str = ""
    guard: str = ""


@dataclass
class StateMachine:
    states: list[str] = field(default_factory=list)
    transitions: list[StateTransition] = field(default_factory=list)
    invariants: list[str] = field(default_factory=list)
    initial_state: str = ""


@dataclass
class NodeDef:
    type: str
    description: str = ""
    properties: list[NodeProperty] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    lifecycle: StateMachine | None = None


@dataclass
class EdgeDef:
    type: str
    description: str = ""
    source_types: list[str] = field(default_factory=list)
    target_types: list[str] = field(default_factory=list)
    cardinality: str = "N:N"


@dataclass
class DomainEvent:
    name: str
    description: str = ""
    source: str = ""
    triggers: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass
class DomainRule:
    name: str
    description: str = ""
    rule: str = ""
    severity: str = "info"


@dataclass
class TypeAlias:
    local_type: str
    equivalent_to: str
    source_domain: str = ""
    confidence: float = 1.0


@dataclass
class SchemaDiff:
    added_nodes: list[str] = field(default_factory=list)
    removed_nodes: list[str] = field(default_factory=list)
    added_edges: list[str] = field(default_factory=list)
    removed_edges: list[str] = field(default_factory=list)
    changed_properties: list[dict] = field(default_factory=list)
    backward_compatible: bool = True
    breaking_changes: list[str] = field(default_factory=list)


@dataclass
class DomainGraph:
    domain: str = ""
    version: str = "1.0"
    description: str = ""
    nodes: dict[str, NodeDef] = field(default_factory=dict)
    edges: dict[str, EdgeDef] = field(default_factory=dict)
    events: list[DomainEvent] = field(default_factory=list)
    rules: list[DomainRule] = field(default_factory=list)
    type_aliases: list[TypeAlias] = field(default_factory=list)


@dataclass
class OOSKTypeRegistry:
    domain_types: list[str] = field(default_factory=list)
    evidence_types: list[str] = field(default_factory=list)
    relation_types: list[str] = field(default_factory=list)
    action_types: dict[str, dict] = field(default_factory=dict)
    constraint_rules: list[dict] = field(default_factory=list)


@dataclass
class BusinessEntityMapping:
    domain_type: str
    bors_type: str = ""
    properties: list[str] = field(default_factory=list)
