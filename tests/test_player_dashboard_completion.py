import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.market_radar import PriceSnapshotInput, record_price_snapshot
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_player_dashboard_returns_best_actions_and_freshness_annotations() -> None:
    temp_dir = Path(".test_tmp") / f"player-dashboard-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'dashboard.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        response = client.get("/api/v1/player/dashboard")
        payload = response.json()["data"]["dashboard"]

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.player_dashboard.v1"
        assert len(payload["today_best_actions"]) >= 1
        assert len(payload["this_week_actions"]) >= 5
        assert any(item["subject"] == "Account Snapshot" for item in payload["data_freshness"])
        assert all(item["safety_boundary"] == "informational_manual_actions_only" for item in payload["today_best_actions"])
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_readiness_endpoint_aggregates_commercial_path_checks() -> None:
    temp_dir = Path(".test_tmp") / f"player-readiness-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'readiness.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        response = client.get("/api/v1/player/readiness")
        readiness = response.json()["data"]["readiness"]
        markdown = client.get("/api/v1/player/readiness?format=markdown")
        csv = client.get("/api/v1/player/readiness?format=csv")
        check_ids = {check["check_id"] for check in readiness["checks"]}

        assert response.status_code == 200
        assert readiness["schema_version"] == "gw2radar.player_readiness_summary.v1"
        assert readiness["readiness_label"] in {"ready", "needs_review", "blocked"}
        assert readiness["readiness_score"] >= 0
        assert {"account_sync", "account_value", "legendary_planner", "market_radar", "build_fit_bridge"} <= check_ids
        assert "api_key" not in str(readiness).lower()
        assert "never places trades" in " ".join(readiness["safety_boundaries"])
        assert markdown.status_code == 200
        assert "# Player Readiness Summary" in markdown.text
        assert "## Checks" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "check_id,label,status,evidence,next_action" in csv.text
        assert "summary_key,summary_value" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_readiness_history_records_and_exports_snapshot_comparison() -> None:
    temp_dir = Path(".test_tmp") / f"player-readiness-history-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'readiness-history.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        first = client.post("/api/v1/player/readiness/history?source=test_snapshot")
        second = client.post("/api/v1/player/readiness/history?source=test_snapshot")
        history_response = client.get("/api/v1/player/readiness/history?limit=10")
        history = history_response.json()["data"]["history"]
        markdown = client.get("/api/v1/player/readiness/history?format=markdown")
        csv = client.get("/api/v1/player/readiness/history?format=csv")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["snapshot"]["schema_version"] == "gw2radar.player_readiness_snapshot.v1"
        assert history_response.status_code == 200
        assert history["schema_version"] == "gw2radar.player_readiness_history.v1"
        assert len(history["snapshots"]) == 2
        assert history["comparison"]["schema_version"] == "gw2radar.player_readiness_history_comparison.v1"
        assert history["comparison"]["status"] in {"unchanged", "changed", "improved", "regressed"}
        assert "api_key" not in str(history).lower()
        assert markdown.status_code == 200
        assert "# Player Readiness History" in markdown.text
        assert "## Snapshots" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "snapshot_id,created_at,source,readiness_label,readiness_score,check_id,check_status" in csv.text
        assert "comparison_key,comparison_value" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_account_value_endpoint_exports_dashboard_ready_snapshot() -> None:
    temp_dir = Path(".test_tmp") / f"player-account-value-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account-value.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        response = client.get("/api/v1/player/account-value")
        snapshot = response.json()["data"]["account_value_snapshot"]
        markdown = client.get("/api/v1/player/account-value?format=markdown")
        csv = client.get("/api/v1/player/account-value?format=csv")

        assert response.status_code == 200
        assert snapshot["schema_version"] == "gw2radar.account_value_snapshot.v1"
        assert "summary" in snapshot
        assert snapshot["diagnostics"]["schema_version"] == "gw2radar.account_value_diagnostics.v1"
        assert snapshot["diagnostics"]["source_insights"]
        assert snapshot["diagnostics"]["remediation_actions"]
        assert snapshot["diagnostics"]["price_coverage_percent"] >= 0
        assert any(action["action_id"] in {"refresh_official_prices", "review_value_sources"} for action in snapshot["diagnostics"]["remediation_actions"])
        assert isinstance(snapshot["by_location"], list)
        assert isinstance(snapshot["by_status"], list)
        assert "never automates trades" in " ".join(snapshot["safety_boundaries"])
        assert markdown.status_code == 200
        assert "# Account Value Snapshot" in markdown.text
        assert "## Source Diagnostics" in markdown.text
        assert "## Remediation Actions" in markdown.text
        assert csv.status_code == 200
        assert "holding_id,entity_id,name,location,status" in csv.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_account_value_history_records_and_exports_snapshot_comparison() -> None:
    temp_dir = Path(".test_tmp") / f"player-account-value-history-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account-value-history.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        first = client.post("/api/v1/player/account-value/history?source=test_snapshot")
        second = client.post("/api/v1/player/account-value/history?source=test_snapshot")
        history_response = client.get("/api/v1/player/account-value/history?limit=10")
        history = history_response.json()["data"]["history"]
        markdown = client.get("/api/v1/player/account-value/history?format=markdown")
        csv = client.get("/api/v1/player/account-value/history?format=csv")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["snapshot"]["schema_version"] == "gw2radar.account_value_history_snapshot.v1"
        assert history_response.status_code == 200
        assert history["schema_version"] == "gw2radar.account_value_history.v1"
        assert len(history["snapshots"]) == 2
        assert history["comparison"]["schema_version"] == "gw2radar.account_value_history_comparison.v1"
        assert history["comparison"]["status"] in {"unchanged", "changed", "improved", "needs_review"}
        assert "api_key" not in str(history).lower()
        assert markdown.status_code == 200
        assert "# Account Value History" in markdown.text
        assert "## Snapshots" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "snapshot_id,created_at,source,total_value_buy_copper" in csv.text
        assert "comparison_key,comparison_value" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_history_correlation_combines_readiness_and_value_history() -> None:
    temp_dir = Path(".test_tmp") / f"player-history-correlation-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'history-correlation.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        assert client.post("/api/v1/player/readiness/history?source=test_correlation").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_correlation").status_code == 200
        assert client.post("/api/v1/player/readiness/history?source=test_correlation").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_correlation").status_code == 200

        response = client.get("/api/v1/player/history/correlation?limit=10")
        correlation = response.json()["data"]["correlation"]
        markdown = client.get("/api/v1/player/history/correlation?format=markdown")
        csv = client.get("/api/v1/player/history/correlation?format=csv")

        assert response.status_code == 200
        assert correlation["schema_version"] == "gw2radar.player_history_correlation.v1"
        assert correlation["status"] in {"unchanged", "changed", "improved", "needs_review"}
        assert correlation["readiness_snapshot_count"] >= 2
        assert correlation["account_value_snapshot_count"] >= 2
        assert isinstance(correlation["correlation_notes"], list)
        assert isinstance(correlation["next_actions"], list)
        assert "api_key" not in str(correlation).lower()
        assert markdown.status_code == 200
        assert "# Player History Correlation" in markdown.text
        assert "## Correlation Notes" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "metric,value" in csv.text
        assert "readiness_score_delta" in csv.text
        assert "price_coverage_delta" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_session_packet_bundles_debug_safe_support_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"player-session-packet-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'session-packet.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        assert client.post("/api/v1/player/readiness/history?source=test_packet").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_packet").status_code == 200
        assert client.post("/api/v1/player/readiness/history?source=test_packet").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_packet").status_code == 200

        response = client.get("/api/v1/player/session-packet?limit=10")
        packet = response.json()["data"]["session_packet"]
        markdown = client.get("/api/v1/player/session-packet?format=markdown")
        csv = client.get("/api/v1/player/session-packet?format=csv")

        assert response.status_code == 200
        assert packet["schema_version"] == "gw2radar.player_session_packet.v1"
        assert packet["readiness_summary"]["schema_version"] == "gw2radar.player_readiness_summary.v1"
        assert packet["account_value_summary"]["schema_version"] == "gw2radar.account_value_snapshot.v1"
        assert packet["history_correlation"]["schema_version"] == "gw2radar.player_history_correlation.v1"
        assert packet["export_manifest"]["contains_raw_key"] is False
        assert packet["export_manifest"]["contains_private_source_payload"] is False
        assert packet["export_manifest"]["contains_full_holding_list"] is False
        assert packet["debug_safe_evidence"]
        assert packet["support_review_prompts"]
        assert "api_key" not in str(packet).lower()
        assert "private_payload" not in str(packet).lower()
        assert markdown.status_code == 200
        assert "# Player Session Packet" in markdown.text
        assert "## Debug-Safe Evidence" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "metric,value" in csv.text
        assert "contains_raw_key" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_session_packet_artifact_writer_manifest_and_safe_retrieval() -> None:
    temp_dir = Path(".test_tmp") / f"player-session-packet-artifact-{uuid4().hex}"
    artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'session-packet-artifact.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        assert client.post("/api/v1/player/readiness/history?source=test_artifact").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_artifact").status_code == 200
        assert client.post("/api/v1/player/readiness/history?source=test_artifact").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_artifact").status_code == 200

        created = client.post("/api/v1/player/session-packet/artifacts?limit=10")
        bundle = created.json()["data"]["artifact_bundle"]
        listed = client.get("/api/v1/player/session-packet/artifacts?limit=10")
        artifact_id = bundle["artifact_id"]
        manifest = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/manifest.json")
        packet_md = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/packet.md")
        blocked = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/../manifest.json")
        missing = client.get(f"/api/v1/player/session-packet/artifacts/{artifact_id}/secret.txt")

        assert created.status_code == 200
        assert bundle["schema_version"] == "gw2radar.player_session_packet_artifact_bundle.v1"
        assert bundle["file_count"] == 4
        assert len(bundle["checksum_sha256"]) == 64
        assert {file["file_name"] for file in bundle["files"]} == {"packet.json", "packet.md", "packet.csv", "manifest.json"}
        assert all(len(file["checksum_sha256"]) == 64 for file in bundle["files"])
        assert listed.status_code == 200
        assert listed.json()["data"]["artifact_bundles"][0]["artifact_id"] == artifact_id
        assert manifest.status_code == 200
        assert "gw2radar.player_session_packet_artifact_manifest.v1" in manifest.text
        assert packet_md.status_code == 200
        assert "# Player Session Packet" in packet_md.text
        assert "api_key" not in manifest.text.lower() + packet_md.text.lower()
        assert blocked.status_code == 404
        assert missing.status_code == 404
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(artifact_root, ignore_errors=True)


