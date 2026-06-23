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


class ProductizedReportDeliveryChecklist(BaseModel):
    schema_version: str = "gw2radar.productized_report_delivery_checklist.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    template_count: int
    artifact_count: int
    packet_file_count: int
    packet_checksum_sha256: str | None = None
    packet_verification_ready: bool = False
    verification_audit_count: int = 0
    latest_verification_audit_id: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Delivery checklist is operational metadata only; it excludes raw API keys, private source payloads, "
        "automatic publishing, automatic trading, and guaranteed-return claims."
    )


class ProductizedReportOperatorHandoffPacket(BaseModel):
    schema_version: str = "gw2radar.productized_report_operator_handoff_packet.v1"
    packet_id: str
    generated_at: datetime
    ready: bool
    maturity_label: str
    checklist: ProductizedReportDeliveryChecklist
    template_summary: list[dict] = Field(default_factory=list)
    artifact_summary: list[dict] = Field(default_factory=list)
    zip_manifest: dict = Field(default_factory=dict)
    audit_summary: dict = Field(default_factory=dict)
    runbook_steps: list[str] = Field(default_factory=list)
    transfer_files: list[str] = Field(default_factory=list)
    operator_next_actions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Operator handoff packet is a metadata and runbook wrapper for manual fulfillment; it does not store "
        "zip bytes, raw API keys, private source payloads, or executable delivery content."
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


def build_productized_report_delivery_checklist(
    *,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
    audit_root: Path = PRODUCTIZED_REPORT_AUDIT_ROOT,
    limit: int = 20,
) -> ProductizedReportDeliveryChecklist:
    templates = list_productized_report_templates()
    artifacts = list_productized_report_artifacts(output_root=output_root, limit=limit)
    packet_manifest: ProductizedReportPacketZipManifest | None = None
    verification: ProductizedReportPacketZipVerification | None = None
    blockers: list[str] = []
    warnings: list[str] = []

    if artifacts:
        try:
            packet_manifest, bundle_bytes = build_productized_report_packet_zip_bundle(
                output_root=output_root,
                limit=limit,
            )
            verification = verify_productized_report_packet_zip_bundle(
                bundle_bytes,
                expected_checksum_sha256=packet_manifest.checksum_sha256,
            )
            blockers.extend(verification.blockers)
            warnings.extend(verification.warnings)
        except ValueError as exc:
            blockers.append(str(exc))
    else:
        blockers.append("No productized report artifacts are available for delivery.")

    audits = list_productized_report_packet_zip_verification_audits(audit_root=audit_root, limit=limit)
    missing_gates: list[str] = []
    if len(templates) < 3:
        missing_gates.append("All three commercial report templates must be registered.")
    if len(artifacts) < 3:
        missing_gates.append("Generate at least one artifact for each productized report template.")
    if packet_manifest is None or packet_manifest.file_count < max(1, len(artifacts) * 2):
        missing_gates.append("Build a packet zip containing each report artifact and manifest.")
    if verification is None or not verification.ready:
        missing_gates.append("Packet zip verification must pass before handoff.")
    if not audits.records:
        missing_gates.append("Record at least one metadata-only verification audit.")

    latest_audit = audits.records[0] if audits.records else None
    checklist_items = [
        f"Productized templates registered: {len(templates)}.",
        f"Report artifacts generated: {len(artifacts)}.",
        f"Packet zip files included: {packet_manifest.file_count if packet_manifest else 0}.",
        f"Packet verification ready: {bool(verification and verification.ready)}.",
        f"Verification audit records: {len(audits.records)}.",
    ]
    next_actions = []
    if missing_gates:
        next_actions.extend(missing_gates)
    else:
        next_actions.extend(
            [
                "Download the productized report packet zip from the reports API.",
                "Confirm the zip checksum against the checklist before manual delivery.",
                "Export the audit CSV or Markdown if the customer handoff requires evidence.",
            ]
        )
    evidence_refs = [f"template:{template.template_id}" for template in templates]
    evidence_refs.extend(f"artifact:{artifact.artifact_id}" for artifact in artifacts)
    if packet_manifest:
        evidence_refs.append(f"packet_checksum:{packet_manifest.checksum_sha256}")
    if latest_audit:
        evidence_refs.append(f"audit:{latest_audit.audit_id}")

    ready = not missing_gates and not blockers
    return ProductizedReportDeliveryChecklist(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label="ready" if ready else "needs_review",
        template_count=len(templates),
        artifact_count=len(artifacts),
        packet_file_count=packet_manifest.file_count if packet_manifest else 0,
        packet_checksum_sha256=packet_manifest.checksum_sha256 if packet_manifest else None,
        packet_verification_ready=bool(verification and verification.ready),
        verification_audit_count=len(audits.records),
        latest_verification_audit_id=latest_audit.audit_id if latest_audit else None,
        checklist_items=checklist_items,
        missing_gates=missing_gates,
        blockers=blockers,
        warnings=warnings,
        next_actions=next_actions,
        evidence_refs=evidence_refs,
    )


