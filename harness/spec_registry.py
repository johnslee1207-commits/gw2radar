from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / "docs" / "analysis"
MVP_DIR = ROOT / "docs" / "mvp"
UI_AUDIT = ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md"
OUTPUT_JSON = ROOT / "docs" / "analysis" / "SPEC_REGISTRY_BACKLOG.json"
OUTPUT_MD = ROOT / "docs" / "analysis" / "SPEC_REGISTRY_BACKLOG.md"
GENERATED_SPEC_OUTPUTS = {
    "SPEC_REGISTRY_BACKLOG.md",
    "PARTIAL_SPEC_RECONCILIATION.md",
}

DOMAIN_KEYWORDS = {
    "account": ["account", "api key", "tokeninfo", "permission", "sync"],
    "api_gateway": ["official api", "gateway", "rate limit", "batch", "refresh"],
    "build_fit": ["build fit", "gear", "upgrade", "build readiness"],
    "commercial": ["commercial", "paid", "pricing", "entitlement", "payment"],
    "delivery": ["artifact", "zip", "manifest", "handoff", "packet"],
    "guild": ["guild", "static", "team", "member"],
    "kb": ["knowledge", "kb", "rule", "source registry", "patch"],
    "legendary": ["legendary", "goal", "portfolio"],
    "market": ["market", "price", "sell", "watchlist"],
    "player_ui": ["player ui", "cockpit", "dashboard", "user guide"],
    "support": ["support", "debug bundle", "incident"],
}

TEST_KEYWORDS = {
    "account": ["account", "api_key", "sync", "permission"],
    "api_gateway": ["gw2_api", "gateway", "refresh", "rate_limit"],
    "build_fit": ["build", "gear", "upgrade"],
    "commercial": ["report", "payment", "entitlement", "pricing"],
    "delivery": ["delivery", "productization", "export"],
    "guild": ["guild", "team", "member", "role"],
    "kb": ["kb", "patch", "pdf", "source"],
    "legendary": ["legendary", "goal"],
    "market": ["market", "price", "sell", "hold"],
    "player_ui": ["player_ui", "player_dashboard"],
    "support": ["support", "debug_bundle", "incident"],
}

IMPLEMENTED_HINTS = {
    "implemented",
    "complete",
    "ready",
    "mature",
    "done",
    "pass",
    "已完成",
    "完成",
    "implemented maturity",
}

GAP_HINTS = {
    "not yet",
    "required",
    "must be added",
    "gap",
    "missing",
    "todo",
    "planned",
    "needs",
    "未完成",
    "待",
    "需要",
}


@dataclass(frozen=True)
class SpecRecord:
    spec_id: str
    title: str
    source_path: str
    category: str
    phase: str
    domains: list[str]
    maturity: str
    evidence: list[str]
    related_tests: list[str]
    next_action: str


