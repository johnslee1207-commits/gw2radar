"""Player use-path completeness audit harness.

The harness verifies the player-facing path from UI shell to account value
evidence bridge, three commercial opportunities, and report export metadata.
It writes a deterministic Markdown audit for operator review.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api import state  # noqa: E402
from gw2radar.api.main import app  # noqa: E402
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products  # noqa: E402
from gw2radar.db import session as db_session  # noqa: E402
from gw2radar.db.init_db import init_db  # noqa: E402
from gw2radar.db.session import close_database, configure_database  # noqa: E402


AUDIT_PATH = ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md"
SESSION_PACKET_ARTIFACT_ROOT = ROOT / "src" / "gw2radar" / "reports" / "artifacts" / "player_session_packets"


@dataclass
class AuditCheck:
    check_id: str
    label: str
    passed: bool
    maturity: str
    evidence: str
    limitation: str = "None for MVP depth."


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"player-use-path-audit-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    checks: list[AuditCheck] = []

    try:
        configure_database(f"sqlite:///{temp_dir / 'player-use-path.db'}")
        init_db()
        state.reset_cached_graph()
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

        _json(client.post("/mock/load"), "load demo graph", checks)
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
            and _get(session_packet, "export_manifest", "contains_raw_key") is False
            and _get(session_packet, "export_manifest", "contains_private_source_payload") is False
            and isinstance(session_packet.get("debug_safe_evidence"), list)
            and isinstance(session_packet.get("support_review_prompts"), list)
            and session_packet_md.status_code == 200
            and "# Player Session Packet" in session_packet_md.text
            and session_packet_csv.status_code == 200
            and "contains_raw_key" in session_packet_csv.text
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
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "outputs", ignore_errors=True)
        shutil.rmtree(SESSION_PACKET_ARTIFACT_ROOT, ignore_errors=True)

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
            "- `PrivatePlayerState` stores private account summaries separately from public game and KB layers.",
            "- `AccountValueSnapshot` normalizes holdings, price coverage, source diagnostics, and remediation actions.",
            "- `AccountValueHistory` stores privacy-safe value coverage snapshots and compares value/coverage/freshness deltas.",
            "- `AccountValueEvidenceBridge` carries the same summary-only evidence into Build Fit, Legendary Planner, Market Radar, and report artifacts.",
            "- `PlayerReadinessSummary` aggregates sync, account value, Legendary, Market, and Build Fit bridge checks into one dashboard action.",
            "- `PlayerReadinessExport` renders the readiness summary as Markdown and CSV for player/support comparison across sessions.",
            "- `PlayerReadinessHistory` stores privacy-safe readiness snapshots and compares the latest two score/check states.",
            "- `PlayerHistoryCorrelation` explains readiness deltas alongside account value, price coverage, and warning deltas.",
            "- `PlayerSessionPacket` packages readiness, value, correlation, and debug-safe support prompts without raw private payloads.",
            "- `PlayerSessionPacketArtifacts` writes local JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.",
            "- `PlayerSupportHandoffBundle` combines packet artifact metadata with account debug review status for privacy-safe support triage.",
            "- `ReportArtifactManifest` records bridge metadata without storing raw API keys or unredacted private payloads.",
            "",
            "## Known Limits",
            "",
            "- Official price refresh depends on the external GW2 API gateway; this audit verifies the UI/API contract and existing dedicated refresh tests cover gateway behavior.",
            "- The audit uses demo graph and deterministic local database data; real player accounts can still encounter GW2 API rate limits or missing optional permissions.",
            "- UI validation here is static plus API-level; full browser visual polish should remain covered by browser screenshot checks when layout changes are substantial.",
            "",
            "## Next Priority",
            "",
            "Add local support handoff artifact files and path-safe retrieval so handoff bundles can be archived with checksums.",
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
