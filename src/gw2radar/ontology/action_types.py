from enum import Enum


class ActionType(str, Enum):
    BUY = "buy"
    FARM = "farm"
    CRAFT = "craft"
    HOLD = "hold"
    RESERVE_FOR_GOAL = "reserve_for_goal"
    SELL_SURPLUS = "sell_surplus"
    DO_DAILY = "do_daily"
    DO_WEEKLY = "do_weekly"
    EXCHANGE = "exchange"
    COMPLETE_ACHIEVEMENT = "complete_achievement"
    COMPLETE_COLLECTION_STEP = "complete_collection_step"
    WATCH_PRICE = "watch_price"
    GENERATE_DAILY_PLAN = "generate_daily_plan"
    GENERATE_WEEKLY_PLAN = "generate_weekly_plan"
