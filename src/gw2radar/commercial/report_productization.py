import hashlib
import json
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

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
PRODUCTIZED_REPORT_AUDIT_ROOT = Path("outputs") / "reports" / "productized_audits"
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


class ProductizedReportPacketFile(BaseModel):
    file_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    checksum_sha256: str


class ProductizedReportPacketZipManifest(BaseModel):
    schema_version: str = "gw2radar.productized_report_packet_zip_manifest.v1"
    bundle_id: str
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    artifact_count: int
    file_count: int
    included_files: list[ProductizedReportPacketFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str = (
        "Productized report packet zip bundles contain report artifacts and manifests only; "
        "they exclude raw API keys, private source payloads, uploaded inputs, and executable content."
    )


class ProductizedReportPacketZipVerification(BaseModel):
    schema_version: str = "gw2radar.productized_report_packet_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = (
        "Productized report packet zip verification reads bytes only; it does not execute, publish, "
        "or store uploaded content."
    )


class ProductizedReportPacketZipVerificationAuditRequest(BaseModel):
    reviewer: str = "report-ops"
    notes: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class ProductizedReportPacketZipVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.productized_report_packet_zip_verification_audit.v1"
    audit_id: str
    recorded_at: datetime
    reviewer: str
    ready: bool
    checksum_sha256: str
    size_bytes: int
    file_count: int
    blocker_count: int
    warning_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source: str = "productized_report_packet_zip_verification"
    boundary: str = (
        "Productized report packet verification audit is metadata-only; it records checksum, file names, "
        "blockers, warnings, and reviewer notes without storing zip bytes, raw API keys, or private payloads."
    )


class ProductizedReportPacketZipVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.productized_report_packet_zip_verification_audit_list.v1"
    records: list[ProductizedReportPacketZipVerificationAuditRecord]
    boundary: str = (
        "Productized report packet verification audit exports are metadata-only and exclude zip content, "
        "raw API keys, and private source payloads."
    )


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


