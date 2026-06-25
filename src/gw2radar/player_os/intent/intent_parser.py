from __future__ import annotations

from uuid import uuid4

from gw2radar.player_os.intent.constraint_extractor import constraints_to_dict, extract_constraints
from gw2radar.player_os.intent.intent_router import route_intent
from gw2radar.player_os.intent.intent_templates import get_intent_template
from gw2radar.player_os.intent.models import IntentParseResult, PlayerConstraint, PlayerIntent


def parse_player_intent(
    raw_text: str | None = None,
    *,
    template_id: str | None = None,
    account_id: str | None = None,
    ui_constraints: dict | None = None,
) -> IntentParseResult:
    intent_id = f"intent-{uuid4().hex[:12]}"
    template = get_intent_template(template_id) if template_id else None
    template_constraints: list[PlayerConstraint] = []
    constraints: list[PlayerConstraint] = []
    intent_type = "unknown"
    confidence = 0.35
    assumptions = [
        "Intent parsing is deterministic and does not call an LLM.",
        "Account facts are not inferred from the player's text.",
    ]

    if template is not None:
        intent_type = template.default_intent_type
        confidence = 0.86
        template_constraints = [
            PlayerConstraint(
                constraint_id=f"{intent_id}:template:{key}",
                intent_id=intent_id,
                key=key,
                value=value,
                source="template",
                confidence=1.0,
            )
            for key, value in sorted(template.default_constraints.items())
        ]

    text_intent_type, text_confidence = _classify_text(raw_text or "")
    if text_intent_type != "unknown":
        intent_type = text_intent_type
        confidence = max(confidence, text_confidence)

    constraints.extend(template_constraints)
    constraints.extend(extract_constraints(raw_text, intent_id))
    if ui_constraints:
        constraints.extend(
            PlayerConstraint(
                constraint_id=f"{intent_id}:ui:{key}",
                intent_id=intent_id,
                key=key,
                value=value,
                source="ui_selection",
                confidence=1.0,
            )
            for key, value in sorted(ui_constraints.items())
        )

    merged_constraints = constraints_to_dict(constraints)
    goal_id = merged_constraints.get("goal_id")
    profession = merged_constraints.get("profession") or merged_constraints.get("preferred_profession")
    specialization = merged_constraints.get("specialization")
    game_mode = merged_constraints.get("game_mode")
    warnings: list[str] = []
    questions: list[str] = []

    if intent_type == "unknown" or confidence < 0.6:
        questions.append("What kind of plan do you want: returner, legendary, build, market, or what should I do now?")
        warnings.append("Low-confidence intent; the system will ask for clarification before strong recommendations.")
    if intent_type == "legendary" and not goal_id:
        questions.append("Which legendary goal should be planned?")
    if intent_type == "build_fit" and not (profession or specialization):
        questions.append("Which profession or build do you want to evaluate?")

    intent = PlayerIntent(
        intent_id=intent_id,
        account_id=account_id,
        raw_text=raw_text,
        template_id=template_id,
        intent_type=intent_type,
        goal_id=goal_id,
        profession=profession,
        specialization=specialization,
        game_mode=game_mode,
        urgency="high" if intent_type == "what_should_i_do_now" else "medium",
        constraints=merged_constraints,
        confidence=round(confidence, 2),
        assumptions=assumptions,
        warnings=warnings,
    )
    return IntentParseResult(
        intent=intent,
        constraints=constraints,
        clarifying_questions=questions,
        router_target=route_intent(intent),
    )


def _classify_text(raw_text: str) -> tuple[str, float]:
    lowered = raw_text.lower()
    if not lowered.strip():
        return "unknown", 0.35
    if any(token in lowered or token in raw_text for token in ("三年", "没玩", "returning", "returner", "back after", "重新开始")):
        return "returner", 0.88
    if any(token in lowered for token in ("aurora", "vision", "legendary", "craft")) or any(
        token in raw_text for token in ("传奇", "欧若拉", "做 Aurora")
    ):
        return "legendary", 0.9
    if any(token in lowered for token in ("build", "reaper", "power", "fit", "gear")) or any(
        token in raw_text for token in ("配装", "能不能玩", "装备")
    ):
        return "build_fit", 0.87
    if any(token in lowered for token in ("what should i do", "do now", "today")) or any(
        token in raw_text for token in ("现在做什么", "今天该做什么", "每日")
    ):
        return "what_should_i_do_now", 0.84
    if any(token in lowered for token in ("market", "watchlist", "price")) or any(token in raw_text for token in ("市场", "价格")):
        return "market_watch", 0.78
    return "unknown", 0.35
