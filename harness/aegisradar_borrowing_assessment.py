from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw2radar.ops.aegisradar_borrowing import (
    build_aegisradar_borrowing_assessment,
    render_aegisradar_borrowing_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "AEGISRADAR_BORROWING_ASSESSMENT.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "AEGISRADAR_BORROWING_ASSESSMENT.md"


def build_payload() -> dict[str, object]:
    return build_aegisradar_borrowing_assessment().model_dump(mode="json")


def render_markdown() -> str:
    return render_aegisradar_borrowing_markdown(build_aegisradar_borrowing_assessment())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build AegisRadar borrowing assessment artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    payload = build_payload()
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown()

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: AegisRadar borrowing assessment is out of date")
            return 1
        if payload["status"] != "ready_for_targeted_adaptation":
            print("FAIL: AegisRadar borrowing assessment is blocked")
            return 1
        print("PASS: AegisRadar borrowing assessment is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: AegisRadar borrowing assessment written to {OUTPUT_MD}")
    return 0
