from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, Evidence, FreshnessStatus, ObjectRef, QAStatus, Relation, ReviewStatus


def test_find_relations_by_predicate() -> None:
    graph = build_mock_graph()
    requires = graph.find_relations(predicate=RelationType.REQUIRES)
    assert len(requires) > 0
    for r in requires:
        assert r.predicate == RelationType.REQUIRES


def test_find_relations_by_subject() -> None:
    graph = build_mock_graph()
    goal = graph.goals()[0]
    goal_rels = graph.find_relations(subject_id=goal.id)
    assert len(goal_rels) > 0
    for r in goal_rels:
        assert r.subject_id == goal.id


def test_find_relations_by_subject_and_predicate() -> None:
    graph = build_mock_graph()
    goal = graph.goals()[0]
    requires = graph.find_relations(subject_id=goal.id, predicate=RelationType.REQUIRES)
    assert len(requires) > 0
    for r in requires:
        assert r.subject_id == goal.id
        assert r.predicate == RelationType.REQUIRES


def test_find_entities_by_relation() -> None:
    graph = build_mock_graph()
    goal = graph.goals()[0]
    required = graph.find_entities_by_relation(subject_id=goal.id, predicate=RelationType.REQUIRES)
    assert len(required) > 0
    for entity in required:
        assert entity.id in graph.entities


def test_find_actions_by_goal_and_type() -> None:
    graph = build_mock_graph()
    goal = graph.goals()[0]
    actions = graph.actions_for_goal(goal.id)
    if actions:
        at = actions[0].action_type
        found = graph.find_actions(goal_id=goal.id, action_type=at)
        assert len(found) > 0
        for a in found:
            assert a.target_goal_id == goal.id
            assert a.action_type == at


def test_entity_governance_fields_have_defaults() -> None:
    entity = Entity(
        id="gw2:item:test",
        type="item",
        canonical_name="Test Item",
    )
    assert entity.freshness_status == FreshnessStatus.UNKNOWN
    assert entity.review_status == ReviewStatus.PENDING
    assert entity.qa_status == QAStatus.UNTESTED
    assert entity.source_refs == []


def test_object_ref_round_trip() -> None:
    ref = ObjectRef(source="official_api", ref_id="gw2:item:123", privacy_scope="public")
    assert ref.source == "official_api"
    assert ref.ref_id == "gw2:item:123"
    assert ref.privacy_scope == "public"


def test_mock_graph_entities_have_governance_fields() -> None:
    graph = build_mock_graph()
    for eid, entity in graph.entities.items():
        assert entity.freshness_status is not None
        assert entity.review_status is not None
        assert entity.qa_status is not None


def test_relation_index_is_populated() -> None:
    graph = build_mock_graph()
    assert len(graph._predicate_index) > 0
    assert len(graph._subject_index) > 0
    assert len(graph._object_index) > 0
    total_indexed = sum(len(v) for v in graph._predicate_index.values())
    assert total_indexed == len(graph.relations)


def test_relation_index_survives_add_relation() -> None:
    graph = build_mock_graph()
    count_before = len(graph.relations)
    graph.add_relation(
        Relation(
            id="rel:test:999",
            subject_id="gw2:item:test",
            predicate=RelationType.REQUIRES,
            object_id="gw2:goal:test",
        )
    )
    assert len(graph.relations) == count_before + 1
    found = graph.find_relations(predicate=RelationType.REQUIRES, subject_id="gw2:item:test")
    assert len(found) == 1
    assert found[0].id == "rel:test:999"


def test_relation_index_survives_upsert() -> None:
    graph = build_mock_graph()
    first = graph.relations[0]
    updated = first.model_copy(update={"object_id": "updated:entity"})
    graph.add_relation(updated)
    assert updated.id in {r.id for r in graph.relations}
    found = graph.find_relations(object_id="updated:entity")
    assert len(found) == 1
