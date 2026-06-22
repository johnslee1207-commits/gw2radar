"""Player use-path completeness audit harness.

The harness verifies the player-facing path from UI shell to account value
evidence bridge, three commercial opportunities, and report export metadata.
It writes a deterministic Markdown audit for operator review.
"""

from __future__ import annotations

import json
import shutil
import sys
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api import state  # noqa: E402
from gw2radar.api.main import app  # noqa: E402
from gw2radar.api.routes import market as market_route  # noqa: E402
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products  # noqa: E402
from gw2radar.db import session as db_session  # noqa: E402
from gw2radar.db.init_db import init_db  # noqa: E402
from gw2radar.db.session import close_database, configure_database  # noqa: E402
from gw2radar.ingest.gateway_status import GatewayStatus  # noqa: E402
from gw2radar.ingest.gw2_api_gateway import GatewayResult  # noqa: E402


AUDIT_PATH = ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md"
SESSION_PACKET_ARTIFACT_ROOT = ROOT / "src" / "gw2radar" / "reports" / "artifacts" / "player_session_packets"
SUPPORT_HANDOFF_ARTIFACT_ROOT = ROOT / "src" / "gw2radar" / "reports" / "artifacts" / "player_support_handoffs"
SUPPORT_HANDOFF_FINAL_ARCHIVE_ROOT = ROOT / "src" / "gw2radar" / "reports" / "artifacts" / "player_support_handoff_final_archives"


@dataclass
class AuditCheck:
    check_id: str
    label: str
    passed: bool
    maturity: str
    evidence: str
    limitation: str = "None for MVP depth."


class AuditMarketPriceGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="audit:market-price",
            payload=[
                {
                    "id": int(item_id),
                    "buys": {"unit_price": 12000 + int(item_id), "quantity": 10},
                    "sells": {"unit_price": 12500 + int(item_id), "quantity": 20},
                }
                for item_id in ids
            ],
            evidence_id="audit:evidence:market-price",
        )


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"player-use-path-audit-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    checks: list[AuditCheck] = []
    original_market_gateway_factory = market_route.gateway_factory

    try:
        configure_database(f"sqlite:///{temp_dir / 'player-use-path.db'}")
        init_db()
        state.reset_cached_graph()
        market_route.gateway_factory = lambda: AuditMarketPriceGateway()
        client = TestClient(app)

        page = client.get("/player")
        js = client.get("/player-ui/app.js")
        _add(
            checks,
            "ui_shell",
            "Player UI shell exposes connect, dashboard, commercial opportunities, evidence bridge panels, and report center.",
            page.status_code == 200
            and js.status_code == 200
            and all(
                marker in page.text
                for marker in [
                    "GW2 API key",
                    "Sync controls",
                    "Check readiness",
                    "Player Readiness",
                    "Refresh official prices",
                    "Gateway Incident Timeline",
                    "Legendary value evidence",
                    "Market value evidence",
                    "Build value evidence",
                    "Reports center",
                    "Privacy & Safety",
                ]
            )
            and "renderAccountValueEvidenceBridge" in js.text,
            "mature_ui_shell",
            "GET /player and /player-ui/app.js expose required workflow markers.",
        )
        first_run_summary = _json(client.get("/account/first-run-summary"), "load first-run empty-result summary", checks)
        _add(
            checks,
            "account_first_run_summary",
            "First-run summary explains missing, pending, limited, queue, and private-layer states before account-aware results exist.",
            first_run_summary.get("schema_version") == "gw2radar.account_first_run_summary.v1"
            and first_run_summary.get("summary_status") == "missing_key"
            and _get(first_run_summary, "primary_action", "action_id") == "focus_api_key_input"
            and {"api_key", "permissions", "sync_queue", "private_layer", "character_snapshot"}
            <= {card.get("card_id") for card in first_run_summary.get("cards", [])}
            and "raw api keys" in first_run_summary.get("boundary", "").lower()
            and "secret-key" not in json.dumps(first_run_summary).lower(),
            "mature_first_run_empty_result_guidance",
            f"{first_run_summary.get('summary_status', 'unknown')} with {len(first_run_summary.get('cards', []))} state cards.",
        )
        account_sync_health = _json(client.get("/api/v1/account/sync/health"), "load account sync worker health", checks)
        _add(
            checks,
            "account_sync_worker_health",
            "Account sync worker health exposes queue depth, retry depth, failed depth, latest jobs, and safe next actions.",
            account_sync_health.get("schema_version") == "gw2radar.account_sync_worker_health.v1"
            and account_sync_health.get("health_status") in {"idle", "active", "waiting_retry", "ready", "needs_review"}
            and isinstance(account_sync_health.get("counts"), dict)
            and isinstance(account_sync_health.get("latest"), list)
            and "raw api keys" in account_sync_health.get("boundary", "").lower()
            and "secret-key" not in json.dumps(account_sync_health).lower(),
            "mature_account_sync_worker_health",
            f"{account_sync_health.get('health_status', 'unknown')} with queue depth {account_sync_health.get('queue_depth', 0)}.",
        )
        account_sync_contract = client.post("/api/v1/account/sync")
        contract_payload = account_sync_contract.json()
        _add(
            checks,
            "account_sync_gateway_contract",
            "Account sync gateway contract returns structured, user-facing envelopes for not-ready and gateway failure states.",
            account_sync_contract.status_code == 400
            and contract_payload.get("ok") is False
            and _get(contract_payload, "error", "code") == "account_sync_not_ready"
            and _get(contract_payload, "error", "details", "retryable") is False
            and _get(contract_payload, "error", "details", "player_action")
            == "Save a GW2 API key before queueing account sync."
            and "secret-key" not in json.dumps(contract_payload).lower(),
            "mature_gateway_error_contract",
            str(_get(contract_payload, "error", "code") or "missing_error_code"),
        )
        public_refresh_health = _json(client.get("/api/v1/public/refresh/health"), "load public refresh worker health", checks)
        _add(
            checks,
            "public_refresh_worker_health",
            "Public refresh worker health exposes queue depth, retry depth, failed depth, latest jobs, and safe next actions.",
            public_refresh_health.get("schema_version") == "gw2radar.public_refresh_worker_health.v1"
            and public_refresh_health.get("health_status") in {"idle", "active", "waiting_retry", "needs_review"}
            and isinstance(public_refresh_health.get("counts"), dict)
            and isinstance(public_refresh_health.get("latest"), list)
            and "raw api keys" in public_refresh_health.get("boundary", "").lower()
            and "secret-key" not in json.dumps(public_refresh_health).lower(),
            "mature_public_refresh_worker_health",
            f"{public_refresh_health.get('health_status', 'unknown')} with queue depth {public_refresh_health.get('queue_depth', 0)}.",
        )

        _json(client.post("/mock/load"), "load demo graph", checks)
        market_price_refresh = _json(
            client.post("/api/v1/market/snapshots/official-refresh?chunk_size=50"),
            "refresh official market prices",
            checks,
        )
        market_refresh = _get(market_price_refresh, "data", "official_price_refresh") or {}
        _add(
            checks,
            "market_price_refresh_diagnostics",
            "Official market price refresh returns status, player action, retry diagnostics, and no-trading boundary even when no prices are refreshed.",
            market_refresh.get("schema_version") == "gw2radar.official_price_refresh.v1"
            and market_refresh.get("status") in {"succeeded", "idle", "refresh_pending"}
            and isinstance(market_refresh.get("gateway_diagnostics"), list)
            and bool(market_refresh.get("player_action"))
            and "does not trade" in market_refresh.get("boundary", "").lower()
            and "secret-key" not in json.dumps(market_refresh).lower(),
            "mature_market_price_refresh_diagnostics",
            f"{market_refresh.get('status', 'missing')} with {len(market_refresh.get('gateway_diagnostics', []))} gateway diagnostics.",
        )
        gateway_incidents = _json(client.get("/api/v1/player/gateway-incidents?limit=20"), "load gateway incident timeline", checks)
        timeline = _get(gateway_incidents, "data", "gateway_incident_timeline") or {}
        _add(
            checks,
            "gateway_incident_timeline",
            "Gateway incident timeline correlates account sync, public refresh, and market price refresh events into one player-facing view.",
            timeline.get("schema_version") == "gw2radar.gateway_incident_timeline.v1"
            and timeline.get("timeline_status") in {"clear", "active", "waiting_retry", "needs_review"}
            and isinstance(timeline.get("events"), list)
            and isinstance(timeline.get("next_actions"), list)
            and "raw api keys" in timeline.get("boundary", "").lower()
            and "secret-key" not in json.dumps(timeline).lower(),
            "mature_gateway_incident_timeline",
            f"{timeline.get('timeline_status', 'missing')} with {timeline.get('event_count', 0)} events.",
        )
        first_gateway_snapshot = _json(
            client.post("/api/v1/player/gateway-incidents/snapshots?source=player_use_path_audit"),
            "save first gateway incident snapshot",
            checks,
        )
        second_gateway_snapshot = _json(
            client.post("/api/v1/player/gateway-incidents/snapshots?source=player_use_path_audit"),
            "save second gateway incident snapshot",
            checks,
        )
        gateway_history_response = _json(
            client.get("/api/v1/player/gateway-incidents/history?limit=10"),
            "load gateway incident history",
            checks,
        )
        gateway_history_md = client.get("/api/v1/player/gateway-incidents/history?format=markdown&limit=10")
        gateway_history_csv = client.get("/api/v1/player/gateway-incidents/history?format=csv&limit=10")
        gateway_history = _get(gateway_history_response, "data", "history") or {}
        latest_gateway_snapshot_id = _get(gateway_history, "snapshots", 0, "snapshot_id")
        _add(
            checks,
            "gateway_incident_history",
            "Gateway incident history persists metadata-only timeline snapshots and compares retry/failure changes across sessions.",
            _get(first_gateway_snapshot, "data", "snapshot", "schema_version")
            == "gw2radar.gateway_incident_snapshot.v1"
            and _get(second_gateway_snapshot, "data", "snapshot", "schema_version")
            == "gw2radar.gateway_incident_snapshot.v1"
            and gateway_history.get("schema_version") == "gw2radar.gateway_incident_history.v1"
            and len(gateway_history.get("snapshots", [])) >= 2
            and _get(gateway_history, "comparison", "schema_version")
            == "gw2radar.gateway_incident_history_comparison.v1"
            and _get(gateway_history, "comparison", "status") in {"unchanged", "improved", "regressed"}
            and gateway_history_md.status_code == 200
            and "# Gateway Incident History" in gateway_history_md.text
            and gateway_history_csv.status_code == 200
            and "snapshot_id,created_at,source,timeline_status" in gateway_history_csv.text
            and "raw api keys" in gateway_history.get("boundary", "").lower()
            and "secret-key" not in json.dumps(gateway_history).lower()
            and "api_key" not in (gateway_history_md.text + gateway_history_csv.text).lower(),
            "mature_gateway_incident_history",
            f"{len(gateway_history.get('snapshots', []))} snapshots with comparison {(_get(gateway_history, 'comparison', 'status') or 'missing')}.",
        )
        gateway_review_note = _json(
            client.post(
                "/api/v1/player/gateway-incidents/review-notes",
                json={
                    "snapshot_id": latest_gateway_snapshot_id,
                    "status": "assigned",
                    "reviewer": "player_use_path_audit",
                    "assignee": "support",
                    "note": "Audit assigned gateway incident follow-up using metadata-only evidence.",
                    "source": "player_use_path_audit",
                },
            ),
            "save gateway incident review note",
            checks,
        )
        gateway_review_notes_response = _json(
            client.get("/api/v1/player/gateway-incidents/review-notes?reviewer=player_use_path_audit&assignee=support"),
            "load gateway incident review notes",
            checks,
        )
        gateway_review_notes = _get(gateway_review_notes_response, "data", "review_notes") or {}
        gateway_review_notes_md = client.get(
            "/api/v1/player/gateway-incidents/review-notes?reviewer=player_use_path_audit&format=markdown"
        )
        gateway_review_notes_csv = client.get(
            "/api/v1/player/gateway-incidents/review-notes?reviewer=player_use_path_audit&format=csv"
        )
        gateway_review_note_closed = _json(
            client.post(
                f"/api/v1/player/gateway-incidents/review-notes/{_get(gateway_review_note, 'data', 'review_note', 'note_id')}/status",
                json={
                    "status": "closed",
                    "reviewer": "player_use_path_audit",
                    "assignee": "support",
                    "note": "Audit closed gateway incident follow-up after metadata review.",
                },
            ),
            "close gateway incident review note",
            checks,
        )
        _add(
            checks,
            "gateway_incident_review_notes",
            "Gateway incident review notes let support annotate, assign, close, and export metadata-only follow-up state.",
            _get(gateway_review_note, "data", "review_note", "schema_version")
            == "gw2radar.gateway_incident_review_note.v1"
            and _get(gateway_review_note, "data", "review_note", "status") == "assigned"
            and gateway_review_notes.get("schema_version") == "gw2radar.gateway_incident_review_note_list.v1"
            and gateway_review_notes.get("assigned_count", 0) >= 1
            and _get(gateway_review_note_closed, "data", "review_note", "status") == "closed"
            and gateway_review_notes_md.status_code == 200
            and "# Gateway Incident Review Notes" in gateway_review_notes_md.text
            and gateway_review_notes_csv.status_code == 200
            and "note_id,snapshot_id,status,reviewer,assignee" in gateway_review_notes_csv.text
            and "secret-key" not in json.dumps(gateway_review_notes).lower(),
            "mature_gateway_incident_review_notes",
            f"{len(gateway_review_notes.get('notes', []))} notes with assigned and closed lifecycle evidence.",
        )
        support_case_incident_dashboard_response = _json(
            client.get("/api/v1/player/support-case/incident-dashboard?limit=20"),
            "load support case incident dashboard",
            checks,
        )
        support_case_incident_dashboard = _get(
            support_case_incident_dashboard_response,
            "data",
            "support_case_incident_dashboard",
        ) or {}
        support_case_incident_dashboard_md = client.get(
            "/api/v1/player/support-case/incident-dashboard?format=markdown&limit=20"
        )
        support_case_incident_dashboard_csv = client.get(
            "/api/v1/player/support-case/incident-dashboard?format=csv&limit=20"
        )
        _add(
            checks,
            "support_case_incident_dashboard",
            "Support case incident dashboard aggregates gateway incident notes, support audits, and handoff readiness into one operator view.",
            support_case_incident_dashboard.get("schema_version") == "gw2radar.support_case_incident_dashboard.v1"
            and support_case_incident_dashboard.get("gateway_note_count", 0) >= 1
            and support_case_incident_dashboard.get("handoff_ready") in {True, False}
            and {"gateway_history", "gateway_notes", "support_audits", "handoff_readiness"}
            <= {card.get("card_id") for card in support_case_incident_dashboard.get("status_cards", [])}
            and support_case_incident_dashboard_md.status_code == 200
            and "# Support Case Incident Dashboard" in support_case_incident_dashboard_md.text
            and support_case_incident_dashboard_csv.status_code == 200
            and "ready,maturity_label,support_status" in support_case_incident_dashboard_csv.text
            and "secret-key" not in json.dumps(support_case_incident_dashboard).lower(),
            "mature_support_case_incident_dashboard",
            f"{len(support_case_incident_dashboard.get('status_cards', []))} cards with status {support_case_incident_dashboard.get('support_status', 'missing')}.",
        )
        support_case_incident_packet_response = _json(
            client.post("/api/v1/player/support-case/incident-packet?limit=20"),
            "write support case incident packet",
            checks,
        )
        support_case_incident_packet = _get(
            support_case_incident_packet_response,
            "data",
            "support_case_incident_packet",
        ) or {}
        support_case_incident_packets_response = _json(
            client.get("/api/v1/player/support-case/incident-packet?limit=10"),
            "list support case incident packets",
            checks,
        )
        support_case_incident_packet_id = support_case_incident_packet.get("packet_id", "")
        support_case_incident_packet_manifest = client.get(
            f"/api/v1/player/support-case/incident-packet/{support_case_incident_packet_id}/manifest.json"
        )
        support_case_incident_packet_markdown = client.get(
            f"/api/v1/player/support-case/incident-packet/{support_case_incident_packet_id}/dashboard.md"
        )
        support_case_incident_packet_blocked = client.get(
            f"/api/v1/player/support-case/incident-packet/{support_case_incident_packet_id}/../manifest.json"
        )
        _add(
            checks,
            "support_case_incident_packet",
            "Support case incident packet writes dashboard JSON, Markdown, CSV, and manifest files with checksums and path-safe retrieval.",
            support_case_incident_packet.get("schema_version")
            == "gw2radar.support_case_incident_packet_manifest.v1"
            and support_case_incident_packet.get("file_count") == 4
            and len(str(support_case_incident_packet.get("checksum_sha256", ""))) == 64
            and support_case_incident_packet.get("contains_raw_key") is False
            and support_case_incident_packet.get("contains_private_source_payload") is False
            and {"dashboard.json", "dashboard.md", "dashboard.csv", "manifest.json"}
            == {file.get("file_name") for file in support_case_incident_packet.get("files", [])}
            and _get(support_case_incident_packets_response, "data", "support_case_incident_packets", 0, "packet_id")
            == support_case_incident_packet_id
            and support_case_incident_packet_manifest.status_code == 200
            and "gw2radar.support_case_incident_packet_manifest.v1" in support_case_incident_packet_manifest.text
            and support_case_incident_packet_markdown.status_code == 200
            and "# Support Case Incident Dashboard" in support_case_incident_packet_markdown.text
            and support_case_incident_packet_blocked.status_code == 404
            and "secret-key" not in json.dumps(support_case_incident_packet).lower(),
            "mature_support_case_incident_packet",
            f"4 files with checksum {str(support_case_incident_packet.get('checksum_sha256', ''))[:12]}.",
        )
        support_case_incident_packet_zip_manifest_response = _json(
            client.get("/api/v1/player/support-case/incident-packet/bundle?format=manifest"),
            "load support case incident packet zip manifest",
            checks,
        )
        support_case_incident_packet_zip_manifest = _get(
            support_case_incident_packet_zip_manifest_response,
            "data",
            "support_case_incident_packet_zip_bundle",
        ) or {}
        support_case_incident_packet_zip = client.get("/api/v1/player/support-case/incident-packet/bundle")
        support_case_incident_packet_zip_verification_response = _json(
            client.post("/api/v1/player/support-case/incident-packet/bundle/verify"),
            "verify support case incident packet zip",
            checks,
        )
        support_case_incident_packet_zip_verification = _get(
            support_case_incident_packet_zip_verification_response,
            "data",
            "support_case_incident_packet_zip_verification",
        ) or {}
        _add(
            checks,
            "support_case_incident_packet_zip_verification",
            "Support case incident packet zip can be downloaded as a read-only transfer bundle and verified for checksum, schema, whitelist, and no-secret boundaries.",
            support_case_incident_packet_zip_manifest.get("schema_version")
            == "gw2radar.support_case_incident_packet_zip_manifest.v1"
            and support_case_incident_packet_zip_manifest.get("file_count") == 4
            and len(str(support_case_incident_packet_zip_manifest.get("checksum_sha256", ""))) == 64
            and support_case_incident_packet_zip.status_code == 200
            and support_case_incident_packet_zip.headers.get("x-checksum-sha256")
            == support_case_incident_packet_zip_manifest.get("checksum_sha256")
            and support_case_incident_packet_zip_verification.get("schema_version")
            == "gw2radar.support_case_incident_packet_zip_verification.v1"
            and support_case_incident_packet_zip_verification.get("ready") is True
            and support_case_incident_packet_zip_verification.get("file_count") == 4
            and "secret-key" not in json.dumps(support_case_incident_packet_zip_verification).lower(),
            "mature_support_case_incident_packet_zip_verification",
            f"zip checksum {str(support_case_incident_packet_zip_manifest.get('checksum_sha256', ''))[:12]} verified with {support_case_incident_packet_zip_verification.get('file_count', 0)} files.",
        )
        player_readiness = _json(client.get("/api/v1/player/readiness"), "load player readiness", checks)
        readiness = _get(player_readiness, "data", "readiness") or {}
        _add(
            checks,
            "player_readiness_action",
            "One-click player readiness action aggregates sync, account value, legendary, market, and build-fit bridge checks.",
            readiness.get("schema_version") == "gw2radar.player_readiness_summary.v1"
            and {"account_sync", "account_value", "legendary_planner", "market_radar", "build_fit_bridge"}
            <= {check.get("check_id") for check in readiness.get("checks", [])}
            and "api_key" not in json.dumps(readiness).lower(),
            "mature_dashboard_readiness",
            f"{readiness.get('readiness_label', 'missing')} at {readiness.get('readiness_score', 0)}/100 with {len(readiness.get('checks', []))} checks.",
        )
        readiness_md = client.get("/api/v1/player/readiness?format=markdown")
        readiness_csv = client.get("/api/v1/player/readiness?format=csv")
        _add(
            checks,
            "player_readiness_exports",
            "Player readiness can be exported as Markdown and CSV for support review and session comparison.",
            readiness_md.status_code == 200
            and "# Player Readiness Summary" in readiness_md.text
            and "## Checks" in readiness_md.text
            and readiness_csv.status_code == 200
            and "check_id,label,status,evidence,next_action" in readiness_csv.text
            and "summary_key,summary_value" in readiness_csv.text
            and "api_key" not in (readiness_md.text + readiness_csv.text).lower(),
            "mature_readiness_exports",
            "GET /api/v1/player/readiness supports markdown and csv formats without raw secret fields.",
        )
        first_history = _json(
            client.post("/api/v1/player/readiness/history?source=player_use_path_audit"),
            "save first player readiness history snapshot",
            checks,
        )
        second_history = _json(
            client.post("/api/v1/player/readiness/history?source=player_use_path_audit"),
            "save second player readiness history snapshot",
            checks,
        )
        readiness_history = _json(
            client.get("/api/v1/player/readiness/history?limit=10"),
            "load player readiness history",
            checks,
        )
        readiness_history_md = client.get("/api/v1/player/readiness/history?format=markdown")
        readiness_history_csv = client.get("/api/v1/player/readiness/history?format=csv")
        history = _get(readiness_history, "data", "history") or {}
        _add(
            checks,
            "player_readiness_history",
            "Player readiness history records privacy-safe snapshots and compares the latest two runs.",
            _get(first_history, "data", "snapshot", "schema_version") == "gw2radar.player_readiness_snapshot.v1"
            and _get(second_history, "data", "snapshot", "schema_version") == "gw2radar.player_readiness_snapshot.v1"
            and history.get("schema_version") == "gw2radar.player_readiness_history.v1"
            and len(history.get("snapshots", [])) >= 2
            and _get(history, "comparison", "schema_version") == "gw2radar.player_readiness_history_comparison.v1"
            and readiness_history_md.status_code == 200
            and "# Player Readiness History" in readiness_history_md.text
            and readiness_history_csv.status_code == 200
            and "snapshot_id,created_at,source,readiness_label,readiness_score,check_id,check_status"
            in readiness_history_csv.text
            and "api_key" not in json.dumps(history).lower()
            and "api_key" not in (readiness_history_md.text + readiness_history_csv.text).lower(),
            "mature_readiness_history",
            f"{len(history.get('snapshots', []))} snapshots with comparison {(_get(history, 'comparison', 'status') or 'missing')}.",
        )
        account_value = _json(client.get("/api/v1/player/account-value"), "load account value snapshot", checks)
        value_snapshot = _get(account_value, "data", "account_value_snapshot") or {}
        bridge = _get(value_snapshot, "diagnostics") or {}
        _add(
            checks,
            "account_value_diagnostics",
            "Account value snapshot exposes diagnostics for price coverage, source insights, remediation, and no-secret boundaries.",
            value_snapshot.get("schema_version") == "gw2radar.account_value_snapshot.v1"
            and bridge.get("schema_version") == "gw2radar.account_value_diagnostics.v1"
            and isinstance(bridge.get("source_insights"), list)
            and isinstance(bridge.get("remediation_actions"), list)
            and "never places orders" in " ".join(value_snapshot.get("safety_boundaries", [])),
            "mature_evidence_spine",
            "GET /api/v1/player/account-value returns account_value_snapshot.diagnostics.",
        )
        first_value_history = _json(
            client.post("/api/v1/player/account-value/history?source=player_use_path_audit"),
            "save first account value history snapshot",
            checks,
        )
        second_value_history = _json(
            client.post("/api/v1/player/account-value/history?source=player_use_path_audit"),
            "save second account value history snapshot",
            checks,
        )
        value_history_response = _json(
            client.get("/api/v1/player/account-value/history?limit=10"),
            "load account value history",
            checks,
        )
        value_history_md = client.get("/api/v1/player/account-value/history?format=markdown")
        value_history_csv = client.get("/api/v1/player/account-value/history?format=csv")
        value_history = _get(value_history_response, "data", "history") or {}
        _add(
            checks,
            "account_value_history",
            "Account value history records privacy-safe value coverage snapshots and compares the latest two runs.",
            _get(first_value_history, "data", "snapshot", "schema_version") == "gw2radar.account_value_history_snapshot.v1"
            and _get(second_value_history, "data", "snapshot", "schema_version") == "gw2radar.account_value_history_snapshot.v1"
            and value_history.get("schema_version") == "gw2radar.account_value_history.v1"
            and len(value_history.get("snapshots", [])) >= 2
            and _get(value_history, "comparison", "schema_version") == "gw2radar.account_value_history_comparison.v1"
            and value_history_md.status_code == 200
            and "# Account Value History" in value_history_md.text
            and value_history_csv.status_code == 200
            and "snapshot_id,created_at,source,total_value_buy_copper" in value_history_csv.text
            and "api_key" not in json.dumps(value_history).lower()
            and "api_key" not in (value_history_md.text + value_history_csv.text).lower(),
            "mature_value_history",
            f"{len(value_history.get('snapshots', []))} snapshots with comparison {(_get(value_history, 'comparison', 'status') or 'missing')}.",
        )
        history_correlation = _json(
            client.get("/api/v1/player/history/correlation?limit=10"),
            "load player history correlation",
            checks,
        )
        correlation = _get(history_correlation, "data", "correlation") or {}
        correlation_md = client.get("/api/v1/player/history/correlation?format=markdown")
        correlation_csv = client.get("/api/v1/player/history/correlation?format=csv")
        _add(
            checks,
            "player_history_correlation",
            "Readiness and account value histories are correlated into one privacy-safe explanation view.",
            correlation.get("schema_version") == "gw2radar.player_history_correlation.v1"
            and correlation.get("readiness_snapshot_count", 0) >= 2
            and correlation.get("account_value_snapshot_count", 0) >= 2
            and isinstance(correlation.get("correlation_notes"), list)
            and isinstance(correlation.get("next_actions"), list)
            and correlation_md.status_code == 200
            and "# Player History Correlation" in correlation_md.text
            and correlation_csv.status_code == 200
            and "readiness_score_delta" in correlation_csv.text
            and "price_coverage_delta" in correlation_csv.text
            and "api_key" not in json.dumps(correlation).lower()
            and "api_key" not in (correlation_md.text + correlation_csv.text).lower(),
            "mature_history_correlation",
            f"{correlation.get('status', 'missing')} with readiness delta {correlation.get('readiness_score_delta', 0)} and price coverage delta {correlation.get('price_coverage_delta', 0)}.",
        )
        session_packet_response = _json(
            client.get("/api/v1/player/session-packet?limit=10"),
            "load player session packet",
            checks,
        )
        session_packet = _get(session_packet_response, "data", "session_packet") or {}
        session_packet_md = client.get("/api/v1/player/session-packet?format=markdown")
        session_packet_csv = client.get("/api/v1/player/session-packet?format=csv")
        _add(
            checks,
            "player_session_packet",
            "Player session packet bundles readiness, value, correlation, and debug-safe support prompts.",
            session_packet.get("schema_version") == "gw2radar.player_session_packet.v1"
            and _get(session_packet, "history_correlation", "schema_version") == "gw2radar.player_history_correlation.v1"
            and _get(session_packet, "gateway_incident_history", "schema_version")
            == "gw2radar.gateway_incident_history.v1"
            and _get(session_packet, "export_manifest", "gateway_incident_snapshot_count",) >= 2
            and _get(session_packet, "export_manifest", "contains_raw_key") is False
            and _get(session_packet, "export_manifest", "contains_private_source_payload") is False
            and isinstance(session_packet.get("debug_safe_evidence"), list)
            and isinstance(session_packet.get("support_review_prompts"), list)
            and session_packet_md.status_code == 200
            and "# Player Session Packet" in session_packet_md.text
            and "Gateway incident comparison" in session_packet_md.text
            and session_packet_csv.status_code == 200
            and "contains_raw_key" in session_packet_csv.text
            and "gateway_incident_snapshot_count" in session_packet_csv.text
            and "api_key" not in json.dumps(session_packet).lower()
            and "api_key" not in (session_packet_md.text + session_packet_csv.text).lower(),
            "mature_session_packet",
            f"{len(session_packet.get('debug_safe_evidence', []))} evidence rows and {len(session_packet.get('support_review_prompts', []))} support prompts.",
        )
        shutil.rmtree(SESSION_PACKET_ARTIFACT_ROOT, ignore_errors=True)
        artifact_response = _json(
            client.post("/api/v1/player/session-packet/artifacts?limit=10"),
            "write player session packet artifacts",
            checks,
        )
        artifact_bundle = _get(artifact_response, "data", "artifact_bundle") or {}
        artifact_id = artifact_bundle.get("artifact_id", "missing-artifact")
        artifact_index = _json(
            client.get("/api/v1/player/session-packet/artifacts?limit=10"),
            "load player session packet artifact index",
            checks,
        )
        artifact_manifest = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/manifest.json")
        artifact_markdown = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/packet.md")
        artifact_blocked = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/secret.txt")
        _add(
            checks,
            "player_session_packet_artifacts",
            "Player session packet can be written as local files with manifest, checksums, and path-safe retrieval.",
            artifact_bundle.get("schema_version") == "gw2radar.player_session_packet_artifact_bundle.v1"
            and artifact_bundle.get("file_count") == 4
            and len(str(artifact_bundle.get("checksum_sha256", ""))) == 64
            and {"packet.json", "packet.md", "packet.csv", "manifest.json"}
            == {file.get("file_name") for file in artifact_bundle.get("files", [])}
            and _get(artifact_index, "data", "artifact_bundles", 0, "artifact_id") == artifact_id
            and artifact_manifest.status_code == 200
            and "gw2radar.player_session_packet_artifact_manifest.v1" in artifact_manifest.text
            and artifact_markdown.status_code == 200
            and "# Player Session Packet" in artifact_markdown.text
            and artifact_blocked.status_code == 404
            and "api_key" not in json.dumps(artifact_bundle).lower()
            and "api_key" not in (artifact_manifest.text + artifact_markdown.text).lower(),
            "mature_session_packet_artifacts",
            f"{artifact_bundle.get('file_count', 0)} files with checksum {str(artifact_bundle.get('checksum_sha256', ''))[:12]}.",
        )
        debug_bundle = _json(
            client.post(
                "/account/debug-bundle",
                json={"active_view": "build", "active_build_id": "audit-build", "player_intent": "support_handoff"},
            ),
            "export account debug bundle for support handoff",
            checks,
        )
        support_handoff_response = _json(
            client.post("/api/v1/player/support-handoff?limit=10", json={"debug_bundle": debug_bundle}),
            "create player support handoff",
            checks,
        )
        support_handoff = _get(support_handoff_response, "data", "support_handoff") or {}
        support_handoff_md = client.post(
            "/api/v1/player/support-handoff?format=markdown&limit=10",
            json={"debug_bundle": debug_bundle},
        )
        support_handoff_csv = client.post(
            "/api/v1/player/support-handoff?format=csv&limit=10",
            json={"debug_bundle": debug_bundle},
        )
        _add(
            checks,
            "player_support_handoff",
            "Support handoff combines session packet artifacts with account debug review metadata.",
            support_handoff.get("schema_version") == "gw2radar.player_support_handoff_bundle.v1"
            and _get(support_handoff, "session_artifact_bundle", "schema_version")
            == "gw2radar.player_session_packet_artifact_bundle.v1"
            and _get(support_handoff, "debug_bundle_review", "schema_version") == "gw2radar.account_debug_bundle_review.v1"
            and _get(support_handoff, "manifest", "contains_raw_key") is False
            and _get(support_handoff, "manifest", "contains_raw_debug_bundle") is False
            and _get(support_handoff, "manifest", "contains_private_source_payload") is False
            and len(str(_get(support_handoff, "session_artifact_bundle", "checksum_sha256") or "")) == 64
            and bool(support_handoff.get("recommended_next_actions"))
            and support_handoff_md.status_code == 200
            and "# Player Support Handoff Bundle" in support_handoff_md.text
            and support_handoff_csv.status_code == 200
            and "support_status" in support_handoff_csv.text
            and "private_payload" not in json.dumps(support_handoff).lower()
            and "private_payload" not in (support_handoff_md.text + support_handoff_csv.text).lower(),
            "mature_support_handoff",
            f"{support_handoff.get('support_status', 'unknown')} with {len(support_handoff.get('recommended_next_actions', []))} next actions.",
        )
        shutil.rmtree(SUPPORT_HANDOFF_ARTIFACT_ROOT, ignore_errors=True)
        support_handoff_artifact_response = _json(
            client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle}),
            "write player support handoff artifacts",
            checks,
        )
        support_handoff_artifact = _get(support_handoff_artifact_response, "data", "artifact_bundle") or {}
        support_handoff_artifact_id = support_handoff_artifact.get("artifact_id", "missing-handoff-artifact")
        support_handoff_artifact_index = _json(
            client.get("/api/v1/player/support-handoff/artifacts?limit=10"),
            "load player support handoff artifact index",
            checks,
        )
        support_handoff_artifact_manifest = client.get(
            f"/api/v1/player/support-handoff/artifacts/{support_handoff_artifact_id}/manifest.json"
        )
        support_handoff_artifact_markdown = client.get(
            f"/api/v1/player/support-handoff/artifacts/{support_handoff_artifact_id}/handoff.md"
        )
        support_handoff_artifact_blocked = client.get(
            f"/api/v1/player/support-handoff/artifacts/{support_handoff_artifact_id}/secret.txt"
        )
        _add(
            checks,
            "player_support_handoff_artifacts",
            "Support handoff can be archived as local files with manifest, checksums, and path-safe retrieval.",
            support_handoff_artifact.get("schema_version") == "gw2radar.player_support_handoff_artifact_bundle.v1"
            and support_handoff_artifact.get("file_count") == 4
            and len(str(support_handoff_artifact.get("checksum_sha256", ""))) == 64
            and {"handoff.json", "handoff.md", "handoff.csv", "manifest.json"}
            == {file.get("file_name") for file in support_handoff_artifact.get("files", [])}
            and _get(support_handoff_artifact_index, "data", "artifact_bundles", 0, "artifact_id")
            == support_handoff_artifact_id
            and support_handoff_artifact_manifest.status_code == 200
            and "gw2radar.player_support_handoff_artifact_manifest.v1" in support_handoff_artifact_manifest.text
            and support_handoff_artifact_markdown.status_code == 200
            and "# Player Support Handoff Bundle" in support_handoff_artifact_markdown.text
            and support_handoff_artifact_blocked.status_code == 404
            and "private_payload" not in json.dumps(support_handoff_artifact).lower()
            and "private_payload"
            not in (support_handoff_artifact_manifest.text + support_handoff_artifact_markdown.text).lower(),
            "mature_support_handoff_artifacts",
            f"{support_handoff_artifact.get('file_count', 0)} files with checksum {str(support_handoff_artifact.get('checksum_sha256', ''))[:12]}.",
        )
        support_handoff_zip_manifest_response = _json(
            client.get("/api/v1/player/support-handoff/artifacts/bundle?format=manifest"),
            "load player support handoff zip manifest",
            checks,
        )
        support_handoff_zip_manifest = _get(support_handoff_zip_manifest_response, "data", "support_handoff_zip_bundle") or {}
        support_handoff_zip = client.get("/api/v1/player/support-handoff/artifacts/bundle")
        support_handoff_zip_names: set[str] = set()
        if support_handoff_zip.status_code == 200:
            support_handoff_zip_names = set(ZipFile(BytesIO(support_handoff_zip.content)).namelist())
        support_handoff_zip_verify_upload = _json(
            client.post(
                "/api/v1/player/support-handoff/artifacts/bundle/verify",
                content=support_handoff_zip.content if support_handoff_zip.status_code == 200 else b"",
                headers={"content-type": "application/zip"},
            ),
            "verify uploaded player support handoff zip",
            checks,
        )
        support_handoff_zip_verification = _get(
            support_handoff_zip_verify_upload,
            "data",
            "support_handoff_zip_verification",
        ) or {}
        support_handoff_zip_verify_latest = _json(
            client.post("/api/v1/player/support-handoff/artifacts/bundle/verify"),
            "verify latest player support handoff zip",
            checks,
        )
        latest_zip_verification = _get(
            support_handoff_zip_verify_latest,
            "data",
            "support_handoff_zip_verification",
        ) or {}
        _add(
            checks,
            "player_support_handoff_zip_verification",
            "Support handoff artifacts can be downloaded as a read-only zip and verified from bytes.",
            support_handoff_zip_manifest.get("schema_version") == "gw2radar.player_support_handoff_zip_manifest.v1"
            and support_handoff_zip_manifest.get("file_count") == 4
            and support_handoff_zip.status_code == 200
            and support_handoff_zip.headers.get("x-checksum-sha256") == support_handoff_zip_manifest.get("checksum_sha256")
            and support_handoff_zip_names
            == {
                "player_support_handoff/handoff.json",
                "player_support_handoff/handoff.md",
                "player_support_handoff/handoff.csv",
                "player_support_handoff/manifest.json",
            }
            and support_handoff_zip_verification.get("schema_version") == "gw2radar.player_support_handoff_zip_verification.v1"
            and support_handoff_zip_verification.get("ready") is True
            and latest_zip_verification.get("ready") is True
            and "secret-key" not in support_handoff_zip.content.decode("latin1").lower(),
            "mature_support_handoff_zip_verification",
            f"zip checksum {str(support_handoff_zip_manifest.get('checksum_sha256', ''))[:12]} verified with {support_handoff_zip_verification.get('file_count', 0)} files.",
        )
        support_handoff_zip_audit_record = _json(
            client.post(
                "/api/v1/player/support-handoff/artifacts/bundle/verification-audit",
                json={"reviewer": "player-audit", "notes": ["Use-path audit recorded support handoff zip verification."]},
            ),
            "record player support handoff zip verification audit",
            checks,
        )
        support_handoff_zip_audit = _json(
            client.get("/api/v1/player/support-handoff/artifacts/bundle/verification-audit?reviewer=player-audit&limit=10"),
            "load player support handoff zip verification audit",
            checks,
        )
        support_handoff_zip_audit_md = client.get(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit?format=markdown"
        )
        support_handoff_zip_audit_csv = client.get(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit?format=csv"
        )
        audit_record = _get(
            support_handoff_zip_audit_record,
            "data",
            "support_handoff_zip_verification_audit_record",
        ) or {}
        audit_list = _get(
            support_handoff_zip_audit,
            "data",
            "support_handoff_zip_verification_audit",
        ) or {}
        _add(
            checks,
            "player_support_handoff_zip_verification_audit",
            "Support handoff zip verification results are recorded as metadata-only audit records.",
            audit_record.get("schema_version") == "gw2radar.player_support_handoff_zip_verification_audit.v1"
            and audit_record.get("ready") is True
            and audit_record.get("reviewer") == "player-audit"
            and audit_record.get("file_count") == 4
            and audit_record.get("checksum_sha256") == support_handoff_zip_manifest.get("checksum_sha256")
            and _get(audit_list, "schema_version") == "gw2radar.player_support_handoff_zip_verification_audit_list.v1"
            and bool(audit_list.get("records"))
            and support_handoff_zip_audit_md.status_code == 200
            and "# Player Support Handoff Zip Verification Audit" in support_handoff_zip_audit_md.text
            and support_handoff_zip_audit_csv.status_code == 200
            and "audit_id,recorded_at,reviewer,ready,checksum_sha256" in support_handoff_zip_audit_csv.text
            and "secret-key" not in json.dumps(audit_list).lower()
            and "secret-key" not in (support_handoff_zip_audit_md.text + support_handoff_zip_audit_csv.text).lower(),
            "mature_support_handoff_zip_audit",
            f"{len(audit_list.get('records', []))} audit records for support handoff zip verification.",
        )
        support_handoff_readiness_response = _json(
            client.get("/api/v1/player/support-handoff/readiness-checklist"),
            "load player support handoff readiness checklist",
            checks,
        )
        support_handoff_readiness = _get(
            support_handoff_readiness_response,
            "data",
            "support_handoff_readiness_checklist",
        ) or {}
        support_handoff_readiness_md = client.get("/api/v1/player/support-handoff/readiness-checklist?format=markdown")
        support_handoff_readiness_csv = client.get("/api/v1/player/support-handoff/readiness-checklist?format=csv")
        _add(
            checks,
            "player_support_handoff_readiness",
            "Support handoff readiness checklist summarizes artifact, zip, verification, and audit gates.",
            support_handoff_readiness.get("schema_version")
            == "gw2radar.player_support_handoff_readiness_checklist.v1"
            and support_handoff_readiness.get("ready") is True
            and support_handoff_readiness.get("maturity_label") == "ready"
            and support_handoff_readiness.get("artifact_file_count") == 4
            and support_handoff_readiness.get("zip_file_count") == 4
            and support_handoff_readiness.get("zip_verification_ready") is True
            and int(support_handoff_readiness.get("verification_audit_count") or 0) >= 1
            and not support_handoff_readiness.get("missing_gates")
            and not support_handoff_readiness.get("blockers")
            and support_handoff_readiness_md.status_code == 200
            and "# Player Support Handoff Readiness Checklist" in support_handoff_readiness_md.text
            and support_handoff_readiness_csv.status_code == 200
            and "ready,maturity_label,latest_artifact_id" in support_handoff_readiness_csv.text
            and "secret-key" not in json.dumps(support_handoff_readiness).lower()
            and "secret-key" not in (support_handoff_readiness_md.text + support_handoff_readiness_csv.text).lower(),
            "mature_support_handoff_readiness",
            f"{support_handoff_readiness.get('maturity_label', 'unknown')} with {support_handoff_readiness.get('verification_audit_count', 0)} audit records.",
        )
        operator_packet_response = _json(
            client.get("/api/v1/player/support-handoff/operator-packet"),
            "load player support handoff operator packet",
            checks,
        )
        operator_packet = _get(operator_packet_response, "data", "support_handoff_operator_packet") or {}
        operator_packet_md = client.get("/api/v1/player/support-handoff/operator-packet?format=markdown")
        operator_packet_csv = client.get("/api/v1/player/support-handoff/operator-packet?format=csv")
        _add(
            checks,
            "player_support_handoff_operator_packet",
            "Support handoff operator packet packages readiness, audit summary, zip manifest, runbook, and safe next actions.",
            operator_packet.get("schema_version") == "gw2radar.player_support_handoff_operator_packet.v1"
            and operator_packet.get("ready") is True
            and operator_packet.get("maturity_label") == "ready"
            and _get(operator_packet, "checklist", "schema_version")
            == "gw2radar.player_support_handoff_readiness_checklist.v1"
            and _get(operator_packet, "zip_manifest", "schema_version")
            == "gw2radar.player_support_handoff_zip_manifest.v1"
            and int(_get(operator_packet, "audit_summary", "record_count") or 0) >= 1
            and "player_support_handoff.zip" in (operator_packet.get("transfer_files") or [])
            and bool(operator_packet.get("runbook_steps"))
            and bool(operator_packet.get("support_next_actions"))
            and operator_packet_md.status_code == 200
            and "# Player Support Handoff Operator Packet" in operator_packet_md.text
            and operator_packet_csv.status_code == 200
            and "packet_id,ready,maturity_label,zip_checksum_sha256" in operator_packet_csv.text
            and "secret-key" not in json.dumps(operator_packet).lower()
            and "secret-key" not in (operator_packet_md.text + operator_packet_csv.text).lower(),
            "mature_support_handoff_operator_packet",
            f"{len(operator_packet.get('runbook_steps', []))} runbook steps and {len(operator_packet.get('transfer_files', []))} transfer files.",
        )
        support_handoff_dashboard_response = _json(
            client.get("/api/v1/player/support-handoff/dashboard"),
            "load player support handoff dashboard",
            checks,
        )
        support_handoff_dashboard = _get(support_handoff_dashboard_response, "data", "support_handoff_dashboard") or {}
        support_handoff_dashboard_md = client.get("/api/v1/player/support-handoff/dashboard?format=markdown")
        support_handoff_dashboard_csv = client.get("/api/v1/player/support-handoff/dashboard?format=csv")
        dashboard_card_ids = {
            str(card.get("card_id"))
            for card in support_handoff_dashboard.get("status_cards", [])
            if isinstance(card, dict)
        }
        _add(
            checks,
            "player_support_handoff_dashboard",
            "Support handoff dashboard aggregates artifacts, zip verification, audit, readiness, and operator packet state.",
            support_handoff_dashboard.get("schema_version") == "gw2radar.player_support_handoff_dashboard.v1"
            and support_handoff_dashboard.get("ready") is True
            and support_handoff_dashboard.get("maturity_label") == "ready"
            and {
                "handoff_artifacts",
                "zip_bundle",
                "zip_verification",
                "verification_audit",
                "operator_packet",
            }.issubset(dashboard_card_ids)
            and int(support_handoff_dashboard.get("audit_record_count") or 0) >= 1
            and bool(support_handoff_dashboard.get("latest_operator_packet_id"))
            and len(str(support_handoff_dashboard.get("zip_checksum_sha256") or "")) == 64
            and support_handoff_dashboard_md.status_code == 200
            and "# Player Support Handoff Dashboard" in support_handoff_dashboard_md.text
            and support_handoff_dashboard_csv.status_code == 200
            and "ready,maturity_label,latest_artifact_id" in support_handoff_dashboard_csv.text
            and "secret-key" not in json.dumps(support_handoff_dashboard).lower()
            and "secret-key" not in (support_handoff_dashboard_md.text + support_handoff_dashboard_csv.text).lower(),
            "mature_support_handoff_dashboard",
            f"{len(dashboard_card_ids)} dashboard cards and {support_handoff_dashboard.get('audit_record_count', 0)} audit records.",
        )
        final_archive_response = _json(
            client.post("/api/v1/player/support-handoff/final-archive"),
            "write player support handoff final archive",
            checks,
        )
        final_archive = _get(final_archive_response, "data", "support_handoff_final_archive") or {}
        final_archive_list = _json(
            client.get("/api/v1/player/support-handoff/final-archive?limit=10"),
            "list player support handoff final archives",
            checks,
        )
        final_archive_zip_manifest = _json(
            client.get("/api/v1/player/support-handoff/final-archive/bundle?format=manifest"),
            "load player support handoff final archive zip manifest",
            checks,
        )
        final_archive_zip = client.get("/api/v1/player/support-handoff/final-archive/bundle")
        final_archive_zip_verify = _json(
            client.post(
                "/api/v1/player/support-handoff/final-archive/bundle/verify",
                content=final_archive_zip.content,
                headers={"content-type": "application/zip"},
            ),
            "verify player support handoff final archive zip",
            checks,
        )
        final_archive_file_names = {
            str(file.get("file_name"))
            for file in final_archive.get("files", [])
            if isinstance(file, dict)
        }
        final_archive_zip_bundle = _get(final_archive_zip_manifest, "data", "support_handoff_final_archive_zip_bundle") or {}
        final_archive_verification = _get(final_archive_zip_verify, "data", "support_handoff_final_archive_zip_verification") or {}
        _add(
            checks,
            "player_support_handoff_final_archive",
            "Support handoff final archive packages dashboard, operator packet, readiness checklist, and audit exports into deterministic files and a verified zip.",
            final_archive.get("schema_version") == "gw2radar.player_support_handoff_final_archive_manifest.v1"
            and final_archive.get("ready") is True
            and final_archive.get("maturity_label") == "ready"
            and {
                "dashboard.json",
                "dashboard.md",
                "operator_packet.md",
                "readiness_checklist.md",
                "verification_audit.csv",
                "manifest.json",
            }.issubset(final_archive_file_names)
            and len(final_archive.get("checksum_sha256") or "") == 64
            and _get(final_archive_list, "data", "support_handoff_final_archives", 0, "archive_id")
            == final_archive.get("archive_id")
            and final_archive_zip.status_code == 200
            and final_archive_zip.headers.get("content-type") == "application/zip"
            and final_archive_zip.headers.get("x-checksum-sha256") == final_archive_zip_bundle.get("checksum_sha256")
            and final_archive_zip_bundle.get("schema_version")
            == "gw2radar.player_support_handoff_final_archive_zip_manifest.v1"
            and final_archive_zip_bundle.get("file_count") == 6
            and final_archive_verification.get("schema_version")
            == "gw2radar.player_support_handoff_final_archive_zip_verification.v1"
            and final_archive_verification.get("ready") is True
            and final_archive_verification.get("file_count") == 6
            and "secret-key" not in json.dumps(final_archive).lower()
            and "secret-key" not in final_archive_zip.content.decode("latin1").lower(),
            "mature_support_handoff_final_archive",
            f"{len(final_archive_file_names)} files with zip checksum {str(final_archive_zip_bundle.get('checksum_sha256') or '')[:12]}.",
        )

        imported = _json(client.post("/api/v1/builds/import", json=_sample_build_import()), "import build", checks)
        build_id = _get(imported, "data", "build", "build_id") or "missing-build-id"
        fit = _json(
            client.post(
                "/api/v1/builds/fit",
                json={"build_id": build_id, "account_gear": _matching_account_gear()},
            ),
            "evaluate build fit",
            checks,
        )
        build_bridge = _get(fit, "data", "fit", "transition_plan", "account_value_evidence") or {}
        _add_bridge_check(checks, "build_fit_bridge", "Build Fit receives account value evidence bridge.", build_bridge)

        legendary = _json(client.post("/api/v1/legendary/recompute"), "recompute legendary planner", checks)
        legendary_bridge = _get(legendary, "data", "planner", "account_value_evidence") or {}
        _add_bridge_check(checks, "legendary_bridge", "Legendary Planner receives account value evidence bridge.", legendary_bridge)

        _json(
            client.post(
                "/api/v1/market/snapshots",
                json={
                    "item_id": "gw2:item:mystic_coin",
                    "item_name": "Mystic Coin",
                    "buy_price_copper": 12000,
                    "sell_price_copper": 12500,
                    "volume": 10000,
                },
            ),
            "record market snapshot",
            checks,
        )
        market = _json(client.get("/api/v1/market/signals?goal_id=gw2:goal:aurora"), "load market signals", checks)
        market_bridge = _get(market, "data", "account_value_evidence") or {}
        _add_bridge_check(checks, "market_bridge", "Market Radar signals expose account value evidence bridge.", market_bridge)

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "build_fit_report")

        build_report = _json(
            client.post(
                "/api/v1/builds/report",
                json={"build_id": build_id, "account_gear": _matching_account_gear(), "format": "markdown"},
            ),
            "generate build report",
            checks,
        )
        job = _get(build_report, "data", "job") or {}
        artifact_path = Path(str(job.get("artifact_path") or ""))
        manifest_path = Path(str(job.get("manifest_path") or ""))
        manifest = _read_json(manifest_path)
        _add(
            checks,
            "report_export_bridge",
            "Paid report artifact and manifest include Account Value Evidence Bridge without raw private payloads.",
            job.get("status") == "succeeded"
            and artifact_path.exists()
            and manifest.get("account_value_snapshot", {}).get("evidence_bridge", {}).get("schema_version")
            == "gw2radar.account_value_evidence_bridge.v1"
            and "api_key" not in json.dumps(manifest).lower(),
            "mature_export_metadata",
            "POST /api/v1/builds/report writes report_manifest.json account_value_snapshot.evidence_bridge.",
        )

        _write_audit(checks)
    except Exception as exc:  # pragma: no cover - harness defensive reporting
        checks.append(
            AuditCheck(
                check_id="unexpected_error",
                label="Unexpected audit harness error.",
                passed=False,
                maturity="blocked",
                evidence=str(exc),
                limitation="The harness crashed before completing all checks.",
            )
        )
        _write_audit(checks)
    finally:
        market_route.gateway_factory = original_market_gateway_factory
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "outputs", ignore_errors=True)
        shutil.rmtree(SESSION_PACKET_ARTIFACT_ROOT, ignore_errors=True)
        shutil.rmtree(SUPPORT_HANDOFF_ARTIFACT_ROOT, ignore_errors=True)
        shutil.rmtree(SUPPORT_HANDOFF_FINAL_ARCHIVE_ROOT, ignore_errors=True)

    failed = [check for check in checks if not check.passed]
    if failed:
        print("FAIL: GW2Radar player use-path completeness audit failed")
        for check in failed:
            print(f"- {check.check_id}: {check.evidence}")
        print(f"Audit written to {AUDIT_PATH}")
        return 1
    print("PASS: GW2Radar player use-path completeness audit succeeded")
    print(f"Audit written to {AUDIT_PATH}")
    return 0


