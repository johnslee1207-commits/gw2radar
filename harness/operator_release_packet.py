from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw2radar.ops.operator_release_packet import (
    build_operator_release_packet_summary,
    render_operator_release_packet_summary_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "OPERATOR_RELEASE_PACKET_READINESS.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "OPERATOR_RELEASE_PACKET_READINESS.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build operator release packet readiness artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    summary = build_operator_release_packet_summary()
    expected_json = json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    expected_md = render_operator_release_packet_summary_markdown(summary)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: operator release packet readiness is out of date")
            return 1
        if summary.status != "ready" or summary.blocker_count != 0:
            print("FAIL: operator release packet readiness is blocked")
            return 1
        print("PASS: operator release packet readiness is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: operator release packet readiness written to {OUTPUT_MD}")
    return 0 if summary.status == "ready" and summary.blocker_count == 0 else 1
