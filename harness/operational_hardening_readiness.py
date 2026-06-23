from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw2radar.ops.release_readiness import (
    build_operational_hardening_readiness,
    render_operational_hardening_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "OPERATIONAL_HARDENING_READINESS.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "OPERATIONAL_HARDENING_READINESS.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build operational hardening readiness artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    readiness = build_operational_hardening_readiness()
    expected_json = json.dumps(readiness.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    expected_md = render_operational_hardening_markdown(readiness)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: operational hardening readiness is out of date")
            return 1
        if readiness.status != "ready":
            print("FAIL: operational hardening readiness is blocked")
            return 1
        print("PASS: operational hardening readiness is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: operational hardening readiness written to {OUTPUT_MD}")
    return 0 if readiness.status == "ready" else 1
