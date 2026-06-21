"""Account connection diagnostic harness.

The harness exercises the real player connection chain with a fake GW2 gateway:
store a pasted API key, inspect permissions, enqueue and drain account sync,
verify private-layer graph writes, and confirm Build Fit can read synced
character gear snapshots.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api import state  # noqa: E402
from gw2radar.api.main import app  # noqa: E402
from gw2radar.api.routes import account as account_route  # noqa: E402
from gw2radar.api.routes import account_sync as account_sync_route  # noqa: E402
from gw2radar.db.session import close_database, configure_database  # noqa: E402
from gw2radar.ingest.gateway_status import GatewayStatus  # noqa: E402
from gw2radar.ingest.gw2_api_gateway import GatewayResult  # noqa: E402
from gw2radar.ontology.graph_layers import GraphLayer  # noqa: E402

CLEAN_KEY = "12345678-1234-1234-1234-123456789abc-1234-1234-1234-123456789abc"


class DiagnosticAccountGateway:
    payloads = {
        "/v2/account": {"name": "Diagnostic.1234", "world": 1001},
        "/v2/characters": ["Diagnostic Hero"],
        "/v2/characters/Diagnostic%20Hero": {
            "name": "Diagnostic Hero",
            "profession": "Mesmer",
            "level": 80,
            "equipment": [
                {"id": 1001, "slot": "Coat", "stats": {"id": 161}, "upgrades": [2001]},
                {"id": 1002, "slot": "WeaponA1", "stats": {"id": 161}, "upgrades": [2002]},
            ],
        },
        "/v2/items": [
            {"id": 1001, "name": "Diagnostic Berserker Chest", "type": "Armor"},
            {"id": 1002, "name": "Diagnostic Berserker Dagger", "type": "Weapon"},
            {"id": 2001, "name": "Superior Rune of the Scholar", "type": "UpgradeComponent", "details": {"type": "Rune"}},
            {"id": 2002, "name": "Superior Sigil of Force", "type": "UpgradeComponent", "details": {"type": "Sigil"}},
        ],
        "/v2/itemstats": [{"id": 161, "name": "Berserker"}],
        "/v2/account/wallet": [{"id": 1, "value": 420000}],
        "/v2/account/materials": [{"id": 19721, "count": 7}],
        "/v2/account/bank": [{"id": 19722, "count": 2}],
        "/v2/account/inventory": [{"id": 19723, "count": 3}],
        "/v2/account/achievements": [{"id": 999, "current": 1, "max": 1}],
        "/v2/commerce/transactions/current/buys": [{"item_id": 19724, "quantity": 4, "price": 1200}],
        "/v2/commerce/transactions/current/sells": [{"item_id": 19725, "quantity": 5, "price": 1500}],
    }

    def _fetch_tokeninfo(self, api_key: str, *, request_id: str) -> dict:
        if api_key != CLEAN_KEY:
            raise AssertionError(f"API key was not normalized before tokeninfo: {api_key!r}")
        return {
            "name": "Diagnostic Test Key",
            "permissions": ["account", "characters", "inventories", "progression", "wallet", "builds", "tradingpost"],
        }

    def get(self, endpoint: str, *, params=None, api_key=None, priority: str = "P3") -> GatewayResult:
        if api_key != CLEAN_KEY:
            raise AssertionError(f"API key was not normalized before {endpoint}: {api_key!r}")
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"diagnostic:{endpoint}",
            payload=self.payloads[endpoint],
            evidence_id=f"evidence:{endpoint}",
        )

    def get_batch(self, endpoint: str, ids, *, params=None, api_key=None, priority: str = "P3") -> GatewayResult:
        wanted = {int(item_id) for item_id in ids}
        payload = [row for row in self.payloads[endpoint] if row["id"] in wanted]
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"diagnostic:{endpoint}",
            payload=payload,
            evidence_id=f"evidence:{endpoint}",
        )


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"account-connection-diagnostic-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_permission_gateway = account_route.permission_gateway_factory
    original_sync_gateway = account_sync_route.gateway_factory
    checks: list[tuple[str, bool, str]] = []

    try:
        configure_database(f"sqlite:///{temp_dir / 'account-connection.db'}")
        state.reset_cached_graph()
        account_route.permission_gateway_factory = DiagnosticAccountGateway
        account_sync_route.gateway_factory = DiagnosticAccountGateway
        client = TestClient(app)

        pasted_key = f"\n{CLEAN_KEY[:36]} \u200b\n {CLEAN_KEY[36:]}\t"
        stored = client.put("/account/api-key", json={"api_key": pasted_key})
        status = client.get("/account/api-key/status")
        permissions = client.get("/account/api-key/permissions")
        first_run_before_sync = client.get("/account/first-run-summary")
        enqueue = client.post("/api/v1/account/sync")
        queued_status = client.get("/api/v1/account/sync/status")
        queued_health = client.get("/api/v1/account/sync/health")
        drained = client.post("/api/v1/account/sync/drain-one")
        price_snapshot = client.post(
            "/api/v1/market/snapshots",
            json={
                "item_id": "gw2:item:19721",
                "item_name": "Diagnostic Material",
                "buy_price_copper": 1800,
                "sell_price_copper": 2000,
                "volume": 1000,
            },
        )
        synced_status = client.get("/api/v1/account/sync/status")
        ready_health = client.get("/api/v1/account/sync/health")
        worker_queued = client.post("/api/v1/account/sync")
        worker_run = client.post("/api/v1/account/sync/worker/run?max_jobs=3&worker_id=diagnostic-worker")
        worker_health = client.get("/api/v1/account/sync/health")
        api_diagnostic = client.get("/account/diagnostic")
        first_run_after_sync = client.get("/account/first-run-summary")
        account_holdings = client.get("/api/v1/player/account-holdings")
        account_value = client.get("/api/v1/player/account-value")
        snapshots = client.get("/api/v1/builds/character-snapshots")
        snapshot_payload = snapshots.json().get("data", {}).get("snapshots", []) if snapshots.status_code == 200 else []
        synced_snapshot = next((snapshot for snapshot in snapshot_payload if snapshot.get("source") == "synced_official_api"), None)
        account_gear = (
            client.get(f"/api/v1/builds/character-snapshots/{synced_snapshot['snapshot_id']}/account-gear")
            if synced_snapshot
            else None
        )
        graph = state.get_graph()

        all_payload_text = "\n".join(
            str(response.text)
            for response in [
                stored,
                status,
                permissions,
                first_run_before_sync,
                enqueue,
                queued_status,
                queued_health,
                drained,
                price_snapshot,
                synced_status,
                ready_health,
                worker_queued,
                worker_run,
                worker_health,
                api_diagnostic,
                first_run_after_sync,
                account_holdings,
                account_value,
                snapshots,
            ]
        )
        if account_gear is not None:
            all_payload_text += str(account_gear.text)

        _add(checks, "key storage accepts pasted key and returns only masked key", stored.status_code == 200 and stored.json().get("masked_key") == "1234...9abc", stored.text)
        _add(checks, "key status is configured without raw key leakage", status.status_code == 200 and status.json().get("is_configured") is True, status.text)
        _add(checks, "permission inspection is ready", permissions.status_code == 200 and permissions.json().get("limited_mode") is False and permissions.json().get("missing_required_permissions") == [], permissions.text)
        _add(checks, "permission inspection explains value analysis readiness", permissions.status_code == 200 and permissions.json().get("value_analysis_readiness", {}).get("status") in {"ready", "limited"} and permissions.json().get("unlocked_analysis_modules"), permissions.text)
        _add(
            checks,
            "first-run summary explains pre-sync empty results",
            first_run_before_sync.status_code == 200
            and first_run_before_sync.json().get("schema_version") == "gw2radar.account_first_run_summary.v1"
            and first_run_before_sync.json().get("summary_status") == "sync_not_started"
            and first_run_before_sync.json().get("primary_action", {}).get("action_id") == "enqueueSync",
            first_run_before_sync.text,
        )
        _add(checks, "account sync queues endpoint-level work", enqueue.status_code == 200 and enqueue.json().get("status") == "queued" and len(enqueue.json().get("endpoint_progress", [])) == 9, enqueue.text)
        _add(checks, "queued sync status is visible", queued_status.status_code == 200 and queued_status.json().get("counts", {}).get("queued") == 1, queued_status.text)
        _add(
            checks,
            "account sync worker health reports active queue",
            queued_health.status_code == 200
            and queued_health.json().get("schema_version") == "gw2radar.account_sync_worker_health.v1"
            and queued_health.json().get("health_status") == "active"
            and queued_health.json().get("queue_depth") == 1,
            queued_health.text,
        )
        _add(checks, "drain-one succeeds and writes player state", drained.status_code == 200 and drained.json().get("status") == "succeeded" and drained.json().get("updated_player_state", 0) >= 5, drained.text)
        _add(checks, "manual price snapshot records account value evidence", price_snapshot.status_code == 200 and price_snapshot.json().get("data", {}).get("snapshot", {}).get("item_id") == "gw2:item:19721", price_snapshot.text)
        _add(checks, "post-drain status exposes succeeded endpoints", synced_status.status_code == 200 and synced_status.json().get("counts", {}).get("succeeded") == 1, synced_status.text)
        _add(
            checks,
            "account sync worker health reports ready after drain",
            ready_health.status_code == 200
            and ready_health.json().get("schema_version") == "gw2radar.account_sync_worker_health.v1"
            and ready_health.json().get("health_status") == "ready"
            and ready_health.json().get("counts", {}).get("succeeded") == 1,
            ready_health.text,
        )
        _add(
            checks,
            "repeat account sync worker run upserts private layer",
            worker_queued.status_code == 200
            and worker_run.status_code == 200
            and worker_run.json().get("schema_version") == "gw2radar.account_sync_worker_run.v1"
            and worker_run.json().get("worker_status") == "drained"
            and worker_run.json().get("processed_count") == 1
            and worker_run.json().get("health", {}).get("health_status") == "ready"
            and worker_health.status_code == 200
            and worker_health.json().get("counts", {}).get("succeeded") == 2,
            worker_run.text,
        )
        _add(checks, "read-only API diagnostic reports ready lifecycle", api_diagnostic.status_code == 200 and api_diagnostic.json().get("summary_status") == "ready" and {check.get("status") for check in api_diagnostic.json().get("checks", [])} == {"pass"}, api_diagnostic.text)
        _add(
            checks,
            "first-run summary reports ready result targets after sync",
            first_run_after_sync.status_code == 200
            and first_run_after_sync.json().get("summary_status") == "ready"
            and {target.get("status") for target in first_run_after_sync.json().get("result_targets", [])} == {"ready"},
            first_run_after_sync.text,
        )
        holding_counts = account_holdings.json().get("data", {}).get("account_holding_index", {}).get("location_counts", {}) if account_holdings.status_code == 200 else {}
        _add(checks, "private account holding index summarizes synced state", account_holdings.status_code == 200 and account_holdings.json().get("data", {}).get("account_holding_index", {}).get("holding_count", 0) >= 8 and holding_counts.get("wallet") == 1 and holding_counts.get("shared_inventory") == 1 and holding_counts.get("tradingpost_buy") == 1 and holding_counts.get("tradingpost_sell") == 1, account_holdings.text)
        _add(checks, "account value snapshot reports conservative totals", account_value.status_code == 200 and account_value.json().get("data", {}).get("account_value_snapshot", {}).get("summary", {}).get("total_value_buy_copper", 0) >= 420000 and account_value.json().get("data", {}).get("account_value_snapshot", {}).get("summary", {}).get("unpriced_holding_count", 0) >= 1, account_value.text)
        _add(checks, "private graph layer contains synced account", "gw2:account:Diagnostic.1234" in graph.entities and graph.entities["gw2:account:Diagnostic.1234"].graph_layer is GraphLayer.PRIVATE_PLAYER_STATE, "missing private account entity")
        _add(checks, "Build Fit sees synced character snapshot before manual fallback", snapshots.status_code == 200 and snapshot_payload and snapshot_payload[0].get("source") == "synced_official_api", snapshots.text)
        _add(checks, "synced account gear includes enriched item/stat metadata", account_gear is not None and account_gear.status_code == 200 and _gear_has_categories(account_gear.json(), {"armor", "weapon", "rune", "sigil"}), account_gear.text if account_gear is not None else "no synced snapshot")
        _add(checks, "raw API key never appears in responses", CLEAN_KEY not in all_payload_text, "raw key leaked in diagnostic response payload")
    except Exception as exc:  # pragma: no cover - harness defensive reporting
        checks.append(("unexpected diagnostic error", False, str(exc)))
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        account_sync_route.gateway_factory = original_sync_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)

    failed = [check for check in checks if not check[1]]
    for name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {name}")
        if not passed:
            print(f"  detail: {detail[:400]}")
    if failed:
        print("FAIL: GW2Radar account connection diagnostic failed")
        return 1
    print("PASS: GW2Radar account connection diagnostic succeeded")
    return 0


def _add(checks: list[tuple[str, bool, str]], name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))


def _gear_has_categories(payload: dict, expected: set[str]) -> bool:
    gear = payload.get("data", {}).get("account_gear", {}).get("gear", [])
    categories = {item.get("equipment_category") for item in gear}
    return expected <= categories


if __name__ == "__main__":
    raise SystemExit(main())