def _json(response, label: str, checks: list[AuditCheck]) -> dict:
    if response.status_code != 200:
        checks.append(
            AuditCheck(
                check_id=f"http_{label.replace(' ', '_')}",
                label=label,
                passed=False,
                maturity="blocked",
                evidence=f"HTTP {response.status_code}: {response.text[:240]}",
                limitation="Endpoint did not return a successful response.",
            )
        )
        return {}
    try:
        return response.json()
    except ValueError:
        checks.append(
            AuditCheck(
                check_id=f"json_{label.replace(' ', '_')}",
                label=label,
                passed=False,
                maturity="blocked",
                evidence="Response was not JSON.",
                limitation="Endpoint contract was not machine-auditable.",
            )
        )
        return {}


def _add(
    checks: list[AuditCheck],
    check_id: str,
    label: str,
    passed: bool,
    maturity: str,
    evidence: str,
    limitation: str = "None for MVP depth.",
) -> None:
    checks.append(AuditCheck(check_id, label, passed, maturity if passed else "blocked", evidence, limitation))


def _add_bridge_check(checks: list[AuditCheck], check_id: str, label: str, bridge: dict) -> None:
    _add(
        checks,
        check_id,
        label,
        bridge.get("schema_version") == "gw2radar.account_value_evidence_bridge.v1"
        and "remediation_summary" in bridge
        and "source_summary" in bridge
        and "api_key" not in json.dumps(bridge).lower()
        and "private_payload" not in json.dumps(bridge).lower(),
        "mature_semantic_bridge",
        f"{bridge.get('schema_version', 'missing')} with {len(bridge.get('source_summary', []))} source summaries and {len(bridge.get('remediation_summary', []))} remediation items.",
    )


