from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.account_value import (
    build_account_holding_index,
    build_account_value_snapshot,
    render_account_value_snapshot_csv,
    render_account_value_snapshot_markdown,
)
from gw2radar.commercial.market_radar import PriceSnapshotInput, record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, PlayerState
from gw2radar.security.api_key_permissions import build_permission_report


def test_permission_report_explains_value_analysis_readiness() -> None:
    report = build_permission_report(
        {
            "name": "Limited Value Key",
            "permissions": ["account", "wallet"],
        }
    )

    payload = report.model_dump(mode="json")

    assert payload["value_analysis_readiness"]["status"] == "limited"
    assert "wallet_value" in {module["module_id"] for module in payload["unlocked_analysis_modules"]}
    assert "material_value" in {module["module_id"] for module in payload["blocked_analysis_modules"]}
    assert "inventories" in payload["value_analysis_readiness"]["missing_permissions"]


def test_holding_index_summarizes_private_player_state_without_raw_payloads() -> None:
    graph = _sample_holding_graph()
    permission_report = build_permission_report({"permissions": ["account", "wallet"]}).model_dump(mode="json")

    index = build_account_holding_index(graph, permission_report=permission_report)
    payload = index.model_dump(mode="json")

    assert payload["holding_count"] == 2
    assert payload["location_counts"] == {"materials": 1, "wallet": 1}
    assert {holding["privacy_boundary"] for holding in payload["holdings"]} == {"private_summary_only"}
    assert "raw_payload" not in str(payload)
    assert "material_value" in {gap["module_id"] for gap in payload["coverage_gaps"]}
    assert any("do-not-sell" in boundary for boundary in payload["safety_boundaries"])


def test_account_value_snapshot_uses_latest_prices_and_marks_unpriced() -> None:
    temp_dir = Path(".test_tmp") / f"account-value-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account-value.db'}")
        init_db()
        graph = _sample_holding_graph()
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:19721",
                    item_name="Glob of Ectoplasm",
                    buy_price_copper=1800,
                    sell_price_copper=2000,
                    volume=10000,
                ),
            )
            snapshot = build_account_value_snapshot(graph, session)

        payload = snapshot.model_dump(mode="json")

        assert payload["summary"]["total_value_buy_copper"] == 432600
        assert payload["summary"]["total_value_sell_copper"] == 434000
        assert payload["summary"]["net_sell_value_copper"] == 431900
        assert payload["summary"]["priced_holding_count"] == 2
        assert payload["summary"]["unpriced_holding_count"] == 0
        assert payload["by_status"][0]["key"] == "priced"
        assert "never guarantees returns" in " ".join(payload["safety_boundaries"])
        assert "raw_payload" not in str(payload)

        markdown = render_account_value_snapshot_markdown(snapshot)
        csv = render_account_value_snapshot_csv(snapshot)
        assert "# Account Value Snapshot" in markdown
        assert "holding_id,entity_id,name,location,status" in csv
    finally:
        close_database()


def _sample_holding_graph() -> GraphData:
    graph = GraphData(account_id="gw2:account:Example.1234")
    graph.add_entity(
        Entity(
            id="gw2:item:19721",
            type=EntityType.ITEM,
            canonical_name="Glob of Ectoplasm",
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
        )
    )
    graph.add_entity(
        Entity(
            id="gw2:currency:1",
            type=EntityType.CURRENCY,
            canonical_name="Coin",
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
        )
    )
    graph.add_player_state(
        PlayerState(
            id="state:material",
            account_id="gw2:account:Example.1234",
            entity_id="gw2:item:19721",
            quantity=7,
            location="materials",
        )
    )
    graph.add_player_state(
        PlayerState(
            id="state:wallet",
            account_id="gw2:account:Example.1234",
            entity_id="gw2:currency:1",
            quantity=420000,
            location="wallet",
        )
    )
    return graph
