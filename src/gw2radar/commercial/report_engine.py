import json
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.orm import Session

from gw2radar.db.models import ReportEntitlementModel, ReportExportJobModel, ReportProductModel, utc_now
from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.kb.kb_models import KnowledgeReviewStatus, KnowledgeRule
from gw2radar.kb.kb_report_quality import score_kb_report_quality
from gw2radar.kb.patch_rule_audit import build_patch_rule_audit_manifest
from gw2radar.commercial.account_value import AccountValueSnapshot, build_account_value_snapshot, render_account_value_snapshot_markdown
from gw2radar.commercial.player_intelligence import render_freshness_markdown
from gw2radar.reports.markdown_report import generate_kb_backed_markdown_report, generate_markdown_report
from gw2radar.security.log_sanitizer import sanitize_log_payload


class ReportTier(StrEnum):
    FREE = "free"
    PAID_ONCE = "paid_once"
    SUBSCRIPTION = "subscription"


class ReportEntitlementType(StrEnum):
    PREVIEW = "preview"
    FULL = "full"
    SUBSCRIPTION = "subscription"


class ReportExportFormat(StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    ZIP = "zip"


class ReportJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ReportProduct(BaseModel):
    product_id: str
    name: str
    report_type: str
    tier: ReportTier
    price_cents: int | None = None
    enabled: bool = True


class ReportEntitlement(BaseModel):
    entitlement_id: str
    user_id: str
    product_id: str
    entitlement_type: ReportEntitlementType
    valid_until: datetime | None = None
    created_at: datetime


class ReportExportJob(BaseModel):
    job_id: str
    user_id: str
    report_type: str
    format: ReportExportFormat
    status: ReportJobStatus
    artifact_path: str | None = None
    manifest_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


DEFAULT_PRODUCTS = [
    ReportProduct(
        product_id="returner_preview_free",
        name="Returner Account Diagnosis Preview",
        report_type="returner",
        tier=ReportTier.FREE,
        price_cents=0,
    ),
    ReportProduct(
        product_id="returner_full_report",
        name="Returner Full Recovery Report",
        report_type="returner_full",
        tier=ReportTier.PAID_ONCE,
        price_cents=1000,
    ),
    ReportProduct(
        product_id="legendary_gap_report",
        name="Legendary Goal Gap Report",
        report_type="legendary",
        tier=ReportTier.PAID_ONCE,
        price_cents=900,
    ),
    ReportProduct(
        product_id="legendary_planner_pro_report",
        name="Legendary Planner Pro Report",
        report_type="legendary_pro",
        tier=ReportTier.PAID_ONCE,
        price_cents=1500,
    ),
    ReportProduct(
        product_id="build_fit_report",
        name="Build Fit Report",
        report_type="build_fit",
        tier=ReportTier.PAID_ONCE,
        price_cents=1200,
    ),
    ReportProduct(
        product_id="market_snapshot_report",
        name="Market Snapshot Report",
        report_type="market",
        tier=ReportTier.PAID_ONCE,
        price_cents=700,
    ),
]


def ensure_default_report_products(session: Session) -> None:
    for product in DEFAULT_PRODUCTS:
        existing = session.get(ReportProductModel, product.product_id)
        if existing is None:
            session.add(
                ReportProductModel(
                    product_id=product.product_id,
                    name=product.name,
                    report_type=product.report_type,
                    tier=product.tier.value,
                    price_cents=product.price_cents,
                    enabled=product.enabled,
                )
            )
    session.commit()


def list_report_products(session: Session) -> list[ReportProduct]:
    ensure_default_report_products(session)
    rows = (
        session.query(ReportProductModel)
        .filter(ReportProductModel.enabled.is_(True))
        .order_by(ReportProductModel.product_id)
        .all()
    )
    return [_product_from_model(row) for row in rows]


def create_report_entitlement(
    session: Session,
    user_id: str,
    product_id: str,
    entitlement_type: ReportEntitlementType = ReportEntitlementType.FULL,
) -> ReportEntitlement:
    entitlement = ReportEntitlementModel(
        entitlement_id=f"ent_{uuid4().hex}",
        user_id=user_id,
        product_id=product_id,
        entitlement_type=entitlement_type.value,
        created_at=utc_now(),
    )
    session.add(entitlement)
    session.commit()
    return _entitlement_from_model(entitlement)


def has_report_entitlement(session: Session, user_id: str, product_id: str) -> bool:
    product = session.get(ReportProductModel, product_id)
    if product is not None and product.tier == ReportTier.FREE.value:
        return True
    return (
        session.query(ReportEntitlementModel)
        .filter(
            ReportEntitlementModel.user_id == user_id,
            ReportEntitlementModel.product_id == product_id,
            ReportEntitlementModel.entitlement_type.in_(
                [ReportEntitlementType.FULL.value, ReportEntitlementType.SUBSCRIPTION.value]
            ),
        )
        .first()
        is not None
    )


def generate_report_preview(
    graph: GraphData,
    goal_id: str,
    report_type: str = "returner",
    output_root: Path = Path("outputs") / "reports",
) -> dict[str, str | dict]:
    markdown = _render_preview_markdown(graph, goal_id, report_type)
    artifact_path, manifest_path = _write_artifact(
        markdown,
        output_root=output_root,
        user_id="local-user",
        report_type=report_type,
        render_mode="preview",
        export_format=ReportExportFormat.MARKDOWN,
    )
    return {
        "render_mode": "preview",
        "report_type": report_type,
        "artifact_path": artifact_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "preview": markdown,
    }


def generate_report_job(
    session: Session,
    graph: GraphData,
    user_id: str,
    product_id: str,
    goal_id: str,
    export_format: ReportExportFormat = ReportExportFormat.MARKDOWN,
    output_root: Path = Path("outputs") / "reports",
    markdown_override: str | None = None,
    knowledge_backed: bool = False,
    knowledge_rules: list[KnowledgeRule] | None = None,
    account_value_snapshot: AccountValueSnapshot | None = None,
) -> ReportExportJob:
    ensure_default_report_products(session)
    product = session.get(ReportProductModel, product_id)
    if product is None or not product.enabled:
        raise ValueError("Unknown or disabled report product.")
    if not has_report_entitlement(session, user_id, product_id):
        raise PermissionError("Full report requires an entitlement.")

    now = utc_now()
    job = ReportExportJobModel(
        job_id=f"job_{uuid4().hex}",
        user_id=user_id,
        report_type=product.report_type,
        export_format=export_format.value,
        status=ReportJobStatus.QUEUED.value,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()

    try:
        job.status = ReportJobStatus.PROCESSING.value
        job.updated_at = utc_now()
        session.commit()
        markdown = markdown_override or _render_full_markdown(
            graph,
            goal_id,
            product.name,
            knowledge_backed=knowledge_backed,
            knowledge_rules=knowledge_rules or [],
        )
        if account_value_snapshot is None and product.report_type in {"legendary_pro", "build_fit", "market"}:
            account_value_snapshot = build_account_value_snapshot(graph, session)
        if account_value_snapshot is not None and "## Account Value Snapshot" not in markdown:
            markdown = markdown.rstrip() + "\n\n" + render_account_value_snapshot_markdown(account_value_snapshot)
        content = _render_export_content(markdown, export_format)
        kb_quality = _build_kb_quality_manifest(graph, goal_id, knowledge_rules or []) if knowledge_backed else None
        kb_audit = build_patch_rule_audit_manifest(knowledge_rules or []) if knowledge_backed else []
        artifact_path, manifest_path = _write_artifact(
            content,
            output_root=output_root,
            user_id=user_id,
            report_type=product.report_type,
            render_mode="full",
            export_format=export_format,
            knowledge_backed=knowledge_backed,
            knowledge_rule_count=_count_reviewed_enabled_rules(knowledge_rules or []),
            kb_quality=kb_quality,
            kb_audit=kb_audit,
            account_value_snapshot=account_value_snapshot,
        )
        job.status = ReportJobStatus.SUCCEEDED.value
        job.artifact_path = artifact_path.as_posix()
        job.manifest_path = manifest_path.as_posix()
        job.updated_at = utc_now()
        session.commit()
    except Exception as exc:
        job.status = ReportJobStatus.FAILED.value
        job.error_message = str(exc)
        job.updated_at = utc_now()
        session.commit()
    return _job_from_model(job)


def get_report_job(session: Session, job_id: str) -> ReportExportJob | None:
    row = session.get(ReportExportJobModel, job_id)
    return _job_from_model(row) if row is not None else None


def resolve_artifact_path(artifact_id: str, output_root: Path = Path("outputs") / "reports") -> Path | None:
    safe_id = Path(artifact_id).name
    for path in output_root.rglob(safe_id):
        if path.is_file() and output_root.resolve() in path.resolve().parents:
            return path
    return None


def _render_preview_markdown(graph: GraphData, goal_id: str, report_type: str) -> str:
    gap = calculate_goal_gap(graph, goal_id)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    lines = [
        "# GW2Radar Free Report Preview",
        "",
        f"- Report type: {report_type}",
        f"- Goal: {gap.goal_name}",
        f"- Progress: {gap.progress_percent:.2f}%",
        "",
        "## Top Recommendations",
    ]
    for action in actions[:3]:
        lines.extend(
            [
                f"- {action.title}",
                f"  - Why: {action.explanation}",
                "  - Boundary: informational recommendation only.",
            ]
        )
    lines.extend(
        [
            "",
            render_freshness_markdown(graph).rstrip(),
            "",
            "## Paid Detail Boundary",
            "- Full missing-material tables, complete do-not-sell policy, and export artifacts require a full report entitlement.",
            "- No API keys or unredacted private payloads are included.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_full_markdown(
    graph: GraphData,
    goal_id: str,
    product_name: str,
    knowledge_backed: bool = False,
    knowledge_rules: list[KnowledgeRule] | None = None,
) -> str:
    if knowledge_backed:
        base_report = generate_kb_backed_markdown_report(graph, goal_id, knowledge_rules or [])
    else:
        base_report = generate_markdown_report(graph, goal_id)
    header = [
        f"# {product_name}",
        "",
        "Commercial report mode: full",
        f"Knowledge-backed explanations: {str(knowledge_backed).lower()}",
        "",
        "Privacy boundary: no API keys, no unredacted private payloads, and recommendations require manual player action.",
        "",
        render_freshness_markdown(graph).rstrip(),
        "",
    ]
    return "\n".join(header) + base_report


def _render_export_content(markdown: str, export_format: ReportExportFormat) -> str:
    if export_format == ReportExportFormat.MARKDOWN:
        return markdown
    if export_format == ReportExportFormat.HTML:
        body = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f"<!doctype html><html><body><pre>{body}</pre></body></html>\n"
    if export_format == ReportExportFormat.PDF:
        return "PDF export interface stub. Render this manifest-backed report through a PDF renderer.\n"
    if export_format == ReportExportFormat.ZIP:
        return "ZIP export interface stub. Package artifact files through the export bundler.\n"
    raise ValueError("Unsupported export format for MVP report engine.")


def _write_artifact(
    content: str,
    output_root: Path,
    user_id: str,
    report_type: str,
    render_mode: str,
    export_format: ReportExportFormat,
    knowledge_backed: bool = False,
    knowledge_rule_count: int = 0,
    kb_quality: dict | None = None,
    kb_audit: list[dict] | None = None,
    account_value_snapshot: AccountValueSnapshot | None = None,
) -> tuple[Path, Path]:
    safe_user = _safe_slug(user_id)
    safe_report = _safe_slug(report_type)
    artifact_id = f"artifact_{uuid4().hex}"
    output_dir = output_root / safe_user / safe_report / artifact_id
    output_dir.mkdir(parents=True, exist_ok=True)

    extension = {
        ReportExportFormat.MARKDOWN: ".md",
        ReportExportFormat.HTML: ".html",
        ReportExportFormat.PDF: ".pdf.txt",
        ReportExportFormat.ZIP: ".zip.txt",
    }[export_format]
    artifact_path = output_dir / f"{artifact_id}{extension}"
    manifest_path = output_dir / "report_manifest.json"
    artifact_path.write_text(content, encoding="utf-8")

    manifest = sanitize_log_payload(
        {
            "schema_version": "gw2radar.report_artifact.v1",
            "artifact_id": artifact_id,
            "report_type": report_type,
            "render_mode": render_mode,
            "format": export_format.value,
            "artifact_path": artifact_path.as_posix(),
            "generated_at": datetime(2026, 6, 16, tzinfo=timezone.utc).isoformat(),
            "privacy_boundary": "no secrets and no unredacted private payloads",
            "recommendation_boundary": "informational_manual_actions_only",
            "knowledge_base": {
                "enabled": knowledge_backed,
                "reviewed_rule_count": knowledge_rule_count if knowledge_backed else 0,
                "boundary": "reviewed_enabled_rules_only",
                "quality": kb_quality,
                "patch_rule_audit": kb_audit or [],
            },
            "account_value_snapshot": _account_value_manifest(account_value_snapshot),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return artifact_path, manifest_path


def _account_value_manifest(snapshot: AccountValueSnapshot | None) -> dict:
    if snapshot is None:
        return {
            "enabled": False,
            "boundary": "No account value snapshot attached.",
        }
    return {
        "enabled": True,
        "schema_version": snapshot.schema_version,
        "account_id_present": bool(snapshot.account_id),
        "total_value_buy_copper": snapshot.summary.total_value_buy_copper,
        "net_sell_value_copper": snapshot.summary.net_sell_value_copper,
        "priced_holding_count": snapshot.summary.priced_holding_count,
        "unpriced_holding_count": snapshot.summary.unpriced_holding_count,
        "account_bound_holding_count": snapshot.summary.account_bound_holding_count,
        "reserved_holding_count": snapshot.summary.reserved_holding_count,
        "warning_count": len(snapshot.warnings),
        "boundary": "Summary metadata only; excludes raw API keys and private source payload details.",
    }


def _product_from_model(row: ReportProductModel) -> ReportProduct:
    return ReportProduct(
        product_id=row.product_id,
        name=row.name,
        report_type=row.report_type,
        tier=ReportTier(row.tier),
        price_cents=row.price_cents,
        enabled=bool(row.enabled),
    )


def _entitlement_from_model(row: ReportEntitlementModel) -> ReportEntitlement:
    return ReportEntitlement(
        entitlement_id=row.entitlement_id,
        user_id=row.user_id,
        product_id=row.product_id,
        entitlement_type=ReportEntitlementType(row.entitlement_type),
        valid_until=row.valid_until,
        created_at=row.created_at,
    )


def _job_from_model(row: ReportExportJobModel) -> ReportExportJob:
    return ReportExportJob(
        job_id=row.job_id,
        user_id=row.user_id,
        report_type=row.report_type,
        format=ReportExportFormat(row.export_format),
        status=ReportJobStatus(row.status),
        artifact_path=row.artifact_path,
        manifest_path=row.manifest_path,
        error_message=row.error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_").lower() or "unknown"


def _count_reviewed_enabled_rules(rules: list[KnowledgeRule]) -> int:
    return sum(1 for rule in rules if rule.enabled and rule.review_status == KnowledgeReviewStatus.REVIEWED)


def _build_kb_quality_manifest(graph: GraphData, goal_id: str, rules: list[KnowledgeRule]) -> dict:
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    quality = score_kb_report_quality(actions, rules)
    return {
        "explanation_coverage_percent": quality.explanation_coverage_percent,
        "explained_actions": quality.explained_actions,
        "matched_rule_count": quality.matched_rule_count,
        "total_actions": quality.total_actions,
        "quality_label": quality.quality_label,
        "low_confidence_explanation_count": quality.low_confidence_explanation_count,
        "warning_count": len(quality.warnings),
    }
