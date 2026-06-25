from __future__ import annotations

from gw2radar.player_os.intent.models import IntentTemplate


_TEMPLATES = [
    IntentTemplate(
        template_id="returner.long_break_open_world",
        name="I am returning after a long break",
        domain="returner",
        description="Recover your account and get a safe 7-day open-world plan.",
        default_intent_type="returner",
        default_constraints={
            "pace": "casual",
            "preferred_modes": ["open_world"],
            "conservative_sell_policy": True,
        },
        required_permissions=["account", "characters", "inventories", "wallet", "progression"],
        recommended_next_questions=[
            "How long have you been away?",
            "Which game mode do you want to return to?",
            "Do you have a preferred profession?",
        ],
    ),
    IntentTemplate(
        template_id="returner.casual_legendary_start",
        name="Return and start a legendary slowly",
        domain="returner",
        description="Blend returner recovery with conservative legendary progress.",
        default_intent_type="returner",
        default_constraints={
            "pace": "casual",
            "goal_id": "gw2:goal:aurora",
            "conservative_sell_policy": True,
        },
        required_permissions=["account", "characters", "inventories", "wallet", "progression"],
        recommended_next_questions=[
            "Which legendary are you considering?",
            "How much time can you play each day?",
        ],
    ),
    IntentTemplate(
        template_id="legendary.aurora_cheap_path",
        name="Aurora Cheap Path",
        domain="legendary",
        description="Plan Aurora with minimum gold spending.",
        default_intent_type="legendary",
        default_constraints={
            "goal_id": "gw2:goal:aurora",
            "spending_mode": "cheap",
            "prefer_farming": True,
            "conservative_sell_policy": True,
        },
        required_permissions=["account", "inventories", "wallet", "progression"],
        recommended_next_questions=[
            "How much gold are you willing to spend?",
            "Do you want to avoid WvW or group content?",
        ],
    ),
    IntentTemplate(
        template_id="legendary.aurora_balanced_path",
        name="Aurora Balanced Path",
        domain="legendary",
        description="Balance time, gold, and do-not-sell protection for Aurora.",
        default_intent_type="legendary",
        default_constraints={
            "goal_id": "gw2:goal:aurora",
            "spending_mode": "balanced",
            "conservative_sell_policy": True,
        },
        required_permissions=["account", "inventories", "wallet", "progression"],
        recommended_next_questions=["Do you prefer fast progress or low gold spending?"],
    ),
    IntentTemplate(
        template_id="build.open_world_low_budget",
        name="Open World Low Budget Build",
        domain="build_fit",
        description="Check whether your account can play a low-cost open-world build.",
        default_intent_type="build_fit",
        default_constraints={
            "game_mode": "open_world",
            "budget_gold_limit": 50,
            "prefer_budget_alternative": True,
        },
        required_permissions=["characters", "inventories", "builds"],
        recommended_next_questions=[
            "Which profession do you want to play?",
            "Do you want a low-cost or optimized build?",
        ],
    ),
    IntentTemplate(
        template_id="account.what_should_i_do_now",
        name="What should I do now?",
        domain="account",
        description="Generate the top current actions from account readiness, goals, and evidence.",
        default_intent_type="what_should_i_do_now",
        default_constraints={"daily_time_limit": "30m", "conservative_sell_policy": True},
        required_permissions=["account", "characters", "inventories", "wallet", "progression"],
        recommended_next_questions=["How much time do you have today?"],
    ),
    IntentTemplate(
        template_id="account.do_not_sell_check",
        name="Do-not-sell check",
        domain="account",
        description="Protect account materials that are likely needed for active goals.",
        default_intent_type="legendary",
        default_constraints={"conservative_sell_policy": True, "goal_id": "gw2:goal:aurora"},
        required_permissions=["account", "inventories", "wallet", "progression"],
        recommended_next_questions=["Which goal should be protected?"],
    ),
    IntentTemplate(
        template_id="market.goal_watch",
        name="Goal cost and market watch",
        domain="market",
        description="Review goal cost signals without automated trading or profit claims.",
        default_intent_type="market_watch",
        default_constraints={"goal_id": "gw2:goal:aurora", "no_automated_trading": True},
        required_permissions=["account", "inventories", "wallet"],
        recommended_next_questions=["Which goal or item should be watched?"],
    ),
]


def list_intent_templates() -> list[IntentTemplate]:
    return [template.model_copy(deep=True) for template in _TEMPLATES if template.enabled]


def get_intent_template(template_id: str) -> IntentTemplate | None:
    for template in _TEMPLATES:
        if template.template_id == template_id and template.enabled:
            return template.model_copy(deep=True)
    return None