def build_productized_report_operator_handoff_packet(
    *,
    output_root: Path = PRODUCTIZED_REPORT_ROOT,
    audit_root: Path = PRODUCTIZED_REPORT_AUDIT_ROOT,
    limit: int = 20,
) -> ProductizedReportOperatorHandoffPacket:
    checklist = build_productized_report_delivery_checklist(
        output_root=output_root,
        audit_root=audit_root,
        limit=limit,
    )
    templates = list_productized_report_templates()
    artifacts = list_productized_report_artifacts(output_root=output_root, limit=limit)
    zip_manifest: dict = {}
    transfer_files: list[str] = []
    try:
        manifest, _bundle_bytes = build_productized_report_packet_zip_bundle(output_root=output_root, limit=limit)
        zip_manifest = manifest.model_dump(mode="json")
        transfer_files = [file.relative_path for file in manifest.included_files]
    except ValueError:
        zip_manifest = {}
    audits = list_productized_report_packet_zip_verification_audits(audit_root=audit_root, limit=limit)
    packet_id = f"productized-report-operator-handoff-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}"
    ready_count = sum(1 for record in audits.records if record.ready)
    blocker_count = sum(record.blocker_count for record in audits.records)
    warning_count = sum(record.warning_count for record in audits.records)
    return ProductizedReportOperatorHandoffPacket(
        packet_id=packet_id,
        generated_at=datetime.now(timezone.utc),
        ready=checklist.ready,
        maturity_label=checklist.maturity_label,
        checklist=checklist,
        template_summary=[
            {
                "template_id": template.template_id,
                "product_id": template.product_id,
                "title": template.title,
                "export_formats": template.export_formats,
            }
            for template in templates
        ],
        artifact_summary=[
            {
                "artifact_id": artifact.artifact_id,
                "template_id": artifact.template_id,
                "product_id": artifact.product_id,
                "format": artifact.format,
                "checksum_sha256": artifact.checksum_sha256,
                "artifact_path": Path(artifact.artifact_path).name,
                "manifest_path": Path(artifact.manifest_path).name,
            }
            for artifact in artifacts
        ],
        zip_manifest=zip_manifest,
        audit_summary={
            "schema_version": "gw2radar.productized_report_operator_audit_summary.v1",
            "record_count": len(audits.records),
            "latest_audit_id": audits.records[0].audit_id if audits.records else None,
            "ready_count": ready_count,
            "blocker_count": blocker_count,
            "warning_count": warning_count,
        },
        runbook_steps=[
            "Confirm Account Value, Legendary Gap, and Build Readiness artifacts are present.",
            "Download the productized report packet zip and compare the SHA-256 checksum.",
            "Confirm verification audit readiness and export the audit evidence when required.",
            "Deliver the zip manually through the approved customer channel.",
            "Remind the recipient that all recommendations require manual player review and action.",
        ],
        transfer_files=transfer_files,
        operator_next_actions=checklist.next_actions,
        safety_boundaries=[
            "Do not include raw API keys or private source payloads in the handoff.",
            "Do not publish or deploy customer artifacts automatically.",
            "Do not make guaranteed profit, automatic trading, or automatic gear-change claims.",
            "Use checksum and audit evidence before delivery.",
        ],
        evidence_refs=checklist.evidence_refs,
    )


