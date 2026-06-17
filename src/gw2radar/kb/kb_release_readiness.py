import csv
from enum import StrEnum
from io import StringIO

from pydantic import BaseModel, Field

from gw2radar.acquisition.readiness import AcquisitionReadinessReport
from gw2radar.kb.kb_domain_rule_packs import DomainRulePack
from gw2radar.kb.kb_promotion_planner import KbPromotionPlan
from gw2radar.kb.kb_semantic_maturity import KbSemanticMaturityReport
from gw2radar.kb.kb_source_semantics import SourceSemanticExtractionReport
from gw2radar.kb.patch_impact_review import PatchReviewDashboardItem
from gw2radar.kb.patch_rule_audit import PatchRuleAuditEvent


class ReadinessStatus(StrEnum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


class ReleaseReadinessChecklistItem(BaseModel):
    check_id: str
    title: str
    status: ReadinessStatus
    summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    operator_steps: list[str] = Field(default_factory=list)


class KbReleaseReadinessReport(BaseModel):
    schema_version: str
    ready_for_release: bool
    status_counts: dict[ReadinessStatus, int]
    checklist: list[ReleaseReadinessChecklistItem]
    next_operator_steps: list[str]


def build_kb_release_readiness_report(
    semantic_report: KbSemanticMaturityReport,
    promotion_plan: KbPromotionPlan,
    source_semantics: SourceSemanticExtractionReport,
    patch_dashboard_items: list[PatchReviewDashboardItem],
    audit_events: list[PatchRuleAuditEvent],
    rule_packs: list[DomainRulePack],
    acquisition_readiness: AcquisitionReadinessReport | None = None,
) -> KbReleaseReadinessReport:
    checklist = [
        _semantic_check(semantic_report),
        _rule_pack_check(rule_packs),
        _promotion_check(promotion_plan),
        _source_semantics_check(source_semantics),
        _patch_workflow_check(patch_dashboard_items, audit_events),
        _operating_boundary_check(),
    ]
    if acquisition_readiness is not None:
        checklist.insert(4, _acquisition_readiness_check(acquisition_readiness))
    status_counts: dict[ReadinessStatus, int] = {status: 0 for status in ReadinessStatus}
    for item in checklist:
        status_counts[item.status] += 1
    next_steps = [
        step
        for item in checklist
        if item.status != ReadinessStatus.PASS
        for step in item.operator_steps
    ]
    if not next_steps:
        next_steps = [
            "Review import previews, then import selected reviewed rule packs with explicit confirmation.",
            "Enable only reviewed KnowledgeRule records that have current evidence and an operator-approved purpose.",
            "Export source semantics, promotion plan, patch dashboard, and audit logs for the release record.",
        ]
    return KbReleaseReadinessReport(
        schema_version="gw2radar.kb_release_readiness.v1",
        ready_for_release=status_counts[ReadinessStatus.FAIL] == 0,
        status_counts=status_counts,
        checklist=checklist,
        next_operator_steps=next_steps,
    )


def render_kb_release_readiness_markdown(report: KbReleaseReadinessReport) -> str:
    lines = [
        "# KB Release Readiness And Operating Playbook",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- ready_for_release: `{str(report.ready_for_release).lower()}`",
        f"- pass: `{report.status_counts[ReadinessStatus.PASS]}`",
        f"- warn: `{report.status_counts[ReadinessStatus.WARN]}`",
        f"- fail: `{report.status_counts[ReadinessStatus.FAIL]}`",
        "",
        "## Checklist",
        "",
        "| Check | Status | Summary | Evidence |",
        "|---|---|---|---|",
    ]
    for item in report.checklist:
        lines.append(f"| {item.title} | {item.status.value} | {item.summary} | {_join(item.evidence_refs)} |")
    lines.extend(["", "## Operator Steps", ""])
    for step in report.next_operator_steps:
        lines.append(f"- {step}")
    lines.extend(
        [
            "",
            "## Safety Boundary",
            "",
            "- This playbook is read-only.",
            "- It does not import, persist, enable, or disable rules.",
            "- It does not alter private player state, team data, builds, market watchlists, or reports.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def render_kb_release_readiness_csv(report: KbReleaseReadinessReport) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["check_id", "title", "status", "summary", "evidence_refs", "operator_steps"])
    for item in report.checklist:
        writer.writerow(
            [
                item.check_id,
                item.title,
                item.status.value,
                item.summary,
                "; ".join(item.evidence_refs),
                "; ".join(item.operator_steps),
            ]
        )
    return output.getvalue()


def _semantic_check(report: KbSemanticMaturityReport) -> ReleaseReadinessChecklistItem:
    status = ReadinessStatus.PASS if report.overall_score >= 0.85 else ReadinessStatus.WARN
    return ReleaseReadinessChecklistItem(
        check_id="semantic_maturity",
        title="Semantic maturity baseline",
        status=status,
        summary=f"Overall KB semantic maturity is {report.overall_score:.3f} ({report.maturity_label}).",
        evidence_refs=["/api/v1/kb/semantic-maturity"],
        operator_steps=["Review remaining semantic maturity gaps before release."] if status != ReadinessStatus.PASS else [],
    )


def _rule_pack_check(rule_packs: list[DomainRulePack]) -> ReleaseReadinessChecklistItem:
    disabled_rules = [rule for pack in rule_packs for rule in pack.rules if not rule.enabled]
    reviewed_rules = [rule for pack in rule_packs for rule in pack.rules if rule.review_status.value == "reviewed"]
    all_rules = [rule for pack in rule_packs for rule in pack.rules]
    ok = len(rule_packs) >= 5 and len(disabled_rules) == len(all_rules) and len(reviewed_rules) == len(all_rules)
    return ReleaseReadinessChecklistItem(
        check_id="reviewed_rule_packs",
        title="Reviewed disabled rule packs",
        status=ReadinessStatus.PASS if ok else ReadinessStatus.FAIL,
        summary=f"{len(rule_packs)} rule packs expose {len(all_rules)} rules; {len(disabled_rules)} are disabled by default.",
        evidence_refs=["/api/v1/kb/rule-packs"],
        operator_steps=[
            "Ensure all release rule packs are reviewed and disabled before import.",
            "Import selected packs only through the confirmation-gated API.",
        ]
        if not ok
        else ["Import selected packs with confirmation, then enable only approved reviewed rules."],
    )


def _promotion_check(plan: KbPromotionPlan) -> ReleaseReadinessChecklistItem:
    status = ReadinessStatus.PASS if plan.blocker_count == 0 else ReadinessStatus.WARN
    return ReleaseReadinessChecklistItem(
        check_id="promotion_plan",
        title="Promotion plan blockers",
        status=status,
        summary=f"Promotion plan found {plan.blocker_count} blockers and {plan.distillable_article_count} distillable articles.",
        evidence_refs=["/api/v1/kb/promotion-plan", "/api/v1/kb/promotion-plan/export"],
        operator_steps=["Resolve or explicitly defer promotion blockers before enabling affected rules."]
        if status != ReadinessStatus.PASS
        else ["Export the promotion plan for the release record."],
    )


def _source_semantics_check(report: SourceSemanticExtractionReport) -> ReleaseReadinessChecklistItem:
    if report.hint_count == 0:
        status = ReadinessStatus.FAIL
    elif report.blocker_count:
        status = ReadinessStatus.WARN
    else:
        status = ReadinessStatus.PASS
    return ReleaseReadinessChecklistItem(
        check_id="source_semantics",
        title="Source semantics and evidence",
        status=status,
        summary=f"{report.hint_count} source semantic hints, {report.ontology_link_count} ontology links, {report.blocker_count} blockers.",
        evidence_refs=["/api/v1/kb/source-semantics", "/api/v1/kb/source-semantics/export"],
        operator_steps=["Export source semantics and review missing evidence or ontology blockers."]
        if status != ReadinessStatus.PASS
        else ["Export source semantics as evidence for the release record."],
    )


def _patch_workflow_check(
    items: list[PatchReviewDashboardItem],
    events: list[PatchRuleAuditEvent],
) -> ReleaseReadinessChecklistItem:
    reviewed_count = sum(1 for item in items if item.review_status.value == "reviewed")
    enabled_count = sum(item.enabled_rule_count for item in items)
    status = ReadinessStatus.PASS if reviewed_count or not items else ReadinessStatus.WARN
    return ReleaseReadinessChecklistItem(
        check_id="patch_review_audit",
        title="Patch review dashboard and audit trail",
        status=status,
        summary=f"{len(items)} patch dashboard items, {reviewed_count} reviewed, {enabled_count} enabled rules, {len(events)} audit events.",
        evidence_refs=[
            "/api/v1/kb/patch-impact/dashboard",
            "/api/v1/kb/patch-impact/dashboard/export",
            "/api/v1/kb/patch-impact/audit",
        ],
        operator_steps=["Review pending patch items and export dashboard/audit before release."]
        if status != ReadinessStatus.PASS
        else ["Export patch dashboard and audit trail for the release record."],
    )


def _acquisition_readiness_check(report: AcquisitionReadinessReport) -> ReleaseReadinessChecklistItem:
    if not report.ready:
        status = ReadinessStatus.FAIL
    elif report.source_count == 0 or report.paid_report_source_count == 0:
        status = ReadinessStatus.WARN
    else:
        status = ReadinessStatus.PASS
    blocker_summary = f"{len(report.blockers)} blockers" if report.blockers else "no blockers"
    return ReleaseReadinessChecklistItem(
        check_id="acquisition_readiness",
        title="Acquisition source and job readiness",
        status=status,
        summary=(
            f"{report.source_count} acquisition sources, {report.enabled_source_count} enabled, "
            f"{report.paid_report_source_count} paid-report eligible, {blocker_summary}."
        ),
        evidence_refs=[
            "/api/v1/acquisition/readiness",
            "/api/v1/acquisition/readiness/export",
        ],
        operator_steps=report.recommendations
        if status != ReadinessStatus.PASS
        else ["Export acquisition readiness and include it in the release record."],
    )


def _operating_boundary_check() -> ReleaseReadinessChecklistItem:
    return ReleaseReadinessChecklistItem(
        check_id="operating_boundaries",
        title="Safety and operating boundaries",
        status=ReadinessStatus.PASS,
        summary="Release flow remains read-only until explicit rule import and enable confirmations are used.",
        evidence_refs=[
            "KnowledgeRuleInput.validate_rule_contract",
            "import_domain_rule_pack",
            "enable_rule",
        ],
        operator_steps=[
            "Never enable unreviewed rules.",
            "Never use KB release tooling to copy full source text or expose private player data.",
        ],
    )


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else "none"