def test_player_support_handoff_combines_packet_artifact_and_debug_review() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-{uuid4().hex}"
    artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        assert client.post("/api/v1/player/readiness/history?source=test_handoff").status_code == 200
        assert client.post("/api/v1/player/account-value/history?source=test_handoff").status_code == 200
        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_handoff"},
        ).json()
        created = client.post("/api/v1/player/support-handoff?limit=10", json={"debug_bundle": debug_bundle})
        handoff = created.json()["data"]["support_handoff"]
        markdown = client.post("/api/v1/player/support-handoff?format=markdown&limit=10", json={"debug_bundle": debug_bundle})
        csv = client.post("/api/v1/player/support-handoff?format=csv&limit=10", json={"debug_bundle": debug_bundle})

        assert created.status_code == 200
        assert handoff["schema_version"] == "gw2radar.player_support_handoff_bundle.v1"
        assert handoff["session_artifact_bundle"]["schema_version"] == "gw2radar.player_session_packet_artifact_bundle.v1"
        assert handoff["session_artifact_bundle"]["file_count"] == 4
        assert len(handoff["session_artifact_bundle"]["checksum_sha256"]) == 64
        assert handoff["debug_bundle_review"]["schema_version"] == "gw2radar.account_debug_bundle_review.v1"
        assert handoff["debug_bundle_review"]["overall_status"] in {"needs_key", "ready", "frontend_flow_incomplete"}
        assert handoff["manifest"]["contains_raw_key"] is False
        assert handoff["manifest"]["contains_raw_debug_bundle"] is False
        assert handoff["manifest"]["contains_private_source_payload"] is False
        assert handoff["recommended_next_actions"]
        assert "private_payload" not in str(handoff).lower()
        assert markdown.status_code == 200
        assert "# Player Support Handoff Bundle" in markdown.text
        assert "## Evidence Chain" in markdown.text
        assert "private_payload" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "support_status" in csv.text
        assert "contains_raw_debug_bundle" in csv.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(artifact_root, ignore_errors=True)


