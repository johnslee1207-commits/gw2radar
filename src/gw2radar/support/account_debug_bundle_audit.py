from __future__ import annotations

import re
from csv import DictWriter
from datetime import datetime
from io import StringIO
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.db.models import SupportReviewAuditModel
from gw2radar.support.account_debug_bundle_review import SupportReviewReport


API_KEY_SHAPED_PATTERN = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){4,}-[0-9a-fA-F]{12,}")
LONG_SECRET_PATTERN = re.compile(r"[A-Za-z0-9_=-]{48,}")
SEVERITY_RANK = {"critical": 3, "warning": 2, "info": 1}


class SupportReviewAuditRecord(BaseModel):
    case_id: str
    bundle_schema_version: str | None = None
    review_schema_version: str
    overall_status: str
    summary: str
    highest_severity: str
    finding_count: int
    finding_ids: list[str] = Field(default_factory=list)
    reviewer: str
    source: str
    reply_template_summary: str
    properties: dict = Field(default_factory=dict)
    created_at: datetime


def create_support_review_audit(
    session: Session,
    *,
    review: SupportReviewReport,
    reviewer: str | None = None,
    reply_template: str | None = None,
    source: str = "support_workbench",
) -> SupportReviewAuditRecord:
    finding_ids = [finding.finding_id for finding in review.findings]
    severities = [finding.severity for finding in review.findings]
    record = SupportReviewAuditModel(
        case_id=f"support-review-{uuid4().hex}",
        bundle_schema_version=review.bundle_schema_version,
        review_schema_version=review.schema_version,
        overall_status=review.overall_status,
        summary=review.summary,
        highest_severity=_highest_severity(severities),
        finding_count=len(review.findings),
        finding_ids_json=finding_ids,
        reviewer=_safe_text(reviewer or "support", max_length=80),
        source=_safe_text(source, max_length=80),
        reply_template_summary=_safe_text(reply_template or "", max_length=360),
        properties_json={
            "evidence_refs": _evidence_refs(review),
            "redaction_boundary": list(review.redaction_boundary),
            "stores_raw_bundle": False,
            "stores_raw_api_key": False,
        },
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _to_record(record)


def list_support_review_audits(
    session: Session,
    *,
    limit: int = 20,
    status: str | None = None,
    severity: str | None = None,
    reviewer: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
) -> list[SupportReviewAuditRecord]:
    safe_limit = min(max(int(limit or 20), 1), 100)
    statement = select(SupportReviewAuditModel)
    if status:
        statement = statement.where(SupportReviewAuditModel.overall_status == _safe_text(status, max_length=80))
    if severity:
        statement = statement.where(SupportReviewAuditModel.highest_severity == _safe_text(severity, max_length=20))
    if reviewer:
        statement = statement.where(SupportReviewAuditModel.reviewer == _safe_text(reviewer, max_length=80))
    if created_from:
        statement = statement.where(SupportReviewAuditModel.created_at >= created_from)
    if created_to:
        statement = statement.where(SupportReviewAuditModel.created_at <= created_to)
    rows = session.scalars(statement.order_by(SupportReviewAuditModel.created_at.desc()).limit(safe_limit)).all()
    return [_to_record(row) for row in rows]


def render_support_review_audit_csv(records: list[SupportReviewAuditRecord]) -> str:
    output = StringIO()
    fieldnames = [
        "case_id",
        "created_at",
        "overall_status",
        "highest_severity",
        "finding_count",
        "finding_ids",
        "reviewer",
        "source",
        "bundle_schema_version",
        "reply_template_summary",
    ]
    writer = DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(
            {
                "case_id": record.case_id,
                "created_at": record.created_at.isoformat(),
                "overall_status": record.overall_status,
                "highest_severity": record.highest_severity,
                "finding_count": record.finding_count,
                "finding_ids": ";".join(record.finding_ids),
                "reviewer": record.reviewer,
                "source": record.source,
                "bundle_schema_version": record.bundle_schema_version or "",
                "reply_template_summary": record.reply_template_summary,
            }
        )
    return output.getvalue()


def _highest_severity(severities: list[str]) -> str:
    if not severities:
        return "info"
    return max(severities, key=lambda item: SEVERITY_RANK.get(item, 0))


def _safe_text(value: str, *, max_length: int) -> str:
    scrubbed = API_KEY_SHAPED_PATTERN.sub("[redacted-api-key-shaped-token]", str(value))
    scrubbed = LONG_SECRET_PATTERN.sub("[redacted-long-token]", scrubbed)
    scrubbed = " ".join(scrubbed.split())
    return scrubbed[:max_length]


def _evidence_refs(review: SupportReviewReport) -> list[str]:
    refs: list[str] = []
    for finding in review.findings:
        refs.extend(finding.evidence_refs)
    return refs[:20]


def _to_record(row: SupportReviewAuditModel) -> SupportReviewAuditRecord:
    return SupportReviewAuditRecord(
        case_id=row.case_id,
        bundle_schema_version=row.bundle_schema_version,
        review_schema_version=row.review_schema_version,
        overall_status=row.overall_status,
        summary=row.summary,
        highest_severity=row.highest_severity,
        finding_count=row.finding_count,
        finding_ids=list(row.finding_ids_json or []),
        reviewer=row.reviewer,
        source=row.source,
        reply_template_summary=row.reply_template_summary,
        properties=dict(row.properties_json or {}),
        created_at=row.created_at,
    )
