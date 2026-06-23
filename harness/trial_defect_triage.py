from __future__ import annotations

import argparse
import json
from pathlib import Path

from gw2radar.ops.trial_defect_triage import (
    build_trial_defect_dashboard,
    build_trial_readiness_checklist,
    render_trial_defect_dashboard_markdown,
    render_trial_readiness_checklist_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "TRIAL_DEFECT_TRIAGE_READINESS.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "TRIAL_DEFECT_TRIAGE_READINESS.md"


def build_trial_defect_triage_readiness() -> dict[str, object]:
    checklist = build_trial_readiness_checklist()
    dashboard = build_trial_defect_dashboard()
    return {
        "schema_version": "gw2radar.trial_defect_triage_readiness.v1",
        "status": dashboard.status,
        "checklist": checklist.model_dump(mode="json"),
        "dashboard": dashboard.model_dump(mode="json"),
        "next_priority": dashboard.next_priority,
    }


def render_markdown(payload: dict[str, object]) -> str:
    checklist = build_trial_readiness_checklist()
    dashboard = build_trial_defect_dashboard()
    return "\n".join(
        [
            render_trial_readiness_checklist_markdown(checklist),
            "",
            "---",
            "",
            render_trial_defect_dashboard_markdown(dashboard),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build trial defect triage readiness artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    payload = build_trial_defect_triage_readiness()
    expected_json = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(payload)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: trial defect triage readiness is out of date")
            return 1
        if payload["status"] != "ready_for_user_trial":
            print("FAIL: trial defect triage readiness is blocked")
            return 1
        print("PASS: trial defect triage readiness is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: trial defect triage readiness written to {OUTPUT_MD}")
    return 0 if payload["status"] == "ready_for_user_trial" else 1