def test_player_support_handoff_artifact_files_manifest_and_safe_retrieval() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-artifact-{uuid4().hex}"
    packet_artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    handoff_artifact_root = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff-artifact.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )

        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_archive"},
        ).json()
        created = client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle})
        bundle = created.json()["data"]["artifact_bundle"]
        listed = client.get("/api/v1/player/support-handoff/artifacts?limit=10")
        artifact_id = bundle["artifact_id"]
        manifest = client.get(f"/api/v1/player/support-handoff/artifacts/{artifact_id}/manifest.json")
        handoff_md = client.get(f"/api/v1/player/support-handoff/artifacts/{artifact_id}/handoff.md")
        blocked = client.get(f"/api/v1/player/support-handoff/artifacts/{artifact_id}/../manifest.json")
        missing = client.get(f"/api/v1/player/support-handoff/artifacts/{artifact_id}/secret.txt")

        assert created.status_code == 200
        assert bundle["schema_version"] == "gw2radar.player_support_handoff_artifact_bundle.v1"
        assert bundle["file_count"] == 4
        assert bundle["source_handoff_id"].startswith("player-support-handoff-")
        assert bundle["source_session_artifact_id"].startswith("player-session-packet-")
        assert len(bundle["checksum_sha256"]) == 64
        assert {file["file_name"] for file in bundle["files"]} == {"handoff.json", "handoff.md", "handoff.csv", "manifest.json"}
        assert all(len(file["checksum_sha256"]) == 64 for file in bundle["files"])
        assert listed.status_code == 200
        assert listed.json()["data"]["artifact_bundles"][0]["artifact_id"] == artifact_id
        assert manifest.status_code == 200
        assert "gw2radar.player_support_handoff_artifact_manifest.v1" in manifest.text
        assert '"contains_raw_debug_bundle": false' in manifest.text
        assert handoff_md.status_code == 200
        assert "# Player Support Handoff Bundle" in handoff_md.text
        assert "private_payload" not in manifest.text.lower() + handoff_md.text.lower()
        assert blocked.status_code == 404
        assert missing.status_code == 404
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)


