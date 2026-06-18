"""Privacy-safe account debug bundle review harness.

With a file path argument, this script reviews a player-exported debug bundle.
Without arguments, it runs a deterministic smoke check against sample bundles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.support.account_debug_bundle_review import (  # noqa: E402
    render_account_debug_bundle_review_markdown,
    review_account_debug_bundle,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        bundle_path = Path(args[0])
        try:
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - operator-facing error path
            print(f"FAIL: could not read debug bundle: {exc}")
            return 1
        print(render_account_debug_bundle_review_markdown(review_account_debug_bundle(bundle)))
        return 0

    checks = [
        ("missing permissions are detected", _review_status(_sample_bundle(missing_required=["characters"])) == "needs_permissions"),
        ("delayed sync is detected", _review_status(_sample_bundle(retry_scheduled=1)) == "sync_delayed"),
        ("ready backend with incomplete UI is detected", _review_status(_sample_bundle(active_view="connect")) == "frontend_flow_incomplete"),
        ("privacy boundary violations are detected", _review_status(_sample_bundle(extra={"api_key": "redacted-example"})) == "privacy_boundary_violation"),
        ("complete player flow is ready", _review_status(_sample_bundle(active_view="build", active_build_id_present=True)) == "ready"),
    ]
    failed = [name for name, passed in checks if not passed]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
    if failed:
        print("FAIL: GW2Radar account debug bundle review harness failed")
        return 1
    print("PASS: GW2Radar account debug bundle review harness succeeded")
    return 0


def _review_status(bundle: dict) -> str:
    return review_account_debug_bundle(bundle).overall_status


def _sample_bundle(
    *,
    missing_required: list[str] | None = None,
    retry_scheduled: int = 0,
    active_view: str = "build",
    active_build_id_present: bool = True,
    extra: dict | None = None,
) -> dict:
    checks = [
        {"check_id": "api_key_stored", "status": "pass"},
        {"check_id": "permissions_ready", "status": "fail" if missing_required else "pass"},
        {"check_id": "sync_job_visible", "status": "pass"},
        {"check_id": "private_snapshot_written", "status": "pass"},
        {"check_id": "synced_character_snapshot", "status": "pass"},
        {"check_id": "build_fit_bridge_ready", "status": "pass"},
    ]
    bundle = {
        "schema_version": "gw2radar.account_debug_bundle.v1",
        "client_state": {
            "active_view": active_view,
            "active_build_id_present": active_build_id_present,
            "player_intent": "build_fit",
            "report_history_count": 0,
        },
        "key_status": {"is_configured": True, "masked_key": "1234...9abc"},
        "permission_summary": {
            "key_configured": True,
            "limited_mode": bool(missing_required),
            "missing_required_permissions": missing_required or [],
            "missing_optional_permissions": [],
        },
        "sync_summary": {
            "status": "succeeded",
            "counts": {"succeeded": 1, "retry_scheduled": retry_scheduled},
            "endpoint_progress": [],
        },
        "diagnostic_summary": {
            "summary_status": "ready" if not missing_required else "blocked",
            "checks": checks,
            "next_actions": [],
        },
        "snapshot_summary": {
            "private_player_state_count": 5,
            "synced_character_snapshot_count": 1,
            "manual_snapshot_count": 0,
            "synced_gear_count": 4,
        },
        "redaction_policy": ["Raw API keys are excluded."],
    }
    if extra:
        bundle.update(extra)
    return bundle


if __name__ == "__main__":
    raise SystemExit(main())
