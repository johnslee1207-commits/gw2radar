from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from harness.spec_registry import OUTPUT_JSON as REGISTRY_JSON


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "docs" / "analysis" / "PARTIAL_SPEC_RECONCILIATION.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "PARTIAL_SPEC_RECONCILIATION.md"


RECONCILIATION_NOTES: dict[str, tuple[str, str, str, list[str]]] = {
    "gw2radar_commercial_opportunity_full_implementation_roadmap_codex_spec": (
        "broad_roadmap",
        "The roadmap intentionally spans multiple commercial stages. Core MVP commercial loops are implemented, while full roadmap breadth remains an operating backlog.",
        "Keep implemented commercial slices covered by report, entitlement, guild, creator, market, build, and player UI tests; schedule only explicitly selected roadmap gaps.",
        ["tests/test_report_productization.py", "tests/test_market_api.py", "tests/test_build_fit_api.py"],
    ),
    "gw2radar_kb_graph_commercial_intelligence_implementation_plan": (
        "broad_roadmap",
        "KB, rule, patch, and report infrastructure exists, but the plan is intentionally larger than the current reviewed rule content inventory.",
        "Prioritize reviewed rule pack content and source-evidence quality, not new lifecycle plumbing.",
        ["tests/test_kb_backed_report.py", "tests/test_kb_release_readiness.py", "tests/test_patch_admin_workflow_api.py"],
    ),
    "gw2radar_master_planning_summary": (
        "post_mvp_master_plan",
        "The master plan intentionally describes progression engines, planning agents, SaaS, growth, and subscription evolution beyond the closed local-first MVP.",
        "Use the post-MVP production roadmap gate to schedule Phase A first and keep SaaS, autonomous agents, and real billing as later explicit stages.",
        ["tests/test_post_mvp_roadmap.py", "tests/test_closure_readiness.py", "tests/test_no_auto_trading.py"],
    ),
    "gw2radar_mvp_0_1_codex_development_spec": (
        "legacy_spec_drift",
        "This early planning spec predates later API, UI, commercial, KB, and delivery lifecycle work; partial status mostly reflects historical wording.",
        "Use current PRD/SDD, MVP docs, and stage gate as source of truth; keep this spec as historical input.",
        ["tests/test_goal_gap.py", "tests/test_graph_layers.py", "tests/test_account_connection_diagnostic.py"],
    ),
    "gw2radar_official_gw2_api_compatibility_layer_codex_spec": (
        "implemented_with_live_gateway_limit",
        "Official-compatible client, token safety, permission checks, batching, refresh queues, and diagnostics are covered by tests; live GW2 availability remains an external runtime condition.",
        "Do not expand scope into live certification. Keep fake gateway and contract tests strict, then add optional live smoke only behind explicit operator configuration.",
        ["tests/test_gw2_api_client_official_contract.py", "tests/test_gw2_api_key_safety.py", "tests/test_gw2_api_rate_limit_behavior.py"],
    ),
    "gw2radar_project_constitution_api_governance_codex_spec": (
        "governance_aligned",
        "Current AGENTS/PRD/SDD now express local-first, manual-review, no-secret, no-trading, and source-boundary governance; older spec remains broader than the active MVP.",
        "Keep governance enforced through stage gate, no-secret tests, and workspace hygiene; avoid adding SaaS or automation scope.",
        ["tests/test_constitution_compliance_security.py", "tests/test_no_auto_trading.py", "tests/test_workspace_hygiene.py"],
    ),
    "senior_player_user_guide": (
        "ui_guide_partially_operationalized",
        "Player cockpit, account diagnostics, Build Fit, Legendary, Market, reports, and support handoff are implemented; guide-level polish and browser visual review remain iterative.",
        "Use future UI slices for browser screenshots and senior-player copy refinement when layout changes are made.",
        ["tests/test_player_ui.py", "tests/test_player_ui_e2e_smoke.py", "tests/test_player_dashboard_completion.py"],
    ),
    "mvp_0_1_2_report_export_package": (
        "superseded_by_delivery_lifecycle",
        "Report export is now covered by productized report artifacts and shared delivery lifecycle verification rather than the original narrow MVP package wording.",
        "Treat this as superseded by delivery lifecycle regression unless a legacy export route is explicitly requested.",
        ["tests/test_report_productization.py", "tests/test_delivery_lifecycle.py", "tests/test_export_package.py"],
    ),
    "mvp_0_1_5_evidence_quality_rules": (
        "implemented_with_content_depth_backlog",
        "Evidence quality patterns exist across KB, reports, source attribution, and player diagnostics; remaining maturity is richer reviewed source coverage.",
        "Invest next in reviewed content depth and source freshness, not new evidence framework mechanics.",
        ["tests/test_evidence_quality.py", "tests/test_source_attribution.py", "tests/test_kb_report_quality.py"],
    ),
    "mvp_0_1_codex_development_spec": (
        "legacy_spec_drift",
        "The original MVP 0.1 spec describes an earlier scope; the implemented system has moved through later account, commercial, KB, and UI milestones.",
        "Keep for audit traceability; rely on current registry and maturity audits for execution priority.",
        ["tests/test_markdown_report.py", "tests/test_graph_builder.py", "tests/test_report_no_secret_leakage.py"],
    ),
    "mvp_0_2_0_official_api_compatibility_hardening": (
        "implemented_with_live_gateway_limit",
        "Compatibility hardening is covered through official contract, permission, safety, batching, and queue tests; live network behavior remains intentionally outside default tests.",
        "Add optional live smoke documentation only after local contract stability remains clean.",
        ["tests/test_gw2_api_client_official_contract.py", "tests/test_gw2_api_permissions.py", "tests/test_gw2_api_batching.py"],
    ),
    "mvp_0_3_0_paid_report_engine": (
        "implemented_for_mock_payment",
        "Paid report engine, entitlement, productized artifacts, and mock payment contracts exist; real payment integration remains explicitly out of MVP scope.",
        "Keep mock payment and entitlement integration; defer real provider work until explicitly requested.",
        ["tests/test_report_entitlement.py", "tests/test_payment_provider_mock.py", "tests/test_paid_report_api_routes.py"],
    ),
    "mvp_0_3_5_guild_readiness_console": (
        "implemented_core_team_model",
        "Guild/static readiness includes team, consent, role coverage, privacy-safe member summary, and report coverage; broader SaaS collaboration is out of MVP scope.",
        "Preserve privacy-safe team modeling and avoid expanding into full collaboration or subscription administration.",
        ["tests/test_guild_api.py", "tests/test_team_consent.py", "tests/test_member_privacy_summary.py"],
    ),
    "trial_defect_triage_readiness": (
        "trial_defect_operationalized",
        "Real-user trial readiness is now represented by a deterministic checklist, defect classification API, dashboard exports, and freshness harness.",
        "Use this track for real trial defect triage only; do not reopen broad phase expansion unless a concrete user defect requires it.",
        ["tests/test_trial_defect_triage.py", "tests/test_final_closeout_dashboard.py", "tests/test_account_connection_diagnostic.py"],
    ),
}