def test_player_support_handoff_zip_bundle_download_and_verification_import() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-zip-{uuid4().hex}"
    packet_artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    handoff_artifact_root = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff-zip.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_zip"},
        ).json()
        assert client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle}).status_code == 200

        manifest = client.get("/api/v1/player/support-handoff/artifacts/bundle?format=manifest")
        bundle_zip = client.get("/api/v1/player/support-handoff/artifacts/bundle")
        uploaded_verify = client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verify",
            content=bundle_zip.content,
            headers={"content-type": "application/zip"},
        )
        latest_verify = client.post("/api/v1/player/support-handoff/artifacts/bundle/verify")

        assert manifest.status_code == 200
        bundle_manifest = manifest.json()["data"]["support_handoff_zip_bundle"]
        assert bundle_manifest["schema_version"] == "gw2radar.player_support_handoff_zip_manifest.v1"
        assert bundle_manifest["file_count"] == 4
        assert bundle_manifest["checksum_sha256"] == bundle_zip.headers["x-checksum-sha256"]
        assert bundle_zip.status_code == 200
        assert bundle_zip.headers["content-type"] == "application/zip"
        assert set(ZipFile(BytesIO(bundle_zip.content)).namelist()) == {
            "player_support_handoff/handoff.json",
            "player_support_handoff/handoff.md",
            "player_support_handoff/handoff.csv",
            "player_support_handoff/manifest.json",
        }
        assert "secret-key" not in bundle_zip.content.decode("latin1").lower()
        assert uploaded_verify.status_code == 200
        assert uploaded_verify.json()["data"]["support_handoff_zip_verification"]["ready"] is True
        assert latest_verify.status_code == 200
        assert latest_verify.json()["data"]["support_handoff_zip_verification"]["ready"] is True

        tampered_buffer = BytesIO()
        with ZipFile(BytesIO(bundle_zip.content), mode="r") as source_archive:
            with ZipFile(tampered_buffer, mode="w") as tampered_archive:
                for name in source_archive.namelist():
                    tampered_archive.writestr(name, source_archive.read(name))
                tampered_archive.writestr("player_support_handoff/secret.txt", "secret-key")
        tampered_verify = client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verify",
            content=tampered_buffer.getvalue(),
            headers={"content-type": "application/zip"},
        )
        tampered = tampered_verify.json()["data"]["support_handoff_zip_verification"]
        assert tampered_verify.status_code == 200
        assert tampered["ready"] is False
        assert any("non-whitelisted" in blocker for blocker in tampered["blockers"])
        assert any("secret marker" in blocker for blocker in tampered["blockers"])
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)


