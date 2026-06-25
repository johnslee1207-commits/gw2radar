from __future__ import annotations

import re
from typing import Any

from gw2radar.player_os.intent.models import PlayerConstraint


PROFESSION_ALIASES = {
    "necromancer": "Necromancer",
    "necro": "Necromancer",
    "死灵": "Necromancer",
    "reaper": "Necromancer",
    "guardian": "Guardian",
    "守护": "Guardian",
    "mesmer": "Mesmer",
    "幻术": "Mesmer",
}

SPECIALIZATION_ALIASES = {
    "reaper": "Reaper",
    "收割": "Reaper",
    "harbinger": "Harbinger",
    "scourge": "Scourge",
    "dragonhunter": "Dragonhunter",
    "firebrand": "Firebrand",
    "virtuoso": "Virtuoso",
}


def extract_constraints(raw_text: str | None, intent_id: str) -> list[PlayerConstraint]:
    text = (raw_text or "").strip()
    lowered = text.lower()
    constraints: dict[str, tuple[Any, float]] = {}

    if any(token in lowered or token in text for token in ("cheap", "少花", "省钱", "不想花金币")):
        constraints["spending_mode"] = ("cheap", 0.92)
        constraints["prefer_farming"] = (True, 0.86)
    if any(token in lowered or token in text for token in ("fast", "更快", "尽快")):
        constraints["spending_mode"] = ("fast", 0.78)
    if any(token in lowered or token in text for token in ("casual", "慢慢", "休闲")):
        constraints["pace"] = ("casual", 0.85)
    if any(token in lowered or token in text for token in ("open world", "open-world", "开放世界")):
        constraints["game_mode"] = ("open_world", 0.92)
        constraints["preferred_modes"] = (["open_world"], 0.82)
    if any(token in lowered or token in text for token in ("wvw", "世界之战")) and any(
        token in lowered or token in text for token in ("avoid", "no ", "不想", "不要", "排除")
    ):
        constraints["avoid_modes"] = (["wvw"], 0.9)
    if any(token in lowered or token in text for token in ("do not sell", "don't sell", "不能卖", "不要卖")):
        constraints["conservative_sell_policy"] = (True, 0.94)

    budget = re.search(r"(\d+)\s*(?:g|gold|金币|金)", lowered)
    if budget:
        constraints["budget_gold_limit"] = (int(budget.group(1)), 0.9)

    minutes = re.search(r"(\d+)\s*(?:m|min|minute|minutes|分钟)", lowered)
    if minutes:
        constraints["daily_time_limit"] = (f"{int(minutes.group(1))}m", 0.9)
    elif "30" in lowered and any(token in lowered or token in text for token in ("daily", "每天", "per day")):
        constraints["daily_time_limit"] = ("30m", 0.72)

    if "aurora" in lowered or "欧若拉" in text:
        constraints["goal_id"] = ("gw2:goal:aurora", 0.96)
    if "vision" in lowered:
        constraints["goal_id"] = ("gw2:goal:vision", 0.72)

    for token, profession in PROFESSION_ALIASES.items():
        if token in lowered or token in text:
            constraints["preferred_profession"] = (profession, 0.82)
            constraints["profession"] = (profession, 0.82)
            break
    for token, specialization in SPECIALIZATION_ALIASES.items():
        if token in lowered or token in text:
            constraints["specialization"] = (specialization, 0.9)
            break

    return [
        PlayerConstraint(
            constraint_id=f"{intent_id}:{key}",
            intent_id=intent_id,
            key=key,
            value=value,
            source="user_text",
            confidence=confidence,
        )
        for key, (value, confidence) in sorted(constraints.items())
    ]


def constraints_to_dict(constraints: list[PlayerConstraint]) -> dict[str, Any]:
    return {constraint.key: constraint.value for constraint in constraints}
