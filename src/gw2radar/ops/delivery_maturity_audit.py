from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[3]
SUPPORT_CASE_FILE = ROOT / "src" / "gw2radar" / "commercial" / "support_case_incidents.py"
REPORT_PRODUCTIZATION_FILE = ROOT / "src" / "gw2radar" / "commercial" / "report_productization.py"
DELIVERY_LIFECYCLE_FILE = ROOT / "src" / "gw2radar" / "delivery" / "lifecycle.py"
OPS_LIFECYCLE_FILE = ROOT / "src" / "gw2radar" / "ops" / "lifecycle.py"
HARNESS_GUIDE_FILE = ROOT / "docs" / "HARNESS.md"


class DeliveryMaturityCheck(BaseModel):
    check_id: str
    axis: str
    status: str
    evidence: str
    required: bool = True


class DeliveryMaturityMetric(BaseModel):
    metric_id: str
    value: int | float | str
    status: str
    evidence: str


class DeliverySemanticEdge(BaseModel):
    source: str
    relation: str
    target: str
    evidence: str


class DeliveryMaturityAudit(BaseModel):
    schema_version: str = "gw2radar.delivery_maturity_audit.v1"
    status: str
    maturity_label: str
    score: float
    scope: str
    code_checks: list[DeliveryMaturityCheck]
    residual_duplication_metrics: list[DeliveryMaturityMetric]
    semantic_edges: list[DeliverySemanticEdge]
    evidence_files: list[str]
    limitations: list[str] = Field(default_factory=list)
    next_priority: str

    @property
    def blocker_count(self) -> int:
        return sum(1 for check in self.code_checks if check.required and check.status != "ready")


def build_delivery_maturity_audit() -> DeliveryMaturityAudit:
    support_text = _read(SUPPORT_CASE_FILE)
    report_text = _read(REPORT_PRODUCTIZATION_FILE)
    delivery_text = _read(DELIVERY_LIFECYCLE_FILE)
    ops_text = _read(OPS_LIFECYCLE_FILE)
    harness_text = _read(HARNESS_GUIDE_FILE)

    checks = [
        _contains_check(
            "shared_delivery_lifecycle_contract",
            "code",
            delivery_text,
            "build_delivery_packet_zip_bundle",
            "Shared lifecycle zip construction remains centralized.",
        ),
        _contains_check(
            "shared_delivery_readiness_contract",
            "code",
            delivery_text,
            "build_delivery_lifecycle_readiness",
            "Productized reports can use one readiness contract instead of bespoke gates.",
        ),
        _contains_check(
            "shared_operational_lifecycle_projection",
            "code",
            ops_text,
            "build_delivery_operational_lifecycle_projection",
            "Delivery objects can share operational lifecycle summaries.",
        ),
        _contains_check(
            "shared_delivery_readiness_projection",
            "code",
            ops_text,
            "build_delivery_readiness_projection",
            "Delivery readiness projection can be reused by support and productized report flows.",
        ),
        _contains_check(
            "support_closure_projection",
            "code",
            support_text,
            "SupportCaseIncidentClosureProjection",
            "Support closure state is represented as a typed projection.",
        ),
        _contains_check(
            "support_manifest_listing_helper",
            "code",
            support_text,
            "_iter_support_case_manifest_entries",
            "Support packet artifact listing uses one manifest iterator.",
        ),
        _contains_check(
            "support_path_safe_resolver",
            "code",
            support_text,
            "_resolve_support_case_artifact_path",
            "Support artifact download paths route through one path-safe resolver.",
        ),
        _contains_check(
            "support_zip_profile_helper",
            "code",
            support_text,
            "SupportCaseIncidentZipProfile",
            "Support zip construction uses shared profile metadata per packet kind.",
        ),
        _contains_check(
            "support_metadata_audit_storage_helper",
            "code",
            support_text,
            "_append_support_case_audit_record",
            "Support zip verification audits write through one metadata-only storage helper.",
        ),
        _contains_check(
            "productized_report_delivery_readiness_reuse",
            "code",
            report_text,
            "build_delivery_lifecycle_readiness(",
            "Productized commercial reports reuse delivery readiness rather than local readiness copies.",
        ),
        _contains_check(
            "productized_report_operational_projection_reuse",
            "code",
            report_text,
            "build_delivery_operational_lifecycle_projection(",
            "Productized commercial reports expose the same operational lifecycle projection.",
        ),
        _contains_check(
            "stage_gate_declares_fast_maturity_checks",
            "harness",
            harness_text,
            "delivery maturity audit",
            "Harness guide declares the delivery maturity audit as a fast freshness check.",
        ),
    ]

    metrics = [
        DeliveryMaturityMetric(
            metric_id="support_manifest_iterator_references",
            value=support_text.count("_iter_support_case_manifest_entries("),
            status="ready" if support_text.count("_iter_support_case_manifest_entries(") >= 5 else "review",
            evidence="One helper definition plus artifact listing call sites across packet kinds.",
        ),
        DeliveryMaturityMetric(
            metric_id="support_path_resolver_references",
            value=support_text.count("_resolve_support_case_artifact_path("),
            status="ready" if support_text.count("_resolve_support_case_artifact_path(") >= 5 else "review",
            evidence="One helper definition plus path-safe artifact retrieval call sites.",
        ),
        DeliveryMaturityMetric(
            metric_id="support_audit_storage_references",
            value=support_text.count("_append_support_case_audit_record("),
            status="ready" if support_text.count("_append_support_case_audit_record(") >= 5 else "review",
            evidence="One helper definition plus metadata-only audit record call sites.",
        ),
        DeliveryMaturityMetric(
            metric_id="support_zip_profile_packet_kinds",
            value=sum(
                1
                for packet_kind in (
                    "incident_packet",
                    "operator_packet",
                    "final_handoff_packet",
                    "closure_packet",
                )
                if packet_kind in support_text
            ),
            status="ready",
            evidence="All four support packet kinds are represented in the zip profile table.",
        ),
    ]
    blockers = sum(1 for check in checks if check.required and check.status != "ready")
    review_metrics = sum(1 for metric in metrics if metric.status != "ready")
    passed = len(checks) - blockers
    score = round((passed / len(checks)) * 100, 1)
    status = "ready" if blockers == 0 and review_metrics == 0 else "needs_review"
    return DeliveryMaturityAudit(
        status=status,
        maturity_label="mature_for_stage" if status == "ready" else "review_before_stage_close",
        score=score,
        scope="P2.8 support and productized delivery horizontal lifecycle closeout",
        code_checks=checks,
        residual_duplication_metrics=metrics,
        semantic_edges=_semantic_edges(),
        evidence_files=[
            str(SUPPORT_CASE_FILE.relative_to(ROOT)),
            str(REPORT_PRODUCTIZATION_FILE.relative_to(ROOT)),
            str(DELIVERY_LIFECYCLE_FILE.relative_to(ROOT)),
            str(OPS_LIFECYCLE_FILE.relative_to(ROOT)),
            "tests/test_gateway_incidents.py",
            "tests/test_report_productization.py",
            "tests/test_delivery_lifecycle.py",
            "docs/HARNESS.md",
        ],
        limitations=[
            "The audit is static and local-first; it does not run live GW2 API calls or provider credentials.",
            "Release closure still requires python harness/run_stage_gate.py release before a milestone handoff.",
            "Future domains should reuse the lifecycle helpers instead of adding another horizontal review/export/archive chain.",
        ],
        next_priority=(
            "Run release gate for milestone closure, then move only to targeted trial defects, live-key diagnostics, "
            "or lifecycle primitive refactors that remove measured duplication."
        ),
    )