def test_player_support_handoff_zip_verification_audit_trail_exports_metadata_only() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-zip-audit-{uuid4().hex}"
    packet_artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    handoff_artifact_root = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff-zip-audit.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_audit"},
        ).json()
        assert client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle}).status_code == 200
        bundle_zip = client.get("/api/v1/player/support-handoff/artifacts/bundle")

        record = client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit",
            json={"reviewer": "support lead", "notes": ["Unit test recorded support handoff verification."]},
        )
        upload_record = client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit/upload?reviewer=upload%20lead",
            content=bundle_zip.content,
            headers={"content-type": "application/zip"},
        )
        listed = client.get("/api/v1/player/support-handoff/artifacts/bundle/verification-audit?limit=10")
        filtered = client.get("/api/v1/player/support-handoff/artifacts/bundle/verification-audit?reviewer=upload%20lead&limit=10")
        markdown = client.get("/api/v1/player/support-handoff/artifacts/bundle/verification-audit?format=markdown")
        csv = client.get("/api/v1/player/support-handoff/artifacts/bundle/verification-audit?format=csv")

        assert record.status_code == 200
        record_payload = record.json()["data"]["support_handoff_zip_verification_audit_record"]
        assert record_payload["schema_version"] == "gw2radar.player_support_handoff_zip_verification_audit.v1"
        assert record_payload["ready"] is True
        assert record_payload["reviewer"] == "support lead"
        assert record_payload["file_count"] == 4
        assert record_payload["checksum_sha256"] == bundle_zip.headers["x-checksum-sha256"]
        assert upload_record.status_code == 200
        assert upload_record.json()["data"]["support_handoff_zip_verification_audit_record"]["reviewer"] == "upload lead"
        assert listed.status_code == 200
        audit = listed.json()["data"]["support_handoff_zip_verification_audit"]
        assert audit["schema_version"] == "gw2radar.player_support_handoff_zip_verification_audit_list.v1"
        assert len(audit["records"]) >= 2
        assert filtered.status_code == 200
        assert filtered.json()["data"]["support_handoff_zip_verification_audit"]["records"][0]["reviewer"] == "upload lead"
        assert markdown.status_code == 200
        assert "# Player Support Handoff Zip Verification Audit" in markdown.text
        assert csv.status_code == 200
        assert "audit_id,recorded_at,reviewer,ready,checksum_sha256" in csv.text
        combined = str(audit) + markdown.text + csv.text
        assert "secret-key" not in combined.lower()
        assert "PK" not in csv.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)


def test_player_support_handoff_readiness_checklist_summarizes_transfer_gates() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-readiness-{uuid4().hex}"
    packet_artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    handoff_artifact_root = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff-readiness.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_readiness"},
        ).json()
        assert client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle}).status_code == 200
        assert client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit",
            json={"reviewer": "readiness", "notes": ["Readiness test recorded verification."]},
        ).status_code == 200

        response = client.get("/api/v1/player/support-handoff/readiness-checklist")
        markdown = client.get("/api/v1/player/support-handoff/readiness-checklist?format=markdown")
        csv = client.get("/api/v1/player/support-handoff/readiness-checklist?format=csv")
        checklist = response.json()["data"]["support_handoff_readiness_checklist"]

        assert response.status_code == 200
        assert checklist["schema_version"] == "gw2radar.player_support_handoff_readiness_checklist.v1"
        assert checklist["ready"] is True
        assert checklist["maturity_label"] == "ready"
        assert checklist["artifact_file_count"] == 4
        assert checklist["zip_file_count"] == 4
        assert checklist["zip_verification_ready"] is True
        assert checklist["verification_audit_count"] >= 1
        assert checklist["missing_gates"] == []
        assert checklist["blockers"] == []
        assert checklist["next_actions"]
        assert markdown.status_code == 200
        assert "# Player Support Handoff Readiness Checklist" in markdown.text
        assert csv.status_code == 200
        assert "ready,maturity_label,latest_artifact_id" in csv.text
        assert "secret-key" not in (str(checklist) + markdown.text + csv.text).lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)


