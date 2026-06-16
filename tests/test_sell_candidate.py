from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import MarketSignalType, infer_market_signals
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import PlayerState


def test_sell_candidate_only_for_true_surplus() -> None:
    temp_dir = Path(".test_tmp") / f"market-sell-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        graph = build_mock_graph()
        graph.add_player_state(
            PlayerState(
                id="state:mock:account:lee:gw2:item:glob_of_ectoplasm:surplus",
                account_id=graph.account_id or "mock:account:lee",
                entity_id="gw2:item:glob_of_ectoplasm",
                graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
                quantity=25,
                location="materials",
            )
        )
        with db_session.SessionLocal() as session:
            signals = infer_market_signals(session, graph, "gw2:goal:aurora")

        assert any(
            signal.item_id == "gw2:item:glob_of_ectoplasm"
            and signal.signal_type is MarketSignalType.CONSIDER_SELL_SURPLUS
            for signal in signals
        )
    finally:
        close_database()