def _get(data: dict, *path):
    cursor = data
    for key in path:
        if isinstance(cursor, list) and isinstance(key, int):
            if key < 0 or key >= len(cursor):
                return None
            cursor = cursor[key]
            continue
        if not isinstance(cursor, dict):
            return None
        cursor = cursor.get(key)
    return cursor


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_audit(checks: list[AuditCheck]) -> None:
    passed = [check for check in checks if check.passed]
    failed = [check for check in checks if not check.passed]
    label = "ready" if not failed else "blocked"
    score = round(len(passed) / len(checks) * 100, 2) if checks else 0.0
    lines = [
        "# Player Use Path Completeness Audit",
        "",
        "- Schema: gw2radar.player_use_path_completeness_audit.v1",
        f"- Maturity label: {label}",
        f"- Readiness score: {score}",
        f"- Passed checks: {len(passed)}",
        f"- Failed checks: {len(failed)}",
        "- Privacy boundary: raw API keys and private source payloads must not appear in this audit.",
        "",
        "## Executable Checklist",
        "",
        "| Check | Status | Maturity | Evidence | Limitation |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(
            f"| `{check.check_id}` | {status} | {check.maturity} | {_md(check.evidence)} | {_md(check.limitation)} |"
        )
    lines.extend(
        [
            "",
            "## Semantic Graph Summary",
            "",
            "- `ApiKeyConnection` gates account-aware recommendations through permission checks and sync status.",
            "- `AccountFirstRunSummary` explains empty account-aware result states across missing key, limited permissions, sync queue, and private-layer write gates.",
            "- `AccountSyncWorkerHealth` exposes bounded worker-loop health, queue depth, retry depth, failed depth, latest jobs, and safe next actions.",
            "- `AccountSyncGatewayContract` returns structured user-facing error envelopes for missing key, permission, rate-limit, and API client failure states.",
            "- `PublicRefreshWorkerHealth` exposes public static refresh queue depth, retry depth, failed depth, latest jobs, and safe next actions.",
            "- `MarketPriceRefreshDiagnostics` explains official commerce price refresh status, retryability, player action, and no-trading boundary.",
            "- `GatewayIncidentTimeline` correlates account sync, public refresh, and market price refresh metadata into one player-facing incident view.",
            "- `GatewayIncidentHistory` persists metadata-only incident snapshots, compares retry/failure deltas, and exports Markdown/CSV support evidence.",
            "- `GatewayIncidentReviewNote` lets support annotate, assign, close, and export metadata-only incident follow-up state.",
            "- `SupportCaseIncidentDashboard` aggregates gateway incidents, support review audits, and handoff readiness into one operator case view.",
            "- `SupportCaseIncidentPacket` writes dashboard JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.",
            "- `SupportCaseIncidentPacketZipVerification` downloads and verifies read-only packet zip bundles for checksum, schema, whitelist, and no-secret boundaries.",
            "- `PrivatePlayerState` stores private account summaries separately from public game and KB layers.",
            "- `AccountValueSnapshot` normalizes holdings, price coverage, source diagnostics, and remediation actions.",
            "- `AccountValueHistory` stores privacy-safe value coverage snapshots and compares value/coverage/freshness deltas.",
            "- `AccountValueEvidenceBridge` carries the same summary-only evidence into Build Fit, Legendary Planner, Market Radar, and report artifacts.",
            "- `PlayerReadinessSummary` aggregates sync, account value, Legendary, Market, and Build Fit bridge checks into one dashboard action.",
            "- `PlayerReadinessExport` renders the readiness summary as Markdown and CSV for player/support comparison across sessions.",
            "- `PlayerReadinessHistory` stores privacy-safe readiness snapshots and compares the latest two score/check states.",
            "- `PlayerHistoryCorrelation` explains readiness deltas alongside account value, price coverage, and warning deltas.",
            "- `PlayerSessionPacket` packages readiness, value, correlation, gateway incident history, and debug-safe support prompts without raw private payloads.",
            "- `PlayerSessionPacketArtifacts` writes local JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.",
            "- `PlayerSupportHandoffBundle` combines packet artifact metadata with account debug review status for privacy-safe support triage.",
            "- `PlayerSupportHandoffArtifacts` archives handoff JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.",
            "- `PlayerSupportHandoffZipVerification` transfers handoff artifacts as a read-only zip and verifies schema, checksum, whitelist, and no-secret boundaries from bytes.",
            "- `PlayerSupportHandoffZipVerificationAudit` records verification outcomes as metadata-only support evidence without storing zip bytes.",
            "- `PlayerSupportHandoffReadinessChecklist` summarizes artifact, zip, verification, and audit gates for support operators.",
            "- `PlayerSupportHandoffOperatorPacket` packages the readiness checklist, audit summary, zip manifest, runbook, and transfer files for support workflows.",
            "- `PlayerSupportHandoffDashboard` aggregates artifacts, zip verification, audit, readiness, and operator packet state into one support case view.",
            "- `PlayerSupportHandoffFinalArchiveManifest` packages dashboard, operator packet, readiness checklist, and audit exports into deterministic local files and a verified zip.",
            "- `ReportArtifactManifest` records bridge metadata without storing raw API keys or unredacted private payloads.",
            "",
            "## Known Limits",
            "",
            "- Official price refresh depends on the external GW2 API gateway; this audit verifies the UI/API contract and dedicated refresh tests cover delayed gateway behavior.",
            "- The audit uses demo graph and deterministic local database data; real player accounts can still encounter GW2 API rate limits or missing optional permissions.",
            "- UI validation here is static plus API-level; full browser visual polish should remain covered by browser screenshot checks when layout changes are substantial.",
            "",
            "## Next Priority",
            "",
            "Add metadata-only verification audit records for support case incident packet zip imports.",
            "",
        ]
    )
    AUDIT_PATH.write_text("\n".join(lines), encoding="utf-8")


