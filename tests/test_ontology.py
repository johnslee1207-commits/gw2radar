from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.relation_types import RelationType


def test_entity_type_contains_required_values() -> None:
    assert EntityType.GOAL
    assert EntityType.ITEM
    assert EntityType.CURRENCY
    assert EntityType.ACTION


def test_relation_type_contains_required_values() -> None:
    assert RelationType.REQUIRES
    assert RelationType.MISSING_FOR_GOAL
    assert RelationType.ADVANCES_GOAL


def test_action_type_contains_required_values() -> None:
    assert ActionType.HOLD
    assert ActionType.BUY
    assert ActionType.FARM
    assert ActionType.DO_DAILY
