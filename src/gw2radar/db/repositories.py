from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from gw2radar.db.models import (
    ActionModel,
    EntityModel,
    EvidenceModel,
    PlayerStateModel,
    RelationModel,
)
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Action, Entity, Evidence, PlayerState, Relation


class GraphLayerViolation(ValueError):
    pass


class GraphRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_graph(self, graph: GraphData) -> None:
        validate_graph_layers(graph)
        for model in (ActionModel, PlayerStateModel, RelationModel, EvidenceModel, EntityModel):
            self.session.execute(delete(model))
        self.session.flush()

        self.session.add_all(_entity_to_model(entity) for entity in graph.entities.values())
        self.session.add_all(_evidence_to_model(evidence) for evidence in graph.evidence.values())
        self.session.add_all(_relation_to_model(relation) for relation in graph.relations)
        self.session.add_all(_player_state_to_model(state) for state in graph.player_state)
        self.session.add_all(_action_to_model(action) for action in graph.actions)
        self.session.commit()

    def load_graph(self) -> GraphData | None:
        entity_models = list(self.session.scalars(select(EntityModel)))
        if not entity_models:
            return None

        evidence_models = list(self.session.scalars(select(EvidenceModel)))
        relation_models = list(self.session.scalars(select(RelationModel)))
        player_state_models = list(self.session.scalars(select(PlayerStateModel)))
        action_models = list(self.session.scalars(select(ActionModel)))

        graph = GraphData()
        for model in entity_models:
            graph.add_entity(_model_to_entity(model))
            if model.type == EntityType.ACCOUNT.value:
                graph.account_id = model.id
        for model in evidence_models:
            graph.add_evidence(_model_to_evidence(model))
        for model in relation_models:
            graph.add_relation(_model_to_relation(model))
        for model in player_state_models:
            graph.add_player_state(_model_to_player_state(model))
            graph.account_id = graph.account_id or model.account_id
        graph.actions.extend(_model_to_action(model) for model in action_models)
        return graph

    def delete_account_snapshot(self) -> dict[str, int]:
        deleted_actions = self.session.query(ActionModel).filter(
            ActionModel.graph_layer == GraphLayer.PERSONAL_INTELLIGENCE.value
        ).delete(synchronize_session=False)
        deleted_player_state = self.session.query(PlayerStateModel).filter(
            PlayerStateModel.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE.value
        ).delete(synchronize_session=False)
        deleted_private_relations = self.session.query(RelationModel).filter(
            RelationModel.graph_layer.in_(
                [GraphLayer.PRIVATE_PLAYER_STATE.value, GraphLayer.PERSONAL_INTELLIGENCE.value]
            )
        ).delete(synchronize_session=False)
        deleted_private_entities = self.session.query(EntityModel).filter(
            EntityModel.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE.value
        ).delete(synchronize_session=False)
        self.session.commit()
        return {
            "actions": deleted_actions,
            "player_state": deleted_player_state,
            "relations": deleted_private_relations,
            "entities": deleted_private_entities,
        }


def validate_graph_layers(graph: GraphData) -> None:
    for state in graph.player_state:
        if state.graph_layer != GraphLayer.PRIVATE_PLAYER_STATE:
            raise GraphLayerViolation(
                f"Player state {state.id} must stay in private_player_state layer."
            )

    for entity in graph.entities.values():
        if entity.type == EntityType.ACCOUNT and entity.graph_layer != GraphLayer.PRIVATE_PLAYER_STATE:
            raise GraphLayerViolation(f"Account entity {entity.id} must stay private.")

    for relation in graph.relations:
        if relation.predicate == RelationType.OWNED_BY and relation.graph_layer != GraphLayer.PRIVATE_PLAYER_STATE:
            raise GraphLayerViolation(f"OWNED_BY relation {relation.id} must stay private.")
        if (
            relation.predicate in {RelationType.MISSING_FOR_GOAL, RelationType.ADVANCES_GOAL}
            and relation.graph_layer != GraphLayer.PERSONAL_INTELLIGENCE
        ):
            raise GraphLayerViolation(
                f"Derived intelligence relation {relation.id} must stay personal."
            )

    for action in graph.actions:
        if action.graph_layer != GraphLayer.PERSONAL_INTELLIGENCE:
            raise GraphLayerViolation(f"Action {action.id} must stay personal intelligence.")


