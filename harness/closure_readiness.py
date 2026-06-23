from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECONCILIATION_JSON = ROOT / "docs" / "analysis" / "PARTIAL_SPEC_RECONCILIATION.json"
SPEC_REGISTRY_JSON = ROOT / "docs" / "analysis" / "SPEC_REGISTRY_BACKLOG.json"
PLAYER_AUDIT = ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md"
OUTPUT_JSON = ROOT / "docs" / "analysis" / "MVP_CLOSURE_READINESS.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "MVP_CLOSURE_READINESS.md"


OPTIONAL_BACKLOG = [
    {
        "task_id": "reviewed_content_depth",
        "status": "optional_post_mvp",
        "rationale": "Infrastructure for KB, patch, reports, and evidence is mature; future work should add more reviewed content only when a specific content pack is selected.",
        "blocking_mvp": False,
    },
    {
        "task_id": "optional_live_api_smoke_documentation",
        "status": "operator_opt_in",
        "rationale": "Official API behavior is covered by fake gateway and contract tests; live GW2 smoke checks depend on external credentials, network, and rate limits.",
        "blocking_mvp": False,
    },
    {
        "task_id": "ui_visual_polish",
        "status": "only_when_layout_changes",
        "rationale": "Player UI smoke and completion tests cover workflows; browser screenshot polish should run for future layout changes, not as a blocker for current closeout.",
        "blocking_mvp": False,
    },
]


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required closure input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _player_failed_checks() -> int:
    if not PLAYER_AUDIT.exists():
        return 999
    for line in PLAYER_AUDIT.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Failed checks:"):
            return int(line.split(":", 1)[1].strip())
    return 999


def build_closure_readiness() -> dict[str, object]:
    registry = _load_json(SPEC_REGISTRY_JSON)
    reconciliation = _load_json(RECONCILIATION_JSON)
    failed_checks = _player_failed_checks()
    blocking_backlog = [task for task in OPTIONAL_BACKLOG if task["blocking_mvp"]]
    ready = (
        registry.get("spec_count", 0) >= 50
        and reconciliation.get("needs_review_count") == 0
        and reconciliation.get("partial_count") == reconciliation.get("reconciled_count")
        and failed_checks == 0
        and not blocking_backlog
    )
    return {
        "schema_version": "gw2radar.mvp_closure_readiness.v1",
        "status": "ready_to_close_mvp_stage" if ready else "blocked",
        "blocking_task_count": len(blocking_backlog),
        "optional_task_count": len(OPTIONAL_BACKLOG),
        "remaining_blocking_tasks": blocking_backlog,
        "optional_post_mvp_tasks": OPTIONAL_BACKLOG,
        "evidence": {
            "spec_count": registry.get("spec_count"),
            "registry_maturity_counts": registry.get("maturity_counts"),
            "partial_count": reconciliation.get("partial_count"),
            "reconciled_count": reconciliation.get("reconciled_count"),
            "needs_review_count": reconciliation.get("needs_review_count"),
            "player_use_path_failed_checks": failed_checks,
        },
        "required_closeout_commands": [
            "python harness/run_stage_gate.py stage",
            "python harness/run_stage_gate.py release",
            "npx gitnexus analyze",
        ],
        "next_priority": "Close the current MVP stage; treat the remaining three tracks as optional post-MVP work only when explicitly scheduled.",
    }


def render_markdown(readiness: dict[str, object]) -> str:
    evidence = readiness["evidence"]
    assert isinstance(evidence, dict)
    optional_tasks = readiness["optional_post_mvp_tasks"]
    assert isinstance(optional_tasks, list)
    lines = [
        "# MVP Closure Readiness",
        "",
        f"- Schema: {readiness['schema_version']}",
        f"- Status: {readiness['status']}",
        f"- Blocking task count: {readiness['blocking_task_count']}",
        f"- Optional post-MVP task count: {readiness['optional_task_count']}",
        "",
        "## Evidence",
        "",
        f"- Spec count: {evidence['spec_count']}",
        f"- Registry maturity counts: {evidence['registry_maturity_counts']}",
        f"- Partial specs: {evidence['partial_count']}",
        f"- Reconciled partial specs: {evidence['reconciled_count']}",
        f"- Needs review: {evidence['needs_review_count']}",
        f"- Player use-path failed checks: {evidence['player_use_path_failed_checks']}",
        "",
        "## Optional Post-MVP Tasks",
        "",
        "| Task | Status | Blocking MVP | Rationale |",
        "| --- | --- | --- | --- |",
    ]
    for task in optional_tasks:
        lines.append(
            "| {task_id} | {status} | {blocking} | {rationale} |".format(
                task_id=task["task_id"],
                status=task["status"],
                blocking=str(task["blocking_mvp"]).lower(),
                rationale=task["rationale"].replace("|", "/"),
            )
        )
    lines.extend(["", "## Required Closeout Commands", ""])
    for command in readiness["required_closeout_commands"]:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Next Priority", "", str(readiness["next_priority"]), ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MVP closure readiness artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    readiness = build_closure_readiness()
    expected_json = json.dumps(readiness, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(readiness)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: MVP closure readiness is out of date")
            return 1
        if readiness["status"] != "ready_to_close_mvp_stage":
            print("FAIL: MVP closure readiness is blocked")
            return 1
        print("PASS: MVP closure readiness is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: MVP closure readiness written to {OUTPUT_MD}")
    return 0 if readiness["status"] == "ready_to_close_mvp_stage" else 1


if __name__ == "__main__":
    raise SystemExit(main())