def list_productized_report_artifacts(
    *,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
    limit: int = 20,
) -> list[ProductizedReportManifest]:
    if not output_root.exists():
        return []
    manifests: list[ProductizedReportManifest] = []
    for manifest_path in sorted(output_root.rglob("manifest.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            manifest = ProductizedReportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        artifact_path = Path(manifest.artifact_path)
        if artifact_path.exists() and artifact_path.is_file():
            manifests.append(manifest)
        if len(manifests) >= max(1, min(limit, 100)):
            break
    return manifests


def build_productized_report_packet_zip_bundle(
    *,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
    limit: int = 20,
) -> tuple[ProductizedReportPacketZipManifest, bytes]:
    artifacts = list_productized_report_artifacts(output_root=output_root, limit=limit)
    if not artifacts:
        raise ValueError("No productized report artifacts are available to bundle.")
    included_files: list[ProductizedReportPacketFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for manifest in sorted(artifacts, key=lambda item: item.generated_at):
            artifact_path = Path(manifest.artifact_path)
            manifest_path = Path(manifest.manifest_path)
            for path in [artifact_path, manifest_path]:
                if not path.exists() or not path.is_file():
                    continue
                file_name = path.name
                content = path.read_bytes()
                archive_path = f"productized_report_packet/{manifest.artifact_id}/{file_name}"
                info = ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, content)
                included_files.append(
                    ProductizedReportPacketFile(
                        file_name=file_name,
                        relative_path=archive_path,
                        media_type=_media_type(file_name),
                        size_bytes=len(content),
                        checksum_sha256=hashlib.sha256(content).hexdigest(),
                    )
                )
    bundle_bytes = buffer.getvalue()
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    return (
        ProductizedReportPacketZipManifest(
            bundle_id=f"productized-report-packet-zip:{checksum[:16]}",
            generated_at=datetime.now(timezone.utc),
            filename=f"productized_report_packet_{checksum[:12]}.zip",
            artifact_count=len(artifacts),
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
        ),
        bundle_bytes,
    )


def verify_productized_report_packet_zip_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> ProductizedReportPacketZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("productized report packet checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            if not names:
                blockers.append("productized report packet zip contains no files")
            artifact_dirs: dict[str, set[str]] = {}
            for name in names:
                path = Path(name)
                parts = path.parts
                if path.is_absolute() or ".." in parts:
                    blockers.append(f"productized report packet contains unsafe path: {name}")
                    continue
                if len(parts) != 3 or parts[0] != "productized_report_packet":
                    blockers.append(f"productized report packet contains non-whitelisted path: {name}")
                    continue
                artifact_id = parts[1]
                file_name = parts[2]
                allowed_artifact_file = file_name == f"{artifact_id}.md" or file_name == f"{artifact_id}.csv" or file_name == f"{artifact_id}.html"
                if file_name != "manifest.json" and not allowed_artifact_file:
                    blockers.append(f"productized report packet contains non-whitelisted file: {name}")
                artifact_dirs.setdefault(artifact_id, set()).add(file_name)
            for artifact_id, files in artifact_dirs.items():
                has_report = any(file_name in files for file_name in {f"{artifact_id}.md", f"{artifact_id}.csv", f"{artifact_id}.html"})
                if "manifest.json" not in files:
                    blockers.append(f"productized report packet artifact is missing manifest.json: {artifact_id}")
                if not has_report:
                    blockers.append(f"productized report packet artifact is missing a report file: {artifact_id}")
            for name in names:
                if name.endswith(".zip"):
                    blockers.append(f"productized report packet contains nested zip content: {name}")
                lowered = archive.read(name).lower()
                if b"secret-key" in lowered or b"private_source_payload" in lowered:
                    blockers.append(f"productized report packet file contains prohibited private marker: {name}")
    except Exception as exc:
        blockers.append(f"productized report packet zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("productized report packet zip is larger than the MVP verification target of 5 MB")
    return ProductizedReportPacketZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def record_productized_report_packet_zip_verification_audit(
    request: ProductizedReportPacketZipVerificationAuditRequest,
    *,
    bundle_bytes: bytes | None = None,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
    audit_root: Path = PRODUCTIZED_REPORT_AUDIT_ROOT,
) -> ProductizedReportPacketZipVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        manifest, bundle_bytes = build_productized_report_packet_zip_bundle(output_root=output_root)
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_productized_report_packet_zip_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    recorded_at = datetime.now(timezone.utc)
    record = ProductizedReportPacketZipVerificationAuditRecord(
        audit_id=f"productized-report-packet-zip-audit-{recorded_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        recorded_at=recorded_at,
        reviewer=_safe_text(request.reviewer or "report-ops", max_length=80),
        ready=verification.ready,
        checksum_sha256=verification.checksum_sha256,
        size_bytes=verification.size_bytes,
        file_count=verification.file_count,
        blocker_count=len(verification.blockers),
        warning_count=len(verification.warnings),
        verified_files=verification.verified_files,
        blockers=verification.blockers,
        warnings=verification.warnings,
        notes=[_safe_text(note, max_length=240) for note in (request.notes or [])]
        or ["Productized report packet zip verification audit recorded."],
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    with (audit_root / "packet_zip_verification_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_productized_report_packet_zip_verification_audits(
    *,
    audit_root: Path = PRODUCTIZED_REPORT_AUDIT_ROOT,
    reviewer: str | None = None,
    limit: int = 20,
) -> ProductizedReportPacketZipVerificationAuditList:
    path = audit_root / "packet_zip_verification_audit.jsonl"
    if not path.exists():
        return ProductizedReportPacketZipVerificationAuditList(records=[])
    safe_reviewer = _safe_text(reviewer, max_length=80) if reviewer else None
    records: list[ProductizedReportPacketZipVerificationAuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = ProductizedReportPacketZipVerificationAuditRecord.model_validate_json(line)
        except ValueError:
            continue
        if safe_reviewer and record.reviewer != safe_reviewer:
            continue
        records.append(record)
    records.sort(key=lambda item: item.recorded_at, reverse=True)
    return ProductizedReportPacketZipVerificationAuditList(records=records[: max(1, min(limit, 100))])


def render_productized_report_packet_zip_verification_audit_markdown(
    audit: ProductizedReportPacketZipVerificationAuditList,
) -> str:
    lines = [
        "# Productized Report Packet Zip Verification Audit",
        "",
        f"- Records: {len(audit.records)}",
        "",
        "## Records",
    ]
    if not audit.records:
        lines.append("- No verification audit records are available.")
    for record in audit.records:
        lines.extend(
            [
                f"- {record.audit_id}",
                f"  - Reviewer: {record.reviewer}",
                f"  - Ready: {record.ready}",
                f"  - Checksum: {record.checksum_sha256}",
                f"  - Files: {record.file_count}",
                f"  - Blockers: {record.blocker_count}",
                f"  - Warnings: {record.warning_count}",
            ]
        )
    lines.extend(["", "## Boundary", "", f"- {audit.boundary}"])
    return "\n".join(lines) + "\n"


def render_productized_report_packet_zip_verification_audit_csv(
    audit: ProductizedReportPacketZipVerificationAuditList,
) -> str:
    rows = ["audit_id,recorded_at,reviewer,ready,checksum_sha256,size_bytes,file_count,blocker_count,warning_count"]
    for record in audit.records:
        rows.append(
            ",".join(
                [
                    _csv(record.audit_id),
                    _csv(record.recorded_at.isoformat()),
                    _csv(record.reviewer),
                    _csv(str(record.ready)),
                    _csv(record.checksum_sha256),
                    _csv(str(record.size_bytes)),
                    _csv(str(record.file_count)),
                    _csv(str(record.blocker_count)),
                    _csv(str(record.warning_count)),
                ]
            )
        )
    return "\n".join(rows) + "\n"


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


def _media_type(file_name: str) -> str:
    if file_name.endswith(".json"):
        return "application/json"
    if file_name.endswith(".csv"):
        return "text/csv"
    if file_name.endswith(".html"):
        return "text/html"
    return "text/markdown"


def _safe_text(value: str, *, max_length: int) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text[:max_length] or "report-ops"