def _entity_to_model(entity: Entity) -> EntityModel:
    return EntityModel(
        id=entity.id,
        type=entity.type.value,
        canonical_name=entity.canonical_name,
        graph_layer=entity.graph_layer.value,
        external_id=entity.external_id,
        properties_json=entity.properties,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _model_to_entity(model: EntityModel) -> Entity:
    return Entity(
        id=model.id,
        type=EntityType(model.type),
        canonical_name=model.canonical_name,
        graph_layer=GraphLayer(model.graph_layer),
        external_id=model.external_id,
        properties=model.properties_json or {},
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _relation_to_model(relation: Relation) -> RelationModel:
    return RelationModel(
        id=relation.id,
        subject_id=relation.subject_id,
        predicate=relation.predicate.value,
        object_id=relation.object_id,
        graph_layer=relation.graph_layer.value,
        properties_json=relation.properties,
        evidence_id=relation.evidence_id,
        confidence=relation.confidence,
        valid_from=relation.valid_from,
        valid_to=relation.valid_to,
        created_at=relation.created_at,
    )


def _model_to_relation(model: RelationModel) -> Relation:
    return Relation(
        id=model.id,
        subject_id=model.subject_id,
        predicate=RelationType(model.predicate),
        object_id=model.object_id,
        graph_layer=GraphLayer(model.graph_layer),
        properties=model.properties_json or {},
        evidence_id=model.evidence_id,
        confidence=model.confidence,
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        created_at=model.created_at,
    )


def _evidence_to_model(evidence: Evidence) -> EvidenceModel:
    return EvidenceModel(
        id=evidence.id,
        source=evidence.source,
        graph_layer=evidence.graph_layer.value,
        source_type=evidence.source_type,
        source_url=evidence.source_url,
        fetched_at=evidence.fetched_at,
        raw_hash=evidence.raw_hash,
        raw_payload=evidence.raw_payload,
        payload_ref=evidence.payload_ref,
        confidence=evidence.confidence,
        license_note=evidence.license_note,
    )


def _model_to_evidence(model: EvidenceModel) -> Evidence:
    return Evidence(
        id=model.id,
        source=model.source,
        graph_layer=GraphLayer(model.graph_layer),
        source_type=model.source_type,
        source_url=model.source_url,
        fetched_at=model.fetched_at,
        raw_hash=model.raw_hash,
        raw_payload=model.raw_payload,
        payload_ref=model.payload_ref,
        confidence=model.confidence,
        license_note=model.license_note,
    )


def _player_state_to_model(state: PlayerState) -> PlayerStateModel:
    return PlayerStateModel(
        id=state.id,
        account_id=state.account_id,
        entity_id=state.entity_id,
        graph_layer=state.graph_layer.value,
        quantity=state.quantity,
        location=state.location,
        observed_at=state.observed_at,
    )


def _model_to_player_state(model: PlayerStateModel) -> PlayerState:
    return PlayerState(
        id=model.id,
        account_id=model.account_id,
        entity_id=model.entity_id,
        graph_layer=GraphLayer(model.graph_layer),
        quantity=model.quantity,
        location=model.location,
        observed_at=model.observed_at,
    )


def _action_to_model(action: Action) -> ActionModel:
    properties = dict(action.properties)
    properties["_preconditions"] = action.preconditions
    properties["_expected_outputs"] = action.expected_outputs
    properties["_costs"] = action.costs
    properties["_constraints"] = action.constraints
    properties["_reason_codes"] = action.reason_codes
    properties["_evidence_refs"] = action.evidence_refs
    return ActionModel(
        id=action.id,
        action_type=action.action_type.value,
        title=action.title,
        graph_layer=action.graph_layer.value,
        description=action.description,
        target_entity_id=action.target_entity_id,
        target_goal_id=action.target_goal_id,
        priority_score=action.priority_score,
        urgency=action.urgency,
        properties_json=properties,
        explanation=action.explanation,
        created_at=action.created_at,
    )


def _model_to_action(model: ActionModel) -> Action:
    return Action(
        id=model.id,
        action_type=ActionType(model.action_type),
        title=model.title,
        graph_layer=GraphLayer(model.graph_layer),
        description=model.description,
        target_entity_id=model.target_entity_id,
        target_goal_id=model.target_goal_id,
        priority_score=model.priority_score,
        urgency=model.urgency,
        preconditions=(model.properties_json or {}).get("_preconditions", []),
        expected_outputs=(model.properties_json or {}).get("_expected_outputs", []),
        costs=(model.properties_json or {}).get("_costs", {}),
        constraints=(model.properties_json or {}).get("_constraints", {}),
        reason_codes=(model.properties_json or {}).get("_reason_codes", []),
        evidence_refs=(model.properties_json or {}).get("_evidence_refs", []),
        properties=model.properties_json or {},
        explanation=model.explanation,
        created_at=model.created_at,
    )