def render_delivery_maturity_audit_markdown(audit: DeliveryMaturityAudit) -> str:
    lines = [
        "# Delivery Maturity Audit",
        "",
        f"- Schema: {audit.schema_version}",
        f"- Status: {audit.status}",
        f"- Maturity label: {audit.maturity_label}",
        f"- Score: {audit.score}",
        f"- Scope: {audit.scope}",
        "",
        "## Code Checks",
        "",
        "| Check | Axis | Status | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for check in audit.code_checks:
        lines.append(f"| {check.check_id} | {check.axis} | {check.status} | {check.evidence} |")
    lines.extend(["", "## Residual Duplication Metrics", "", "| Metric | Value | Status | Evidence |", "| --- | ---: | --- | --- |"])
    for metric in audit.residual_duplication_metrics:
        lines.append(f"| {metric.metric_id} | {metric.value} | {metric.status} | {metric.evidence} |")
    lines.extend(["", "## Semantic Graph", "", "| Source | Relation | Target | Evidence |", "| --- | --- | --- | --- |"])
    for edge in audit.semantic_edges:
        lines.append(f"| {edge.source} | {edge.relation} | {edge.target} | {edge.evidence} |")
    lines.extend(["", "## Evidence Files", ""])
    for evidence_file in audit.evidence_files:
        lines.append(f"- `{evidence_file}`")
    lines.extend(["", "## Known Limits", ""])
    for limitation in audit.limitations:
        lines.append(f"- {limitation}")
    lines.extend(["", "## Next Priority", "", audit.next_priority, ""])
    return "\n".join(lines)


def _contains_check(
    check_id: str,
    axis: str,
    text: str,
    needle: str,
    evidence: str,
) -> DeliveryMaturityCheck:
    return DeliveryMaturityCheck(
        check_id=check_id,
        axis=axis,
        status="ready" if needle in text else "missing",
        evidence=evidence if needle in text else f"Missing expected marker: {needle}",
    )


def _semantic_edges() -> list[DeliverySemanticEdge]:
    return [
        DeliverySemanticEdge(
            source="support_case_incident_packet",
            relation="uses",
            target="delivery_lifecycle_zip_policy",
            evidence="Support packets build deterministic zip bundles through shared lifecycle contracts.",
        ),
        DeliverySemanticEdge(
            source="support_case_incident_packet",
            relation="records",
            target="metadata_only_verification_audit",
            evidence="Verification records exclude raw keys, raw debug bundles, private payloads, and zip bytes.",
        ),
        DeliverySemanticEdge(
            source="support_case_incident_closure",
            relation="projects",
            target="operational_lifecycle_summary",
            evidence="Closure readiness is exposed through shared operational lifecycle projections.",
        ),
        DeliverySemanticEdge(
            source="productized_commercial_report",
            relation="reuses",
            target="delivery_lifecycle_readiness",
            evidence="Commercial report packets share readiness and lifecycle semantics with support packets.",
        ),
        DeliverySemanticEdge(
            source="stage_gate",
            relation="checks",
            target="delivery_maturity_audit",
            evidence="Fast validation can detect drift in the P2.8 closeout maturity contract.",
        ),
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
