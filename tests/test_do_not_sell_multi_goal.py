from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import add_legendary_goal, recompute_legendary_plan
from gw2radar.commercial.account_value import build_account_value_snapshot
from gw2radar.commercial.market_radar import MarketSignalType, infer_market_signals
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from legendary_test_helpers import add_second_legendary_goal


def test_do_not_sell_policy_reserves_materials_across_active_goals() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-dns-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        add_second_legendary_goal(graph)
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            add_legendary_goal(session, graph, "gw2:goal:vision")
            result = recompute_legendary_plan(session, graph)

        mystic_coin = next(item for item in result.do_not_sell if item.entity_id == "gw2:item:mystic_coin")
        assert mystic_coin.policy == "do_not_sell"
        assert set(mystic_coin.reserved_for_goal_ids) == {"gw2:goal:aurora", "gw2:goal:vision"}
    finally:
        close_database()


def test_account_value_and_market_signals_respect_multi_goal_reservations() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-market-reserve-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        add_second_legendary_goal(graph)
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            add_legendary_goal(session, graph, "gw2:goal:vision")
            snapshot = build_account_value_snapshot(graph, session, top_limit=100)
            signals = infer_market_signals(session, graph, "gw2:goal:aurora")

        mystic_coin_holding = next(holding for holding in snapshot.top_holdings if holding.entity_id == "gw2:item:mystic_coin")
        assert mystic_coin_holding.reserved_quantity > 0
        assert set(mystic_coin_holding.reserved_for_goal_ids) == {"gw2:goal:aurora", "gw2:goal:vision"}
        assert "reserved_for_goal" in mystic_coin_holding.warning_codes
        assert not any(
            signal.item_id == "gw2:item:mystic_coin"
            and signal.signal_type is MarketSignalType.CONSIDER_SELL_SURPLUS
            for signal in signals
        )
        assert any(
            signal.item_id == "gw2:item:mystic_coin"
            and signal.reserved_quantity > 0
            and set(signal.reserved_for_goal_ids) == {"gw2:goal:aurora", "gw2:goal:vision"}
            for signal in signals
        )
    finally:
        close_database()
