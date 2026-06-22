import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.api.routes import market as market_route
from gw2radar.api.routes import public_refresh as public_refresh_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, PlayerState


class AccountSyncGateway:
    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {
            "name": "Unit Test",
            "permissions": ["account", "characters", "wallet", "inventories", "progression", "tradingpost"],
        }


class DelayedPublicRefreshGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.RATE_LIMITED_RETRYING,
            endpoint=endpoint,
            request_id="timeline:public:rate-limit",
            retry_after_seconds=30,
            diagnostics={"params_hash": "safe-public-hash"},
        )


class DelayedMarketPriceGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.RATE_LIMITED_RETRYING,
            endpoint=endpoint,
            request_id="timeline:market:rate-limit",
            retry_after_seconds=30,
            diagnostics={"params_hash": "safe-market-hash"},
        )


def test_player_gateway_incident_timeline_correlates_refresh_events_without_secrets() -> None:
    temp_dir = Path(".test_tmp") / f"gateway-incidents-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_account_factory = account_sync_route.gateway_factory
    original_public_factory = public_refresh_route.gateway_factory
    original_market_factory = market_route.gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'timeline.db'}")
        state.reset_cached_graph()
        account_sync_route.gateway_factory = AccountSyncGateway
        public_refresh_route.gateway_factory = lambda: DelayedPublicRefreshGateway()
        market_route.gateway_factory = lambda: DelayedMarketPriceGateway()
        client = TestClient(app)

        public_queued = client.post(
            "/api/v1/public/refresh",
            json={"endpoint": "/v2/items", "ids": [19721], "chunk_size": 1},
        )
        public_drained = client.post("/api/v1/public/refresh/drain-one")
        assert public_queued.status_code == 200
        assert public_drained.status_code == 200

        raw_key = "12345678-abcdef-secret-key"
        assert client.put("/account/api-key", json={"api_key": raw_key}).status_code == 200
        assert client.post("/api/v1/account/sync").status_code == 200

        assert client.post("/mock/load").status_code == 200
        _add_private_holding("gw2:item:19721", "Glob of Ectoplasm")
        price_refresh = client.post("/api/v1/market/snapshots/official-refresh?chunk_size=1")
        assert price_refresh.status_code == 200
        assert price_refresh.json()["data"]["official_price_refresh"]["status"] == "refresh_pending"

        response = client.get("/api/v1/player/gateway-incidents?limit=20")

        assert response.status_code == 200
        timeline = response.json()["data"]["gateway_incident_timeline"]
        assert timeline["schema_version"] == "gw2radar.gateway_incident_timeline.v1"
        assert timeline["timeline_status"] == "waiting_retry"
        assert timeline["retry_event_count"] >= 2
        sources = {event["source"] for event in timeline["events"]}
        assert {"account_sync", "public_refresh", "market_price_refresh"} <= sources
        public_event = next(event for event in timeline["events"] if event["source"] == "public_refresh")
        market_event = next(event for event in timeline["events"] if event["source"] == "market_price_refresh")
        assert public_event["retry_after_seconds"] == 30
        assert market_event["retryable"] is True
        assert any("Market price refresh" in action for action in timeline["next_actions"])
        assert "raw api keys" in timeline["boundary"].lower()
        assert raw_key not in str(timeline)
        assert "secret-key" not in str(timeline).lower()

        first_snapshot = client.post("/api/v1/player/gateway-incidents/snapshots?source=test_gateway_incidents")
        second_snapshot = client.post("/api/v1/player/gateway-incidents/snapshots?source=test_gateway_incidents")
        history = client.get("/api/v1/player/gateway-incidents/history?limit=10")
        history_md = client.get("/api/v1/player/gateway-incidents/history?format=markdown&limit=10")
        history_csv = client.get("/api/v1/player/gateway-incidents/history?format=csv&limit=10")
        note = client.post(
            "/api/v1/player/gateway-incidents/review-notes",
            json={
                "snapshot_id": first_snapshot.json()["data"]["snapshot"]["snapshot_id"],
                "status": "assigned",
                "reviewer": "unit-support",
                "assignee": "ops",
                "note": "Retry window observed; assign follow-up without requesting raw API keys.",
                "source": "test_gateway_incidents",
            },
        )
        notes = client.get("/api/v1/player/gateway-incidents/review-notes?reviewer=unit-support&assignee=ops")
        notes_md = client.get("/api/v1/player/gateway-incidents/review-notes?format=markdown&reviewer=unit-support")
        notes_csv = client.get("/api/v1/player/gateway-incidents/review-notes?format=csv&reviewer=unit-support")
        closed_note = client.post(
            f"/api/v1/player/gateway-incidents/review-notes/{note.json()['data']['review_note']['note_id']}/status",
            json={
                "status": "closed",
                "reviewer": "unit-support",
                "assignee": "ops",
                "note": "Closed after retry window cleared.",
            },
        )
        closed_notes = client.get("/api/v1/player/gateway-incidents/review-notes?status=closed&reviewer=unit-support")
        support_audit = client.post(
            "/account/debug-bundle/review/audit",
            json={
                "bundle": {
                    "schema_version": "gw2radar.account_debug_bundle.v1",
                    "client_state": {"active_view": "connect", "active_build_id_present": False},
                    "key_status": {"is_configured": True},
                    "permission_summary": {"missing_required_permissions": []},
                    "sync_summary": {"counts": {"retry_scheduled": 0}, "endpoint_progress": []},
                    "diagnostic_summary": {
                        "summary_status": "ready",
                        "checks": [
                            {"check_id": "api_key_stored", "status": "pass"},
                            {"check_id": "permissions_ready", "status": "pass"},
                            {"check_id": "sync_job_visible", "status": "pass"},
                            {"check_id": "private_snapshot_written", "status": "pass"},
                            {"check_id": "synced_character_snapshot", "status": "pass"},
                            {"check_id": "build_fit_bridge_ready", "status": "pass"},
                        ],
                    },
                    "snapshot_summary": {"synced_character_snapshot_count": 1, "synced_gear_count": 4},
                },
                "reviewer": "unit-support",
                "reply_template": "Use metadata-only incident dashboard.",
            },
        )
        incident_dashboard = client.get("/api/v1/player/support-case/incident-dashboard?limit=20")
        incident_dashboard_md = client.get("/api/v1/player/support-case/incident-dashboard?format=markdown&limit=20")
        incident_dashboard_csv = client.get("/api/v1/player/support-case/incident-dashboard?format=csv&limit=20")
        incident_packet = client.post("/api/v1/player/support-case/incident-packet?limit=20")
        incident_packets = client.get("/api/v1/player/support-case/incident-packet?limit=10")
        session_packet = client.get("/api/v1/player/session-packet?limit=10")

        assert first_snapshot.status_code == 200
        assert second_snapshot.status_code == 200
        assert first_snapshot.json()["data"]["snapshot"]["schema_version"] == "gw2radar.gateway_incident_snapshot.v1"
        assert history.status_code == 200
        history_payload = history.json()["data"]["history"]
        assert history_payload["schema_version"] == "gw2radar.gateway_incident_history.v1"
        assert len(history_payload["snapshots"]) >= 2
        assert history_payload["comparison"]["schema_version"] == "gw2radar.gateway_incident_history_comparison.v1"
        assert history_payload["comparison"]["status"] in {"unchanged", "improved", "regressed"}
        assert "secret-key" not in str(history_payload).lower()
        assert history_md.status_code == 200
        assert "# Gateway Incident History" in history_md.text
        assert history_csv.status_code == 200
        assert "snapshot_id,created_at,source,timeline_status" in history_csv.text
        assert note.status_code == 200
        note_payload = note.json()["data"]["review_note"]
        assert note_payload["schema_version"] == "gw2radar.gateway_incident_review_note.v1"
        assert note_payload["status"] == "assigned"
        assert note_payload["assignee"] == "ops"
        assert "raw API keys" in note_payload["note"]
        assert "secret-key" not in str(note_payload).lower()
        assert notes.status_code == 200
        notes_payload = notes.json()["data"]["review_notes"]
        assert notes_payload["schema_version"] == "gw2radar.gateway_incident_review_note_list.v1"
        assert notes_payload["assigned_count"] >= 1
        assert notes_md.status_code == 200
        assert "# Gateway Incident Review Notes" in notes_md.text
        assert notes_csv.status_code == 200
        assert "note_id,snapshot_id,status,reviewer,assignee" in notes_csv.text
        assert closed_note.status_code == 200
        assert closed_note.json()["data"]["review_note"]["status"] == "closed"
        assert closed_notes.status_code == 200
        assert closed_notes.json()["data"]["review_notes"]["closed_count"] >= 1
        assert support_audit.status_code == 200
        assert incident_dashboard.status_code == 200
        incident_payload = incident_dashboard.json()["data"]["support_case_incident_dashboard"]
        assert incident_payload["schema_version"] == "gw2radar.support_case_incident_dashboard.v1"
        assert incident_payload["support_audit_count"] >= 1
        assert incident_payload["gateway_closed_count"] >= 1
        assert "gateway_notes" in {card["card_id"] for card in incident_payload["status_cards"]}
        assert "secret-key" not in str(incident_payload).lower()
        assert incident_dashboard_md.status_code == 200
        assert "# Support Case Incident Dashboard" in incident_dashboard_md.text
        assert incident_dashboard_csv.status_code == 200
        assert "ready,maturity_label,support_status" in incident_dashboard_csv.text
        assert incident_packet.status_code == 200
        packet_payload = incident_packet.json()["data"]["support_case_incident_packet"]
        assert packet_payload["schema_version"] == "gw2radar.support_case_incident_packet_manifest.v1"
        assert packet_payload["file_count"] == 4
        assert len(packet_payload["checksum_sha256"]) == 64
        assert packet_payload["contains_raw_key"] is False
        assert packet_payload["contains_private_source_payload"] is False
        assert {file["file_name"] for file in packet_payload["files"]} == {
            "dashboard.json",
            "dashboard.md",
            "dashboard.csv",
            "manifest.json",
        }
        assert incident_packets.status_code == 200
        assert incident_packets.json()["data"]["support_case_incident_packets"][0]["packet_id"] == packet_payload["packet_id"]
        manifest = client.get(f"/api/v1/player/support-case/incident-packet/{packet_payload['packet_id']}/manifest.json")
        packet_md = client.get(f"/api/v1/player/support-case/incident-packet/{packet_payload['packet_id']}/dashboard.md")
        blocked_path = client.get(f"/api/v1/player/support-case/incident-packet/{packet_payload['packet_id']}/../manifest.json")
        missing_file = client.get(f"/api/v1/player/support-case/incident-packet/{packet_payload['packet_id']}/secret.txt")
        zip_manifest = client.get("/api/v1/player/support-case/incident-packet/bundle?format=manifest")
        zip_bundle = client.get("/api/v1/player/support-case/incident-packet/bundle")
        zip_verify = client.post("/api/v1/player/support-case/incident-packet/bundle/verify")
        assert manifest.status_code == 200
        assert "gw2radar.support_case_incident_packet_manifest.v1" in manifest.text
        assert packet_md.status_code == 200
        assert "# Support Case Incident Dashboard" in packet_md.text
        assert blocked_path.status_code == 404
        assert missing_file.status_code == 404
        assert zip_manifest.status_code == 200
        zip_manifest_payload = zip_manifest.json()["data"]["support_case_incident_packet_zip_bundle"]
        assert zip_manifest_payload["schema_version"] == "gw2radar.support_case_incident_packet_zip_manifest.v1"
        assert zip_manifest_payload["file_count"] == 4
        assert len(zip_manifest_payload["checksum_sha256"]) == 64
        assert zip_bundle.status_code == 200
        assert zip_bundle.headers["x-checksum-sha256"] == zip_manifest_payload["checksum_sha256"]
        assert set(ZipFile(BytesIO(zip_bundle.content)).namelist()) == {
            "support_case_incident_packet/dashboard.json",
            "support_case_incident_packet/dashboard.md",
            "support_case_incident_packet/dashboard.csv",
            "support_case_incident_packet/manifest.json",
        }
        assert zip_verify.status_code == 200
        verification = zip_verify.json()["data"]["support_case_incident_packet_zip_verification"]
        assert verification["schema_version"] == "gw2radar.support_case_incident_packet_zip_verification.v1"
        assert verification["ready"] is True
        assert verification["checksum_sha256"] == zip_manifest_payload["checksum_sha256"]
        tampered_buffer = BytesIO()
        with ZipFile(BytesIO(zip_bundle.content), mode="r") as source_archive:
            with ZipFile(tampered_buffer, mode="w") as tampered_archive:
                for name in source_archive.namelist():
                    tampered_archive.writestr(name, source_archive.read(name))
                tampered_archive.writestr("support_case_incident_packet/secret.txt", "secret-key")
        tampered_verify = client.post(
            "/api/v1/player/support-case/incident-packet/bundle/verify",
            content=tampered_buffer.getvalue(),
            headers={"Content-Type": "application/zip"},
        )
        assert tampered_verify.status_code == 200
        assert tampered_verify.json()["data"]["support_case_incident_packet_zip_verification"]["ready"] is False
        assert session_packet.status_code == 200
        packet = session_packet.json()["data"]["session_packet"]
        assert packet["gateway_incident_history"]["schema_version"] == "gw2radar.gateway_incident_history.v1"
        assert "gateway_incident_snapshots=" in "; ".join(packet["debug_safe_evidence"])
        assert packet["export_manifest"]["gateway_incident_snapshot_count"] >= 2
    finally:
        account_sync_route.gateway_factory = original_account_factory
        public_refresh_route.gateway_factory = original_public_factory
        market_route.gateway_factory = original_market_factory
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _add_private_holding(entity_id: str, name: str) -> None:
    graph = state.get_graph()
    graph.add_entity(
        Entity(
            id=entity_id,
            type=EntityType.ITEM,
            canonical_name=name,
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
        )
    )
    graph.add_player_state(
        PlayerState(
            id=f"state:timeline:{entity_id.rsplit(':', 1)[-1]}",
            account_id=graph.account_id or "mock:account:lee",
            entity_id=entity_id,
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            quantity=7,
            location="materials",
        )
    )
    state.save_graph(graph)
