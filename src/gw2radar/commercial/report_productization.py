import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.commercial.account_value import (
    AccountValueSnapshot,
    build_account_value_snapshot,
    render_account_value_snapshot_csv,
    render_account_value_snapshot_markdown,
)
from gw2radar.commercial.build_fit import (
    AccountGearSnapshot,
    BuildImport,
    BuildSource,
    GearRequirement,
    GearSlot,
    evaluate_build_fit,
    get_build,
    import_build,
    list_builds,
    list_character_snapshots,
    render_build_fit_report,
)
from gw2radar.commercial.legendary_planner import (
    DEFAULT_USER_ID,
    recompute_legendary_plan,
    render_legendary_planner_report,
)
from gw2radar.commercial.report_engine import ensure_default_report_products, has_report_entitlement
from gw2radar.graph.graph_query import GraphData
from gw2radar.kb.kb_repository import list_rules
from gw2radar.security.log_sanitizer import sanitize_log_payload


PRODUCTIZED_REPORT_ROOT = Path("outputs") / "reports" / "productized"
SUPPORTED_PRODUCTIZED_FORMATS = {"markdown", "csv", "html"}


class ProductizedReportTemplate(BaseModel):
    template_id: str
    product_id: str
    title: str
    audience: str
    required_inputs: list[str] = Field(default_factory=list)
    sections: list[str] = Field(default_factory=list)
    export_formats: list[str] = Field(default_factory=lambda: sorted(SUPPORTED_PRODUCTIZED_FORMATS))
    boundary: str = "Paid report template is deterministic and stores no raw API keys or private source payloads."


class ProductizedReportManifest(BaseModel):
    schema_version: str = "gw2radar.productized_report_artifact.v1"
    artifact_id: str
    template_id: str
    product_id: str
    title: str
    format: str
    generated_at: datetime
    artifact_path: str
    manifest_path: str
    checksum_sha256: str
    sections: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    privacy_boundary: str = (
        "Summary-only commercial report artifact; excludes raw API keys, private source payloads, "
        "automatic trading instructions, and guaranteed-return claims."
    )
    manual_action_boundary: str = "All recommendations require manual player review and action."


REPORT_TEMPLATES = [
    ProductizedReportTemplate(
        template_id="account_value_analysis",
        product_id="account_value_report",
        title="Account Value Analysis Report",
        audience="Experienced players reviewing account value, price coverage, and do-not-sell risk.",
        required_inputs=["synced account summary", "stored market price snapshot"],
        sections=[
            "Executive Summary",
            "Account Value Snapshot",
            "Source Diagnostics",
            "Top Holdings CSV",
            "Warnings And Boundaries",
        ],
    ),
    ProductizedReportTemplate(
        template_id="legendary_gap_analysis",
        product_id="legendary_planner_pro_report",
        title="Legendary Gap And Portfolio Report",
        audience="Experienced legendary planners comparing shared requirements, cheap path, fast path, and do-not-sell materials.",
        required_inputs=["goal portfolio", "public legendary graph", "account value evidence"],
        sections=[
            "Active Legendary Portfolio",
            "Shared Material Conflicts",
            "Cheapest Path",
            "Fastest Path",
            "Do-Not-Sell List",
        ],
    ),
    ProductizedReportTemplate(
        template_id="build_readiness_advisor",
        product_id="build_fit_report",
        title="Build Readiness And Gear Transition Report",
        audience="Experienced players checking whether an account can play a build and what conversion costs remain.",
        required_inputs=["build import", "account gear snapshot", "account value evidence"],
        sections=[
            "Fit Score",
            "Gear Reuse",
            "Transition Plan",
            "Account Value Context",
            "Budget Alternative",
        ],
    ),
]


def list_productized_report_templates() -> list[ProductizedReportTemplate]:
    return REPORT_TEMPLATES


def get_productized_report_template(template_id: str) -> ProductizedReportTemplate | None:
    return next((template for template in REPORT_TEMPLATES if template.template_id == template_id), None)


