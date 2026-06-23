from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw2radar.ops.final_closeout import (
    build_final_closeout_dashboard,
    render_final_closeout_dashboard_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "FINAL_CLOSEOUT_DASHBOARD.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "FINAL_CLOSEOUT_DASHBOARD.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build final closeout dashboard artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    dashboard = build_final_closeout_dashboard()
    expected_json = json.dumps(dashboard.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    expected_md = render_final_closeout_dashboard_markdown(dashboard)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: final closeout dashboard is out of date")
            return 1
        if dashboard.status != "ready_for_user_trial" or dashboard.stop_line_count != 0:
            print("FAIL: final closeout dashboard is blocked")
            return 1
        print("PASS: final closeout dashboard is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: final closeout dashboard written to {OUTPUT_MD}")
    return 0 if dashboard.status == "ready_for_user_trial" and dashboard.stop_line_count == 0 else 1
