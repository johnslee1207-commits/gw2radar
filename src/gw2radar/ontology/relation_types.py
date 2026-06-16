from enum import Enum


class RelationType(str, Enum):
    REQUIRES = "requires"
    CONSUMES = "consumes"
    PRODUCES = "produces"
    USED_IN = "used_in"
    UNLOCKS = "unlocks"
    PART_OF = "part_of"
    OWNED_BY = "owned_by"
    HAS_PRICE = "has_price"
    MISSING_FOR_GOAL = "missing_for_goal"
    ADVANCES_GOAL = "advances_goal"
    BLOCKS_GOAL = "blocks_goal"
    RESERVES_FOR_GOAL = "reserves_for_goal"
    RESERVED_FOR_GOAL = "reserved_for_goal"
    ACQUIRED_BY = "acquired_by"
