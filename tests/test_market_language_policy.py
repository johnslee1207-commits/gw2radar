import pytest

from gw2radar.commercial.market_radar import validate_market_language


def test_market_language_policy_rejects_forbidden_profit_language() -> None:
    with pytest.raises(ValueError):
        validate_market_language("This is guaranteed profit and you must buy now.")


def test_market_language_policy_allows_observation_language() -> None:
    validate_market_language("Consider observing the price above recent average before manual action.")
