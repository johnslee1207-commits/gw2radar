#!/usr/bin/env python3
import shutil
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.api.routes import public_refresh as public_refresh_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult


class SmokeAccountGateway:
    payloads = {
        "/v2/account": {"name": "Smoke.1234", "world": 1001},
        "/v2/characters": ["Smoke Hero"],
        "/v2/account/wallet": [{"id": 1, "value": 42}],
        "/v2/account/materials": [{"id": 19721, "count": 7}],
        "/v2/account/bank": [{"id": 19722, "count": 2}],
        "/v2/account/achievements": [{"id": 999, "current": 1, "max": 1}],
    }

    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {"permissions": ["account", "characters", "wallet", "inventories", "progression"]}

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=self.payloads[endpoint],
            evidence_id=f"evidence:{endpoint}",
        )


class SmokePublicGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=[{"id": item_id, "name": f"Item {item_id}"} for item_id in ids],
            evidence_id=f"evidence:{endpoint}:{','.join(str(item_id) for item_id in ids)}",
        )


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"sync-smoke-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_account_gateway = account_sync_route.gateway_factory
    original_public_gateway = public_refresh_route.gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'sync-smoke.db'}")
        state.reset_cached_graph()
        account_sync_route.gateway_factory = SmokeAccountGateway
        public_refresh_route.gateway_factory = SmokePublicGateway
        client = TestClient(app)

        key_put = client.put("/account/api-key", json={"api_key": "12345678-abcdef-secret-key"})
        account_enqueue = client.post("/api/v1/account/sync")
        account_drain = client.post("/api/v1/account/sync/drain-one")
        public_enqueue = client.post(
            "/api/v1/public/refresh",
            json={"endpoint": "/v2/items", "ids": [2, 1, 2], "chunk_size": 200},
        )
        public_drain = client.post("/api/v1/public/refresh/drain-one")
        ops = client.get("/api/v1/ops/status")
    finally:
        account_sync_route.gateway_factory = original_account_gateway
        public_refresh_route.gateway_factory = original_public_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)

    checks = [
        key_put.status_code == 200,
        "12345678-abcdef-secret-key" not in str(key_put.json()),
        account_enqueue.status_code == 200 and account_enqueue.json().get("status") == "queued",
        account_drain.status_code == 200 and account_drain.json().get("status") == "succeeded",
        public_enqueue.status_code == 200 and public_enqueue.json().get("ids") == [1, 2],
        public_drain.status_code == 200 and public_drain.json().get("status") == "succeeded",
        ops.status_code == 200 and ops.json().get("ok") is True,
    ]
    if not all(checks):
        print("FAIL: GW2Radar sync smoke harness checks failed")
        return 1
    print("PASS: GW2Radar account/public sync smoke succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
