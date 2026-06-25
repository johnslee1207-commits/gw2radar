from gw2radar.player_os.intent.intent_parser import parse_player_intent


def test_returner_text_routes_to_returner_with_goal_and_profession() -> None:
    parsed = parse_player_intent("我三年没玩了，想重新开始玩死灵，还想慢慢做 Aurora。")

    assert parsed.intent.intent_type == "returner"
    assert parsed.router_target == "returner_wizard"
    assert parsed.intent.goal_id == "gw2:goal:aurora"
    assert parsed.intent.profession == "Necromancer"
    assert parsed.intent.constraints["pace"] == "casual"


def test_legendary_text_extracts_cheap_and_avoid_wvw() -> None:
    parsed = parse_player_intent("I want to craft Aurora cheaply and avoid WvW.")

    assert parsed.intent.intent_type == "legendary"
    assert parsed.intent.goal_id == "gw2:goal:aurora"
    assert parsed.intent.constraints["spending_mode"] == "cheap"
    assert parsed.intent.constraints["avoid_modes"] == ["wvw"]


def test_build_text_extracts_reaper_budget_and_open_world() -> None:
    parsed = parse_player_intent("Can I play Open World Power Reaper with 50 gold?")

    assert parsed.intent.intent_type == "build_fit"
    assert parsed.intent.profession == "Necromancer"
    assert parsed.intent.specialization == "Reaper"
    assert parsed.intent.game_mode == "open_world"
    assert parsed.intent.constraints["budget_gold_limit"] == 50


def test_unknown_intent_asks_clarification() -> None:
    parsed = parse_player_intent("hello")

    assert parsed.intent.intent_type == "unknown"
    assert parsed.router_target == "clarify"
    assert parsed.clarifying_questions
