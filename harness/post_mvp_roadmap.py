from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "docs" / "analysis"
TRUST_DOC = ANALYSIS_DIR / "GW2Radar_Trust_Credential_Architecture.md"
SAAS_DOC = ANALYSIS_DIR / "GW2Radar_Production_SaaS_Architecture.md"
MASTER_DOC = ANALYSIS_DIR / "GW2Radar_Master_Planning_Summary.md"
CLOSURE_JSON = ANALYSIS_DIR / "MVP_CLOSURE_READINESS.json"
OUTPUT_JSON = ANALYSIS_DIR / "POST_MVP_PRODUCTION_ROADMAP.json"
OUTPUT_MD = ANALYSIS_DIR / "POST_MVP_PRODUCTION_ROADMAP.md"


PHASES = [
    {
        "phase_id": "phase_a_trust_credential_mvp",
        "title": "Phase A Trust & Credential MVP",
        "priority": 1,
        "status": "next_recommended",
        "scope": [
            "session-only BYOK mode",
            "credential mode model",
            "permission explanation UI/API",
            "credential usage audit summary",
            "revoke/delete/rotate UX",
        ],
        "defer": ["team workspace credential sharing", "KMS production vault"],
        "acceptance": [
            "raw keys never appear in logs, URLs, reports, or front-end storage",
            "session-only mode requires no persisted secret",
            "encrypted persistent mode remains local-first unless production mode is explicit",
        ],
    },
    {
        "phase_id": "phase_b_report_product_close_loop",
        "title": "Phase B Report Product Close Loop",
        "priority": 2,
        "status": "recommended_after_phase_a",
        "scope": [
            "clear report product contracts",
            "preview vs full report boundary",
            "mock license and entitlement lifecycle",
            "delivery artifacts through shared lifecycle",
        ],
        "defer": ["real payment provider", "email delivery provider"],
        "acceptance": [
            "mock payment only",
            "deterministic report artifacts",
            "no unsupported claims or guaranteed outcomes",
        ],
    },
    {
        "phase_id": "phase_c_progression_decision_engine_v1",
        "title": "Phase C Progression Decision Engine v1",
        "priority": 3,
        "status": "recommended_after_phase_b",
        "scope": [
            "manual action model",
            "scoring model",
            "Top-K recommendation API",
            "KB-backed recommendation explanation",
        ],
        "defer": ["automatic trading", "automatic gameplay execution", "profit guarantees"],
        "acceptance": [
            "all sell/buy actions are review candidates only",
            "every action includes evidence, risk, and assumptions",
            "manual review boundary is visible in outputs",
        ],
    },
    {
        "phase_id": "phase_d_7_day_planning_dag",
        "title": "Phase D 7-Day Planning / DAG",
        "priority": 4,
        "status": "post_phase_c",
        "scope": [
            "goal interpreter",
            "action dependency graph",
            "7-day plan generator",
            "plan export Markdown/CSV/JSON",
        ],
        "defer": ["real-time autonomous replanning"],
        "acceptance": [
            "plan is explainable and deterministic for fixture inputs",
            "missing facts become assumptions",
            "no guaranteed completion claim",
        ],
    },
    {
        "phase_id": "phase_e_production_saas_foundation",
        "title": "Phase E Production SaaS Foundation",
        "priority": 5,
        "status": "large_separate_stage",
        "scope": [
            "auth/session model",
            "workspace model",
            "PostgreSQL migration plan",
            "Redis/cache/queue plan",
            "object storage abstraction",
            "billing guard abstraction",
        ],
        "defer": ["full multi-tenant SaaS launch", "real payment integration"],
        "acceptance": [
            "local-first mode still works",
            "SaaS behavior is behind deployment mode",
            "private data isolation is tested",
        ],
    },
    {
        "phase_id": "phase_f_growth_retention",
        "title": "Phase F Growth / Retention",
        "priority": 6,
        "status": "after_saas_foundation",
        "scope": [
            "weekly report job",
            "report history",
            "safe share preview",
            "mock email delivery abstraction",
            "subscription retention UX",
        ],
        "defer": ["public sharing of private account payloads", "real email provider lock-in"],
        "acceptance": [
            "share previews contain no private payloads",
            "delete/unsubscribe path is documented",
            "weekly outputs preserve no-guarantee language",
        ],
    },
]