def generate_productized_report_artifact(
    session: Session,
    graph: GraphData,
    *,
    user_id: str = DEFAULT_USER_ID,
    template_id: str,
    export_format: str = "markdown",
    build_id: str | None = None,
    account_gear: AccountGearSnapshot | None = None,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
) -> ProductizedReportManifest:
    ensure_default_report_products(session)
    template = get_productized_report_template(template_id)
    if template is None:
        raise ValueError("Unknown productized report template.")
    if export_format not in SUPPORTED_PRODUCTIZED_FORMATS:
        raise ValueError("Unsupported productized report format.")
    if not has_report_entitlement(session, user_id, template.product_id):
        raise PermissionError("Productized report requires an entitlement.")

    content, assumptions, evidence_refs, warnings = _render_template_content(
        session,
        graph,
        template,
        export_format=export_format,
        build_id=build_id,
        account_gear=account_gear,
    )
    artifact_id = f"productized_{template.template_id}_{uuid4().hex}"
    output_dir = output_root / artifact_id
    output_dir.mkdir(parents=True, exist_ok=True)
    extension = {"markdown": ".md", "csv": ".csv", "html": ".html"}[export_format]
    artifact_path = output_dir / f"{artifact_id}{extension}"
    manifest_path = output_dir / "manifest.json"
    artifact_path.write_text(content, encoding="utf-8")
    checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
    manifest = ProductizedReportManifest(
        artifact_id=artifact_id,
        template_id=template.template_id,
        product_id=template.product_id,
        title=template.title,
        format=export_format,
        generated_at=datetime.now(timezone.utc),
        artifact_path=artifact_path.as_posix(),
        manifest_path=manifest_path.as_posix(),
        checksum_sha256=checksum,
        sections=template.sections,
        assumptions=assumptions,
        evidence_refs=evidence_refs,
        warnings=warnings,
    )
    safe_manifest = sanitize_log_payload(manifest.model_dump(mode="json"))
    manifest_path.write_text(json.dumps(safe_manifest, indent=2, sort_keys=True), encoding="utf-8")
    return ProductizedReportManifest.model_validate(safe_manifest)


def resolve_productized_report_artifact_path(
    artifact_id: str,
    *,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
) -> Path | None:
    safe_id = Path(artifact_id).name
    for path in output_root.rglob(safe_id):
        if path.is_file() and output_root.resolve() in path.resolve().parents:
            return path
    return None


def _render_template_content(
    session: Session,
    graph: GraphData,
    template: ProductizedReportTemplate,
    *,
    export_format: str,
    build_id: str | None,
    account_gear: AccountGearSnapshot | None,
) -> tuple[str, list[str], list[str], list[str]]:
    if template.template_id == "account_value_analysis":
        snapshot = build_account_value_snapshot(graph, session, top_limit=25)
        return _account_value_content(snapshot, template, export_format)
    if template.template_id == "legendary_gap_analysis":
        result = recompute_legendary_plan(session, graph, user_id=DEFAULT_USER_ID)
        markdown = _product_header(template) + render_legendary_planner_report(result)
        csv = _legendary_gap_csv(result)
        return _format_content(markdown, csv, export_format), [], result.evidence_refs, []
    if template.template_id == "build_readiness_advisor":
        build = _load_or_create_build(session, build_id)
        gear = account_gear or _default_account_gear(graph)
        value_snapshot = build_account_value_snapshot(graph, session, top_limit=10000)
        result = evaluate_build_fit(build, gear, list_rules(session), value_snapshot)
        markdown = _product_header(template) + render_build_fit_report(result)
        csv = _build_readiness_csv(result)
        assumptions = [
            "Build readiness uses the selected build import and the provided or default account gear snapshot.",
            "Missing gear, conversion cost, and budget alternatives are planning estimates only.",
        ]
        warnings = [result.score.stale_warning] if result.score.stale_warning else []
        return _format_content(markdown, csv, export_format), assumptions, [], warnings
    raise ValueError("Unknown productized report template.")


def _account_value_content(
    snapshot: AccountValueSnapshot,
    template: ProductizedReportTemplate,
    export_format: str,
) -> tuple[str, list[str], list[str], list[str]]:
    markdown = _product_header(template) + render_account_value_snapshot_markdown(snapshot)
    csv = render_account_value_snapshot_csv(snapshot)
    warnings = [warning.player_message for warning in snapshot.warnings]
    return _format_content(markdown, csv, export_format), snapshot.assumptions, [], warnings