@dataclass(frozen=True)
class ReconciliationRecord:
    spec_id: str
    title: str
    source_path: str
    gap_type: str
    status_after_reconciliation: str
    rationale: str
    recommended_action: str
    evidence_tests: list[str]


def _load_registry() -> dict[str, object]:
    if not REGISTRY_JSON.exists():
        raise FileNotFoundError(f"Missing registry: {REGISTRY_JSON}")
    return json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))


def build_reconciliation() -> dict[str, object]:
    registry = _load_registry()
    records = []
    for record in registry["records"]:
        if record["maturity"] != "partial":
            continue
        spec_id = record["spec_id"]
        gap_type, rationale, action, evidence_tests = RECONCILIATION_NOTES.get(
            spec_id,
            (
                "review_needed",
                "This partial spec needs manual review before it can be promoted or scheduled.",
                "Review the source spec and add focused acceptance tests.",
                record.get("related_tests", [])[:3],
            ),
        )
        status = "reconciled" if gap_type != "review_needed" else "needs_review"
        records.append(
            ReconciliationRecord(
                spec_id=spec_id,
                title=record["title"],
                source_path=record["source_path"],
                gap_type=gap_type,
                status_after_reconciliation=status,
                rationale=rationale,
                recommended_action=action,
                evidence_tests=evidence_tests,
            )
        )

    counts: dict[str, int] = {}
    for record in records:
        counts[record.gap_type] = counts.get(record.gap_type, 0) + 1

    return {
        "schema_version": "gw2radar.partial_spec_reconciliation.v1",
        "partial_count": len(records),
        "reconciled_count": sum(1 for record in records if record.status_after_reconciliation == "reconciled"),
        "needs_review_count": sum(1 for record in records if record.status_after_reconciliation == "needs_review"),
        "gap_type_counts": counts,
        "records": [asdict(record) for record in records],
        "next_priority": "Promote reconciled partial specs into a smaller backlog: reviewed content depth, optional live API smoke documentation, and UI visual polish only when explicitly scheduled.",
    }


def render_markdown(reconciliation: dict[str, object]) -> str:
    records = reconciliation["records"]
    assert isinstance(records, list)
    counts = reconciliation["gap_type_counts"]
    assert isinstance(counts, dict)

    lines = [
        "# Partial Spec Reconciliation",
        "",
        f"- Schema: {reconciliation['schema_version']}",
        f"- Partial specs: {reconciliation['partial_count']}",
        f"- Reconciled specs: {reconciliation['reconciled_count']}",
        f"- Needs review: {reconciliation['needs_review_count']}",
        "",
        "## Gap Type Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- {key}: {counts[key]}")

    lines.extend(["", "## Reconciliation Table", ""])
    lines.append("| Spec | Gap Type | Status | Evidence Tests | Recommended Action |")
    lines.append("| --- | --- | --- | --- | --- |")
    for record in records:
        tests = ", ".join(record["evidence_tests"])
        lines.append(
            "| [{title}]({source_path}) | {gap_type} | {status} | {tests} | {action} |".format(
                title=record["title"].replace("|", "/"),
                source_path=record["source_path"],
                gap_type=record["gap_type"],
                status=record["status_after_reconciliation"],
                tests=tests.replace("|", "/"),
                action=record["recommended_action"].replace("|", "/"),
            )
        )

    lines.extend(["", "## Next Priority", "", str(reconciliation["next_priority"]), ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build partial spec reconciliation artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    reconciliation = build_reconciliation()
    expected_json = json.dumps(reconciliation, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(reconciliation)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: partial spec reconciliation is out of date")
            return 1
        print("PASS: partial spec reconciliation is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: partial spec reconciliation written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
