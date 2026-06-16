import csv
from io import StringIO

from gw2radar.kb.patch_impact_review import PatchReviewDashboardItem


PATCH_DASHBOARD_CSV_FIELDS = [
    "patch_id",
    "date",
    "year",
    "lifecycle_status",
    "review_status",
    "affected_systems",
    "candidate_rule_count",
    "persisted_rule_count",
    "enabled_rule_count",
    "audit_event_count",
    "audit_action_counts",
    "latest_reviewer",
    "latest_audit_at",
    "rule_ids",
    "evidence_id",
    "source_pdf",
]


def render_patch_dashboard_markdown(items: list[PatchReviewDashboardItem]) -> str:
    lines = [
        "# Patch Review Dashboard",
        "",
        f"- Total patches: {len(items)}",
        "- Boundary: review queue export only; does not copy raw PDF source text.",
        "",
        "| Date | Patch | Status | Review | Rules | Audit | Reviewer |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for item in items:
        lines.append(
            "| "
            + " | ".join(
                [
                    item.date,
                    item.patch_id,
                    item.lifecycle_status,
                    item.review_status.value,
                    str(item.persisted_rule_count),
                    str(item.audit_event_count),
                    item.latest_reviewer or "",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Evidence Index", ""])
    for item in items:
        lines.extend(
            [
                f"### {item.patch_id}",
                f"- source_pdf: `{item.source_pdf}`",
                f"- evidence_id: `{item.evidence_id}`",
                f"- affected_systems: `{_join(item.affected_systems)}`",
                f"- build_impact: `{_join(item.possible_build_impact)}`",
                f"- market_impact: `{_join(item.possible_market_impact)}`",
                "",
            ]
        )
    return "\n".join(lines)


def render_patch_dashboard_csv(items: list[PatchReviewDashboardItem]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=PATCH_DASHBOARD_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for item in items:
        writer.writerow(
            {
                "patch_id": item.patch_id,
                "date": item.date,
                "year": item.year,
                "lifecycle_status": item.lifecycle_status,
                "review_status": item.review_status.value,
                "affected_systems": _join(item.affected_systems),
                "candidate_rule_count": item.candidate_rule_count,
                "persisted_rule_count": item.persisted_rule_count,
                "enabled_rule_count": item.enabled_rule_count,
                "audit_event_count": item.audit_event_count,
                "audit_action_counts": _format_counts(item.audit_action_counts),
                "latest_reviewer": item.latest_reviewer or "",
                "latest_audit_at": item.latest_audit_at.isoformat() if item.latest_audit_at else "",
                "rule_ids": _join(item.rule_ids),
                "evidence_id": item.evidence_id,
                "source_pdf": item.source_pdf,
            }
        )
    return buffer.getvalue()


def _join(values: list[str]) -> str:
    return ";".join(values)


def _format_counts(counts: dict[str, int]) -> str:
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))
