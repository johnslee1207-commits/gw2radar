from dataclasses import dataclass, field

from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.schemas import Action, Entity, Evidence, PlayerState, Relation


@dataclass
class GraphData:
    entities: dict[str, Entity] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    player_state: list[PlayerState] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    account_id: str | None = None

    def add_entity(self, entity: Entity) -> Entity:
        self.entities[entity.id] = entity
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        self.relations.append(relation)
        return relation

    def add_evidence(self, evidence: Evidence) -> Evidence:
        self.evidence[evidence.id] = evidence
        return evidence

    def add_player_state(self, state: PlayerState) -> PlayerState:
        self.player_state.append(state)
        return state

    def replace_actions_for_goal(self, goal_id: str, actions: list[Action]) -> None:
        self.actions = [action for action in self.actions if action.target_goal_id != goal_id]
        self.actions.extend(actions)

    def goals(self) -> list[Entity]:
        return [entity for entity in self.entities.values() if entity.type.value == "goal"]

    def entity_name(self, entity_id: str) -> str:
        entity = self.entities.get(entity_id)
        return entity.canonical_name if entity else entity_id

    def quantity_owned(self, entity_id: str) -> float:
        return sum(state.quantity for state in self.player_state if state.entity_id == entity_id)

    def actions_for_goal(self, goal_id: str) -> list[Action]:
        return [action for action in self.actions if action.target_goal_id == goal_id]

    def actions_by_type(self, action_type: ActionType) -> list[Action]:
        return [action for action in self.actions if action.action_type == action_type]
