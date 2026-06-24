from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from gw2radar.ops.delivery_maturity_audit import (
    build_delivery_maturity_audit,
    render_delivery_maturity_audit_markdown,
)


OUTPUT_JSON = ROOT / "docs" / "analysis" / "DELIVERY_MATURITY_AUDIT.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "DELIVERY_MATURITY_AUDIT.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build P2.8 delivery maturity audit artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    audit = build_delivery_maturity_audit()
    expected_json = json.dumps(audit.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    expected_md = render_delivery_maturity_audit_markdown(audit)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: delivery maturity audit is out of date")
            return 1
        if audit.status != "ready" or audit.blocker_count != 0:
            print("FAIL: delivery maturity audit is blocked")
            return 1
        print("PASS: delivery maturity audit is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: delivery maturity audit written to {OUTPUT_MD}")
    return 0 if audit.status == "ready" and audit.blocker_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