def _md(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")[:420]


def _sample_build_import() -> dict:
    return {
        "name": "Power Virtuoso Audit Build",
        "source": {
            "name": "manual_player_use_path_audit",
            "url": "https://example.invalid/audit-build",
            "attribution": "Deterministic audit build data.",
        },
        "profession": "Mesmer",
        "specialization": "Virtuoso",
        "role": "DPS",
        "game_mode": "Strike",
        "patch_freshness_days": 20,
        "difficulty": "medium",
        "estimated_transition_cost_gold": 42,
        "requirements": [
            {"slot": "chest", "item_name": "Ascended Chest", "stat_combo": "Berserker", "required": True, "estimated_cost_gold": 20},
            {"slot": "weapon_1", "item_name": "Primary Weapon", "stat_combo": "Berserker", "required": True, "estimated_cost_gold": 20},
            {"slot": "relic", "item_name": "Power Relic", "stat_combo": "Power", "required": False, "estimated_cost_gold": 2},
        ],
    }


def _matching_account_gear() -> dict:
    return {
        "profession": "Mesmer",
        "specializations": ["Virtuoso"],
        "preferred_game_modes": ["Strike"],
        "difficulty_preference": "medium",
        "wallet_gold": 120,
        "gear": [
            {"slot": "chest", "item_name": "Owned Ascended Chest", "stat_combo": "Berserker"},
            {"slot": "weapon_1", "item_name": "Owned Dagger", "stat_combo": "Berserker"},
            {"slot": "relic", "item_name": "Owned Power Relic", "stat_combo": "Power", "equipment_category": "relic"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