def render_productized_report_delivery_checklist_markdown(
    checklist: ProductizedReportDeliveryChecklist,
) -> str:
    lines = [
        "# Productized Report Delivery Checklist",
        "",
        f"- Ready: {checklist.ready}",
        f"- Maturity: {checklist.maturity_label}",
        f"- Templates: {checklist.template_count}",
        f"- Artifacts: {checklist.artifact_count}",
        f"- Packet files: {checklist.packet_file_count}",
        f"- Packet checksum: {checklist.packet_checksum_sha256 or 'not available'}",
        f"- Verification audits: {checklist.verification_audit_count}",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist.checklist_items)
    lines.extend(["", "## Missing Gates"])
    lines.extend(f"- {gate}" for gate in checklist.missing_gates) if checklist.missing_gates else lines.append("- None.")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {action}" for action in checklist.next_actions)
    lines.extend(["", "## Boundary", "", f"- {checklist.boundary}"])
    return "\n".join(lines) + "\n"


def render_productized_report_delivery_checklist_csv(
    checklist: ProductizedReportDeliveryChecklist,
) -> str:
    rows = [
        "ready,maturity_label,template_count,artifact_count,packet_file_count,packet_verification_ready,verification_audit_count,packet_checksum_sha256,latest_verification_audit_id",
        ",".join(
            [
                _csv(str(checklist.ready)),
                _csv(checklist.maturity_label),
                _csv(str(checklist.template_count)),
                _csv(str(checklist.artifact_count)),
                _csv(str(checklist.packet_file_count)),
                _csv(str(checklist.packet_verification_ready)),
                _csv(str(checklist.verification_audit_count)),
                _csv(checklist.packet_checksum_sha256 or ""),
                _csv(checklist.latest_verification_audit_id or ""),
            ]
        ),
    ]
    return "\n".join(rows) + "\n"


def render_productized_report_operator_handoff_packet_markdown(
    packet: ProductizedReportOperatorHandoffPacket,
) -> str:
    lines = [
        "# Productized Report Operator Handoff Packet",
        "",
        f"- Packet ID: {packet.packet_id}",
        f"- Ready: {packet.ready}",
        f"- Maturity: {packet.maturity_label}",
        f"- Transfer files: {len(packet.transfer_files)}",
        "",
        "## Runbook",
    ]
    lines.extend(f"- {step}" for step in packet.runbook_steps)
    lines.extend(["", "## Templates"])
    for template in packet.template_summary:
        lines.append(f"- {template.get('template_id')}: {template.get('title')}")
    lines.extend(["", "## Artifacts"])
    for artifact in packet.artifact_summary:
        lines.append(f"- {artifact.get('artifact_id')} ({artifact.get('format')}): {artifact.get('checksum_sha256')}")
    lines.extend(["", "## Safety Boundaries"])
    lines.extend(f"- {boundary}" for boundary in packet.safety_boundaries)
    lines.extend(["", "## Boundary", "", f"- {packet.boundary}"])
    return "\n".join(lines) + "\n"


def render_productized_report_operator_handoff_packet_csv(
    packet: ProductizedReportOperatorHandoffPacket,
) -> str:
    rows = [
        "packet_id,ready,maturity_label,template_count,artifact_count,packet_file_count,audit_record_count,transfer_file_count",
        ",".join(
            [
                _csv(packet.packet_id),
                _csv(str(packet.ready)),
                _csv(packet.maturity_label),
                _csv(str(packet.checklist.template_count)),
                _csv(str(packet.checklist.artifact_count)),
                _csv(str(packet.checklist.packet_file_count)),
                _csv(str(packet.audit_summary.get("record_count", 0))),
                _csv(str(len(packet.transfer_files))),
            ]
        ),
    ]
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
