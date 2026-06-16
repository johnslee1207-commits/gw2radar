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
    COMPLETE_ACHIEVEMENT = "complete_achievement"
    WATCH_PRICE = "watch_price"
    GENERATE_DAILY_PLAN = "generate_daily_plan"
    GENERATE_WEEKLY_PLAN = "generate_weekly_plan"
