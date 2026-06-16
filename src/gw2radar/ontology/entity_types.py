from enum import Enum


class EntityType(str, Enum):
    ACCOUNT = "account"
    CHARACTER = "character"
    GOAL = "goal"
    ITEM = "item"
    MATERIAL = "material"
    CURRENCY = "currency"
    RECIPE = "recipe"
    ACHIEVEMENT = "achievement"
    COLLECTION = "collection"
    TASK = "task"
    ACTION = "action"
    TRADING_POST_PRICE = "trading_post_price"
    SOURCE = "source"
    EVIDENCE = "evidence"