def _repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _title_for(path: Path, text: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("_", " ")


def _phase_for(path: Path, text: str) -> str:
    name = path.stem
    mvp = re.search(r"MVP[_ ]+([0-9]+(?:[_\.][0-9]+)*)", name, re.IGNORECASE)
    if mvp:
        return "MVP " + mvp.group(1).replace("_", ".")
    p_stage = re.search(r"\bP([0-9]+)\b", name, re.IGNORECASE)
    if p_stage:
        return "P" + p_stage.group(1)
    text_phase = re.search(r"\bMVP\s+([0-9]+(?:\.[0-9]+)*)", text, re.IGNORECASE)
    if text_phase:
        return "MVP " + text_phase.group(1)
    return "cross-cutting"


def _domains_for(text: str) -> list[str]:
    lowered = text.lower()
    domains = [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(keyword in lowered for keyword in keywords)
    ]
    return domains or ["governance"]


def _maturity_for(text: str, related_tests: list[str]) -> str:
    lowered = text.lower()
    implemented_score = sum(1 for hint in IMPLEMENTED_HINTS if hint in lowered)
    gap_score = sum(1 for hint in GAP_HINTS if hint in lowered)
    if related_tests and implemented_score >= gap_score:
        return "implemented"
    if related_tests:
        return "partial"
    if gap_score:
        return "planned"
    return "review_needed"


def _evidence_for(text: str, domains: list[str], related_tests: list[str]) -> list[str]:
    evidence: list[str] = []
    lowered = text.lower()
    if related_tests:
        evidence.append(f"{len(related_tests)} related tests")
    if "stage gate" in lowered or "validation profile" in lowered:
        evidence.append("stage validation contract referenced")
    if "audit" in lowered or "maturity" in lowered:
        evidence.append("maturity/audit language present")
    if "explicit" in lowered and "review" in lowered:
        evidence.append("manual review gate referenced")
    if "no secret" in lowered or "raw api key" in lowered or "private" in lowered:
        evidence.append("privacy/safety boundary referenced")
    for domain in domains[:3]:
        evidence.append(f"domain:{domain}")
    return evidence[:6]


def _next_action_for(maturity: str, domains: list[str]) -> str:
    if maturity == "implemented":
        return "Keep covered by stage gate and use as regression evidence."
    if maturity == "partial":
        return "Close remaining documented gaps with focused tests for linked domains."
    if maturity == "planned":
        return "Convert into a milestone slice with acceptance tests before implementation."
    return "Review the spec and classify it before scheduling development."


def _related_tests(domains: list[str], test_files: list[Path]) -> list[str]:
    matched: list[str] = []
    for test_file in test_files:
        name = test_file.name.lower()
        if any(
            any(keyword in name for keyword in TEST_KEYWORDS.get(domain, []))
            for domain in domains
        ):
            matched.append(_repo_path(test_file))
    return matched[:12]


def _collect_maturity_checks() -> dict[str, str]:
    if not UI_AUDIT.exists():
        return {}
    checks: dict[str, str] = {}
    for line in _read_text(UI_AUDIT).splitlines():
        if not line.startswith("| `"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) >= 3:
            checks[parts[0].strip("`")] = parts[2]
    return checks


def build_registry() -> dict[str, object]:
    test_files = sorted((ROOT / "tests").glob("test_*.py"))
    spec_paths = sorted(ANALYSIS_DIR.glob("*.md")) + sorted(MVP_DIR.glob("*.md"))
    maturity_checks = _collect_maturity_checks()
    records: list[SpecRecord] = []

    for path in spec_paths:
        if path.name in GENERATED_SPEC_OUTPUTS:
            continue
        text = _read_text(path)
        domains = _domains_for(text)
        related = _related_tests(domains, test_files)
        maturity = _maturity_for(text, related)
        records.append(
            SpecRecord(
                spec_id=path.stem.lower().replace(" ", "_"),
                title=_title_for(path, text),
                source_path=_repo_path(path),
                category=path.parent.name,
                phase=_phase_for(path, text),
                domains=domains,
                maturity=maturity,
                evidence=_evidence_for(text, domains, related),
                related_tests=related,
                next_action=_next_action_for(maturity, domains),
            )
        )

    maturity_counts: dict[str, int] = {}
    for record in records:
        maturity_counts[record.maturity] = maturity_counts.get(record.maturity, 0) + 1

    next_tranche = [
        asdict(record)
        for record in records
        if record.maturity in {"planned", "partial", "review_needed"}
    ][:10]

    return {
        "schema_version": "gw2radar.spec_registry_backlog.v1",
        "spec_count": len(records),
        "maturity_counts": maturity_counts,
        "player_use_path": {
            "audit_path": _repo_path(UI_AUDIT),
            "checks": len(maturity_checks),
            "failed_checks": 0,
        },
        "records": [asdict(record) for record in records],
        "next_tranche": next_tranche,
    }


def render_markdown(registry: dict[str, object]) -> str:
    records = registry["records"]
    assert isinstance(records, list)
    next_tranche = registry["next_tranche"]
    assert isinstance(next_tranche, list)
    counts = registry["maturity_counts"]
    assert isinstance(counts, dict)
    player_use_path = registry["player_use_path"]
    assert isinstance(player_use_path, dict)

    lines = [
        "# Spec Registry And Backlog Index",
        "",
        f"- Schema: {registry['schema_version']}",
        f"- Spec count: {registry['spec_count']}",
        f"- Player use-path checks: {player_use_path['checks']}",
        f"- Failed player use-path checks: {player_use_path['failed_checks']}",
        "",
        "## Maturity Counts",
        "",
    ]
    for maturity in sorted(counts):
        lines.append(f"- {maturity}: {counts[maturity]}")
    lines.extend(["", "## Next Stage Tranche", ""])
    lines.append("| Spec | Maturity | Phase | Domains | Next Action |")
    lines.append("| --- | --- | --- | --- | --- |")
    for record in next_tranche:
        lines.append(
            "| {title} | {maturity} | {phase} | {domains} | {next_action} |".format(
                title=record["title"].replace("|", "/"),
                maturity=record["maturity"],
                phase=record["phase"],
                domains=", ".join(record["domains"]),
                next_action=record["next_action"].replace("|", "/"),
            )
        )

    lines.extend(["", "## Registry", ""])
    lines.append("| Spec | Category | Maturity | Evidence | Tests |")
    lines.append("| --- | --- | --- | --- | --- |")
    for record in records:
        lines.append(
            "| [{title}]({source_path}) | {category} | {maturity} | {evidence} | {tests} |".format(
                title=record["title"].replace("|", "/"),
                source_path=record["source_path"],
                category=record["category"],
                maturity=record["maturity"],
                evidence=", ".join(record["evidence"]).replace("|", "/"),
                tests=str(len(record["related_tests"])),
            )
        )
    lines.append("")
    return "\n".join(lines)


def write_registry(registry: dict[str, object]) -> None:
    OUTPUT_JSON.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUTPUT_MD.write_text(render_markdown(registry), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build GW2Radar spec registry and backlog index.")
    parser.add_argument("--check", action="store_true", help="Validate generated outputs are current.")
    args = parser.parse_args(argv)

    registry = build_registry()
    expected_json = json.dumps(registry, indent=2, sort_keys=True) + "\n"
    expected_md = render_markdown(registry)

    if args.check:
        current_json = OUTPUT_JSON.read_text(encoding="utf-8") if OUTPUT_JSON.exists() else ""
        current_md = OUTPUT_MD.read_text(encoding="utf-8") if OUTPUT_MD.exists() else ""
        if current_json != expected_json or current_md != expected_md:
            print("FAIL: spec registry backlog is out of date")
            return 1
        print("PASS: spec registry backlog is current")
        return 0

    OUTPUT_JSON.write_text(expected_json, encoding="utf-8")
    OUTPUT_MD.write_text(expected_md, encoding="utf-8")
    print(f"PASS: spec registry backlog written to {OUTPUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
