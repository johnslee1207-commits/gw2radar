from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.relation_types import RelationType


def test_entity_type_contains_required_values() -> None:
    assert EntityType.GOAL
    assert EntityType.ITEM
    assert EntityType.CURRENCY
    assert EntityType.RECIPE
    assert EntityType.ACTION


def test_relation_type_contains_required_values() -> None:
    assert RelationType.REQUIRES
    assert RelationType.MISSING_FOR_GOAL
    assert RelationType.ADVANCES_GOAL
    assert RelationType.UNLOCKS
    assert RelationType.PART_OF
    assert RelationType.RESERVED_FOR_GOAL


def test_action_type_contains_required_values() -> None:
    assert ActionType.HOLD
    assert ActionType.BUY
    assert ActionType.FARM
    assert ActionType.DO_DAILY
    assert ActionType.EXCHANGE
    assert ActionType.COMPLETE_COLLECTION_STEP
