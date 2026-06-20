from gw2radar.commercial.account_value import build_account_holding_index
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
    permission_report = build_permission_report({"permissions": ["account", "wallet"]}).model_dump(mode="json")

    index = build_account_holding_index(graph, permission_report=permission_report)
    payload = index.model_dump(mode="json")

    assert payload["holding_count"] == 2
    assert payload["location_counts"] == {"materials": 1, "wallet": 1}
    assert {holding["privacy_boundary"] for holding in payload["holdings"]} == {"private_summary_only"}
    assert "raw_payload" not in str(payload)
    assert "material_value" in {gap["module_id"] for gap in payload["coverage_gaps"]}
    assert any("do-not-sell" in boundary for boundary in payload["safety_boundaries"])