def _format_content(markdown: str, csv: str, export_format: str) -> str:
    if export_format == "markdown":
        return markdown
    if export_format == "csv":
        return csv
    escaped = markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<!doctype html><html><body><pre>{escaped}</pre></body></html>\n"


def _product_header(template: ProductizedReportTemplate) -> str:
    return "\n".join(
        [
            f"# {template.title}",
            "",
            f"- Audience: {template.audience}",
            "- Commercial report mode: productized",
            "- Privacy boundary: no raw API keys, no private source payloads, no automatic trading.",
            "- Assumption policy: missing facts are marked as assumptions; no invented market claims.",
            "",
        ]
    )


def _legendary_gap_csv(result) -> str:
    rows = ["row_type,entity_id,name,quantity,detail"]
    for item in result.shared_requirements:
        rows.append(f"shared,{_csv(item.entity_id)},{_csv(item.name)},{item.missing_quantity},{_csv(';'.join(item.required_by_goal_ids))}")
    for item in result.do_not_sell:
        rows.append(f"do_not_sell,{_csv(item.entity_id)},{_csv(item.name)},{item.owned_quantity},{_csv(item.policy)}")
    for step in result.cheap_path:
        rows.append(f"cheap_path,{_csv(step.entity_id)},{_csv(step.name)},{step.missing_quantity},{_csv(step.rationale)}")
    for step in result.fast_path:
        rows.append(f"fast_path,{_csv(step.entity_id)},{_csv(step.name)},{step.missing_quantity},{_csv(step.rationale)}")
    return "\n".join(rows) + "\n"


def _build_readiness_csv(result) -> str:
    rows = ["row_type,slot,item_name,matched,detail"]
    for match in result.matches:
        rows.append(
            ",".join(
                [
                    "gear_match",
                    _csv(match.requirement.slot.value),
                    _csv(match.requirement.item_name),
                    str(match.matched).lower(),
                    _csv(match.explanation),
                ]
            )
        )
    rows.append(f"score,,,{str(result.score.playable_now).lower()},{result.score.score:.3f}")
    rows.append(f"budget_alternative,,,{result.budget_alternative.estimated_savings_gold:g},{_csv(result.budget_alternative.suggestion)}")
    return "\n".join(rows) + "\n"


def _load_or_create_build(session: Session, build_id: str | None):
    if build_id:
        build = get_build(session, build_id)
        if build is None:
            raise ValueError("Build not found.")
        return build
    builds = list_builds(session, user_id=DEFAULT_USER_ID)
    if builds:
        return builds[0]
    return import_build(
        session,
        BuildImport(
            name="Productized Virtuoso Readiness Template",
            source=BuildSource(
                name="gw2radar_productized_sample",
                attribution="Deterministic sample used when no player build import exists.",
            ),
            profession="Mesmer",
            specialization="Virtuoso",
            role="Power DPS",
            game_mode="Strike",
            patch_version="reviewed-sample",
            difficulty="medium",
            requirements=[
                GearRequirement(slot=GearSlot.HEAD, item_name="Berserker Headgear", stat_combo="Berserker", estimated_cost_gold=4),
                GearRequirement(slot=GearSlot.CHEST, item_name="Berserker Chest", stat_combo="Berserker", estimated_cost_gold=8),
                GearRequirement(slot=GearSlot.WEAPON_1, item_name="Berserker Dagger", stat_combo="Berserker", estimated_cost_gold=6),
                GearRequirement(slot=GearSlot.RUNE, item_name="Power Rune Set", stat_combo="Power", estimated_cost_gold=12),
                GearRequirement(slot=GearSlot.RELIC, item_name="Power Relic", stat_combo="Power", estimated_cost_gold=8),
            ],
            estimated_transition_cost_gold=38,
        ),
        user_id=DEFAULT_USER_ID,
    )


def _default_account_gear(graph: GraphData) -> AccountGearSnapshot:
    snapshots = list_character_snapshots(graph)
    if snapshots:
        return snapshots[0].to_account_gear_snapshot()
    return AccountGearSnapshot(wallet_gold=0.0)


def _csv(value: str) -> str:
    text = str(value).replace('"', '""')
    if any(char in text for char in [",", "\n", '"']):
        return f'"{text}"'
    return text
