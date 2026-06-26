from dataclasses import dataclass, field
from typing import Sequence

from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Action, Entity, Evidence, PlayerState, Relation


@dataclass
class GraphData:
    entities: dict[str, Entity] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)
    evidence: dict[str, Evidence] = field(default_factory=dict)
    player_state: list[PlayerState] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    account_id: str | None = None

    _predicate_index: dict[str, list[Relation]] = field(default_factory=dict)
    _subject_index: dict[str, list[Relation]] = field(default_factory=dict)
    _object_index: dict[str, list[Relation]] = field(default_factory=dict)

    def _rebuild_index(self) -> None:
        self._predicate_index.clear()
        self._subject_index.clear()
        self._object_index.clear()
        for r in self.relations:
            self._predicate_index.setdefault(r.predicate.value, []).append(r)
            self._subject_index.setdefault(r.subject_id, []).append(r)
            self._object_index.setdefault(r.object_id, []).append(r)

    def add_entity(self, entity: Entity) -> Entity:
        self.entities[entity.id] = entity
        return entity

    def add_relation(self, relation: Relation) -> Relation:
        for index, existing in enumerate(self.relations):
            if existing.id == relation.id:
                self.relations[index] = relation
                self._rebuild_index()
                return relation
        self.relations.append(relation)
        self._predicate_index.setdefault(relation.predicate.value, []).append(relation)
        self._subject_index.setdefault(relation.subject_id, []).append(relation)
        self._object_index.setdefault(relation.object_id, []).append(relation)
        return relation

    def add_evidence(self, evidence: Evidence) -> Evidence:
        self.evidence[evidence.id] = evidence
        return evidence

    def add_player_state(self, state: PlayerState) -> PlayerState:
        for index, existing in enumerate(self.player_state):
            if existing.id == state.id:
                self.player_state[index] = state
                return state
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

    def find_relations(
        self,
        *,
        subject_id: str | None = None,
        predicate: RelationType | str | None = None,
        object_id: str | None = None,
    ) -> list[Relation]:
        candidates: Sequence[Relation]
        if predicate:
            pred_key = predicate.value if isinstance(predicate, RelationType) else predicate
            candidates = self._predicate_index.get(pred_key, [])
        elif subject_id:
            candidates = self._subject_index.get(subject_id, [])
        elif object_id:
            candidates = self._object_index.get(object_id, [])
        else:
            candidates = self.relations
        result = list(candidates)
        if subject_id is not None:
            result = [r for r in result if r.subject_id == subject_id]
        if predicate is not None:
            pred_key = predicate.value if isinstance(predicate, RelationType) else predicate
            result = [r for r in result if r.predicate.value == pred_key]
        if object_id is not None:
            result = [r for r in result if r.object_id == object_id]
        return result

    def find_entities_by_relation(
        self,
        *,
        subject_id: str | None = None,
        predicate: RelationType | str | None = None,
        object_id: str | None = None,
    ) -> list[Entity]:
        matched = self.find_relations(subject_id=subject_id, predicate=predicate, object_id=object_id)
        ids: set[str] = set()
        for r in matched:
            if subject_id is None and object_id is None:
                ids.add(r.subject_id)
                ids.add(r.object_id)
            elif subject_id is not None:
                ids.add(r.object_id)
            elif object_id is not None:
                ids.add(r.subject_id)
            else:
                ids.add(r.subject_id)
                ids.add(r.object_id)
        return [self.entities[eid] for eid in ids if eid in self.entities]

    def find_actions(
        self,
        *,
        goal_id: str | None = None,
        action_type: ActionType | str | None = None,
    ) -> list[Action]:
        result = self.actions
        if goal_id is not None:
            result = [a for a in result if a.target_goal_id == goal_id]
        if action_type is not None:
            at_key = action_type.value if isinstance(action_type, ActionType) else action_type
            result = [a for a in result if a.action_type.value == at_key]
        return result