def test_player_support_handoff_operator_packet_exports_runbook_metadata() -> None:
    temp_dir = Path(".test_tmp") / f"player-support-handoff-operator-{uuid4().hex}"
    packet_artifact_root = Path("src/gw2radar/reports/artifacts/player_session_packets")
    handoff_artifact_root = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)
        configure_database(f"sqlite:///{temp_dir / 'support-handoff-operator.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        debug_bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "build", "active_build_id": "sample-build", "player_intent": "support_operator"},
        ).json()
        assert client.post("/api/v1/player/support-handoff/artifacts?limit=10", json={"debug_bundle": debug_bundle}).status_code == 200
        assert client.post(
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit",
            json={"reviewer": "operator", "notes": ["Operator packet test recorded verification."]},
        ).status_code == 200

        response = client.get("/api/v1/player/support-handoff/operator-packet")
        markdown = client.get("/api/v1/player/support-handoff/operator-packet?format=markdown")
        csv = client.get("/api/v1/player/support-handoff/operator-packet?format=csv")
        packet = response.json()["data"]["support_handoff_operator_packet"]

        assert response.status_code == 200
        assert packet["schema_version"] == "gw2radar.player_support_handoff_operator_packet.v1"
        assert packet["ready"] is True
        assert packet["maturity_label"] == "ready"
        assert packet["checklist"]["schema_version"] == "gw2radar.player_support_handoff_readiness_checklist.v1"
        assert packet["audit_summary"]["record_count"] >= 1
        assert packet["zip_manifest"]["schema_version"] == "gw2radar.player_support_handoff_zip_manifest.v1"
        assert "player_support_handoff.zip" in packet["transfer_files"]
        assert packet["runbook_steps"]
        assert packet["support_next_actions"]
        assert packet["safety_boundaries"]
        assert markdown.status_code == 200
        assert "# Player Support Handoff Operator Packet" in markdown.text
        assert "## Runbook Steps" in markdown.text
        assert csv.status_code == 200
        assert "packet_id,ready,maturity_label,zip_checksum_sha256" in csv.text
        assert "secret-key" not in (str(packet) + markdown.text + csv.text).lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(packet_artifact_root, ignore_errors=True)
        shutil.rmtree(handoff_artifact_root, ignore_errors=True)


def test_legendary_catalog_and_actions_cover_player_guide_goal_choices() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-catalog-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        catalog = client.get("/api/v1/legendary/goals/catalog")
        goals = catalog.json()["data"]["goals"]
        goal_names = {goal["display_name"] for goal in goals}
        assert {"Aurora", "Vision", "Conflux", "Ad Infinitum", "Legendary Weapon", "Legendary Armor", "Custom Goal"}.issubset(goal_names)

        created = client.post("/api/v1/legendary/goals", json={"graph_goal_id": "gw2:goal:vision", "priority": 2})
        planner = client.post("/api/v1/legendary/recompute")
        actions = client.get("/api/v1/legendary/actions")
        planner_payload = planner.json()["data"]["planner"]
        plan = actions.json()["data"]["action_plan"]

        assert created.status_code == 200
        assert planner.status_code == 200
        assert planner_payload["account_value_evidence"]["schema_version"] == "gw2radar.account_value_evidence_bridge.v1"
        assert planner_payload["account_value_evidence"]["remediation_summary"]
        assert actions.status_code == 200
        assert plan["today_actions"]
        assert plan["this_week_actions"]
        assert "balanced_path" in plan["route_comparison"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_returner_full_report_requires_entitlement_and_exports_artifact() -> None:
    temp_dir = Path(".test_tmp") / f"returner-full-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        locked = client.post("/api/v1/returner/report", json={"goal_id": "gw2:goal:aurora"})
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "returner_full_report")

        report = client.post("/api/v1/returner/report", json={"goal_id": "gw2:goal:aurora"})
        job = report.json()["data"]["job"]
        artifact = Path(job["artifact_path"])

        assert report.status_code == 200
        assert job["status"] == "succeeded"
        assert artifact.exists()
        text = artifact.read_text(encoding="utf-8")
        assert "Returner Full Recovery Report" in text
        assert "Evidence & Data Freshness" in text
        assert "No gameplay automation" in text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