def _read(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing roadmap input: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def _load_closure() -> dict[str, object]:
    if not CLOSURE_JSON.exists():
        raise FileNotFoundError(f"Missing closure readiness: {CLOSURE_JSON}")
    return json.loads(CLOSURE_JSON.read_text(encoding="utf-8"))


def build_roadmap() -> dict[str, object]:
    trust = _read(TRUST_DOC)
    saas = _read(SAAS_DOC)
    master = _read(MASTER_DOC)
    closure = _load_closure()
    required_terms = {
        "trust": ["Session-only", "Encrypted Persistent", "Team Workspace", "Permission Explain"],
        "saas": ["Production SaaS", "Credential Center", "Subscription", "PostgreSQL"],
        "master": ["Progression Engine", "Decision System", "7-Day Plan", "SaaS"],
    }
    source_coverage = {
        "trust": {term: term in trust for term in required_terms["trust"]},
        "saas": {term: term in saas for term in required_terms["saas"]},
        "master": {term: term in master for term in required_terms["master"]},
    }
    blocking_current_mvp = closure.get("blocking_task_count", 999) != 0
    return {
        "schema_version": "gw2radar.post_mvp_production_roadmap.v1",
        "current_mvp_status": closure.get("status"),
        "blocking_current_mvp": blocking_current_mvp,
        "source_docs": [
            "docs/analysis/GW2Radar_Trust_Credential_Architecture.md",
            "docs/analysis/GW2Radar_Production_SaaS_Architecture.md",
            "docs/analysis/GW2Radar_Master_Planning_Summary.md",
        ],
        "source_coverage": source_coverage,
        "phase_count": len(PHASES),
        "next_phase": PHASES[0]["phase_id"],
        "phases": PHASES,
        "decision": "Start Phase A only; keep production SaaS, real billing, team workspace, and autonomous agents as later explicit stages.",
    }


def render_markdown(roadmap: dict[str, object]) -> str:
    phases = roadmap["phases"]
    assert isinstance(phases, list)
    lines = [
        "# Post-MVP Production Roadmap",
        "",
        f"- Schema: {roadmap['schema_version']}",
        f"- Current MVP status: {roadmap['current_mvp_status']}",
        f"- Blocking current MVP: {str(roadmap['blocking_current_mvp']).lower()}",
        f"- Phase count: {roadmap['phase_count']}",
        f"- Next phase: {roadmap['next_phase']}",
        "",
        "## Decision",
        "",
        str(roadmap["decision"]),
        "",
        "## Source Documents",
        "",
    ]
    for source in roadmap["source_docs"]:
        lines.append(f"- [{source}]({source})")
    lines.extend(["", "## Phases", ""])
    lines.append("| Priority | Phase | Status | Scope | Deferred |")
    lines.append("| --- | --- | --- | --- | --- |")
    for phase in phases:
        lines.append(
            "| {priority} | {title} | {status} | {scope} | {defer} |".format(
                priority=phase["priority"],
                title=phase["title"],
                status=phase["status"],
                scope=", ".join(phase["scope"]).replace("|", "/"),
                defer=", ".join(phase["defer"]).replace("|", "/"),
            )
        )
    lines.extend(["", "## Phase A Acceptance", ""])
    for item in phases[0]["acceptance"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build post-MVP production roadmap artifacts.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    roadmap = build_roadmap()
    expected_json = json.dumps(roadmap, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(roadmap)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: post-MVP production roadmap is out of date")
            return 1
        print("PASS: post-MVP production roadmap is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: post-MVP production roadmap written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
