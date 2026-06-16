from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(BaseModel):
    id: str
    source: str
    graph_layer: GraphLayer = GraphLayer.PUBLIC_GAME
    source_type: str = "mock"
    source_url: str | None = None
    fetched_at: datetime = Field(default_factory=utc_now)
    raw_hash: str | None = None
    raw_payload: dict[str, Any] | None = None
    payload_ref: str | None = None
    confidence: float = 1.0
    license_note: str | None = None


class Entity(BaseModel):
    id: str
    type: EntityType
    canonical_name: str
    graph_layer: GraphLayer = GraphLayer.PUBLIC_GAME
    external_id: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Relation(BaseModel):
    id: str
    subject_id: str
    predicate: RelationType
    object_id: str
    graph_layer: GraphLayer = GraphLayer.PUBLIC_GAME
    properties: dict[str, Any] = Field(default_factory=dict)
    evidence_id: str | None = None
    confidence: float = 1.0
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)


class PlayerState(BaseModel):
    id: str
    account_id: str
    entity_id: str
    graph_layer: GraphLayer = GraphLayer.PRIVATE_PLAYER_STATE
    quantity: float
    location: str | None = None
    observed_at: datetime = Field(default_factory=utc_now)


class Action(BaseModel):
    id: str
    action_type: ActionType
    title: str
    graph_layer: GraphLayer = GraphLayer.PERSONAL_INTELLIGENCE
    description: str | None = None
    target_entity_id: str | None = None
    target_goal_id: str | None = None
    preconditions: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    costs: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    priority_score: float
    urgency: str
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    explanation: str
    created_at: datetime = Field(default_factory=utc_now)


class GoalRequirement(BaseModel):
    entity_id: str
    type: EntityType
    required_quantity: float


class GoalGapItem(BaseModel):
    entity_id: str
    name: str
    entity_type: EntityType
    required_quantity: float
    owned_quantity: float
    missing_quantity: float
    completed: bool


class GoalGapResult(BaseModel):
    goal_id: str
    goal_name: str
    progress_percent: float
    completed_requirements: list[GoalGapItem]
    missing_requirements: list[GoalGapItem]
    surplus_quantities: dict[str, float]
