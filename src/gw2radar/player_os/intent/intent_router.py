from __future__ import annotations

from gw2radar.player_os.intent.models import PlayerIntent


ROUTE_BY_INTENT = {
    "returner": "returner_wizard",
    "legendary": "legendary_wizard",
    "build_fit": "build_fit_wizard",
    "account_overview": "what_should_i_do_now_wizard",
    "what_should_i_do_now": "what_should_i_do_now_wizard",
    "market_watch": "what_should_i_do_now_wizard",
    "unknown": "clarify",
}


def route_intent(intent: PlayerIntent) -> str:
    return ROUTE_BY_INTENT[intent.intent_type]
