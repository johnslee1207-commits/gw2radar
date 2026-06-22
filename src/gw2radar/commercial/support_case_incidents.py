import hashlib
import json
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, Field

from gw2radar.commercial.gateway_incidents import GatewayIncidentHistory, GatewayIncidentReviewNoteList
from gw2radar.commercial.player_intelligence import PlayerSupportHandoffDashboard
from gw2radar.support.account_debug_bundle_audit import SupportReviewAuditRecord, SupportReviewMetricsSummary

SUPPORT_CASE_INCIDENT_PACKET_ROOT = Path("src/gw2radar/reports/artifacts/support_case_incident_packets")
SUPPORT_CASE_INCIDENT_PACKET_FILES = {"dashboard.json", "dashboard.md", "dashboard.csv", "manifest.json"}


class SupportCaseIncidentDashboard(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_dashboard.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    support_status: str
    status_cards: list[dict] = Field(default_factory=list)
    gateway_snapshot_count: int = 0
    gateway_note_count: int = 0
    gateway_open_count: int = 0
    gateway_assigned_count: int = 0
    gateway_closed_count: int = 0
    support_audit_count: int = 0
    handoff_ready: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident dashboard is read-only metadata; it excludes raw API keys, "
        "raw debug bundles, private account payloads, and zip bytes."
    )


class SupportCaseIncidentPacketFile(BaseModel):
    file_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    checksum_sha256: str


class SupportCaseIncidentPacketManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_packet_manifest.v1"
    packet_id: str
    packet_root: str
    generated_at: datetime
    source_dashboard_schema: str
    ready: bool
    maturity_label: str
    support_status: str
    file_count: int
    files: list[SupportCaseIncidentPacketFile]
    manifest_path: str
    checksum_sha256: str
    contains_raw_key: bool = False
    contains_raw_debug_bundle: bool = False
    contains_private_source_payload: bool = False
    contains_zip_bytes: bool = False
    boundary: str = (
        "Support case incident packets are deterministic metadata exports; they exclude raw API keys, "
        "raw debug bundles, private account payloads, zip bytes, and executable content."
    )


class SupportCaseIncidentPacketZipManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_packet_zip_manifest.v1"
    bundle_id: str
    source_packet_id: str
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    file_count: int
    included_files: list[SupportCaseIncidentPacketFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str = (
        "Support case incident packet zip bundles are read-only transfer files; they exclude raw API keys, "
        "raw debug bundles, private account payloads, zip bytes in manifests, and executable content."
    )


class SupportCaseIncidentPacketZipVerification(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_packet_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident packet zip verification reads zip bytes only; it does not execute, publish, "
        "or store uploaded content."
    )


def build_support_case_incident_dashboard(
    *,
    gateway_history: GatewayIncidentHistory,
    gateway_notes: GatewayIncidentReviewNoteList,
    support_audits: list[SupportReviewAuditRecord],
    support_metrics: SupportReviewMetricsSummary,
    handoff_dashboard: PlayerSupportHandoffDashboard,
) -> SupportCaseIncidentDashboard:
    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []
    if gateway_notes.open_count:
        blockers.append(f"{gateway_notes.open_count} gateway incident notes are still open.")
        next_actions.append("Assign or close open gateway incident notes before final support handoff.")
    if gateway_notes.assigned_count:
        warnings.append(f"{gateway_notes.assigned_count} gateway incident notes are assigned and need follow-up.")
        next_actions.append("Review assigned gateway incident notes and record close/defer decisions.")
    if gateway_history.comparison.status == "regressed":
        blockers.append("Gateway incident history regressed between the latest two snapshots.")
        next_actions.append("Inspect retry and failed event deltas before closing the support case.")
    if not support_audits:
        warnings.append("No account debug bundle support audit record is available.")
        next_actions.append("Save a privacy-safe support review audit for the latest debug bundle.")
    if not handoff_dashboard.ready:
        blockers.extend(handoff_dashboard.blockers)
        warnings.extend(handoff_dashboard.warnings)
        next_actions.extend(handoff_dashboard.next_actions)
    ready = not blockers and handoff_dashboard.ready
    support_status = "ready" if ready else "blocked" if blockers else "needs_review"
    status_cards = [
        {
            "card_id": "gateway_history",
            "label": "Gateway history",
            "status": gateway_history.comparison.status,
            "summary": f"{len(gateway_history.snapshots)} snapshots; comparison {gateway_history.comparison.status}.",
        },
        {
            "card_id": "gateway_notes",
            "label": "Gateway notes",
            "status": "ready" if not gateway_notes.open_count and not gateway_notes.assigned_count else "needs_review",
            "summary": (
                f"{len(gateway_notes.notes)} notes; open {gateway_notes.open_count}, "
                f"assigned {gateway_notes.assigned_count}, closed {gateway_notes.closed_count}."
            ),
        },
        {
            "card_id": "support_audits",
            "label": "Support audits",
            "status": "ready" if support_audits else "missing",
            "summary": f"{len(support_audits)} audit records; {support_metrics.trend_summary}",
        },
        {
            "card_id": "handoff_readiness",
            "label": "Handoff readiness",
            "status": handoff_dashboard.maturity_label,
            "summary": f"Ready {handoff_dashboard.ready}; {handoff_dashboard.audit_record_count} handoff audit records.",
        },
    ]
    return SupportCaseIncidentDashboard(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label="ready" if ready else "blocked" if blockers else "needs_review",
        support_status=support_status,
        status_cards=status_cards,
        gateway_snapshot_count=len(gateway_history.snapshots),
        gateway_note_count=len(gateway_notes.notes),
        gateway_open_count=gateway_notes.open_count,
        gateway_assigned_count=gateway_notes.assigned_count,
        gateway_closed_count=gateway_notes.closed_count,
        support_audit_count=len(support_audits),
        handoff_ready=handoff_dashboard.ready,
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        next_actions=_unique(next_actions) or ["Support case incident dashboard is ready for operator review."],
        evidence_refs=_unique(
            [
                "/api/v1/player/gateway-incidents/history",
                "/api/v1/player/gateway-incidents/review-notes",
                "/account/debug-bundle/review/audit",
                "/api/v1/player/support-handoff/dashboard",
            ]
            + handoff_dashboard.evidence_refs
        ),
    )


def render_support_case_incident_dashboard_markdown(dashboard: SupportCaseIncidentDashboard) -> str:
    lines = [
        "# Support Case Incident Dashboard",
        "",
        f"- Schema: {dashboard.schema_version}",
        f"- Ready: {dashboard.ready}",
        f"- Maturity: {dashboard.maturity_label}",
        f"- Support status: {dashboard.support_status}",
        f"- Gateway snapshots: {dashboard.gateway_snapshot_count}",
        f"- Gateway notes: {dashboard.gateway_note_count}",
        f"- Support audits: {dashboard.support_audit_count}",
        f"- Handoff ready: {dashboard.handoff_ready}",
        f"- Boundary: {dashboard.boundary}",
        "",
        "## Status Cards",
        "",
    ]
    for card in dashboard.status_cards:
        lines.append(f"- {card.get('label')}: {card.get('status')} - {card.get('summary')}")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {item}" for item in dashboard.blockers) if dashboard.blockers else lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in dashboard.warnings) if dashboard.warnings else lines.append("- None")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in dashboard.next_actions)
    return "\n".join(lines) + "\n"


def render_support_case_incident_dashboard_csv(dashboard: SupportCaseIncidentDashboard) -> str:
    rows = [
        "ready,maturity_label,support_status,gateway_snapshot_count,gateway_note_count,gateway_open_count,gateway_assigned_count,gateway_closed_count,support_audit_count,handoff_ready,blocker_count,warning_count",
        ",".join(
            [
                _csv(str(dashboard.ready)),
                _csv(dashboard.maturity_label),
                _csv(dashboard.support_status),
                _csv(str(dashboard.gateway_snapshot_count)),
                _csv(str(dashboard.gateway_note_count)),
                _csv(str(dashboard.gateway_open_count)),
                _csv(str(dashboard.gateway_assigned_count)),
                _csv(str(dashboard.gateway_closed_count)),
                _csv(str(dashboard.support_audit_count)),
                _csv(str(dashboard.handoff_ready)),
                _csv(str(len(dashboard.blockers))),
                _csv(str(len(dashboard.warnings))),
            ]
        ),
        "card_id,label,status,summary",
    ]
    for card in dashboard.status_cards:
        rows.append(
            ",".join(
                [
                    _csv(str(card.get("card_id") or "")),
                    _csv(str(card.get("label") or "")),
                    _csv(str(card.get("status") or "")),
                    _csv(str(card.get("summary") or "")),
                ]
            )
        )
    rows.extend(["", "next_action"])
    rows.extend(_csv(action) for action in dashboard.next_actions)
    return "\n".join(rows) + "\n"


def write_support_case_incident_packet(
    dashboard: SupportCaseIncidentDashboard,
    *,
    packet_root: Path | None = None,
) -> SupportCaseIncidentPacketManifest:
    root = packet_root or SUPPORT_CASE_INCIDENT_PACKET_ROOT
    generated_at = datetime.now(timezone.utc)
    packet_id = f"support-case-incident-packet-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    packet_dir = root / packet_id
    packet_dir.mkdir(parents=True, exist_ok=False)
    contents = {
        "dashboard.json": dashboard.model_dump_json(indent=2),
        "dashboard.md": render_support_case_incident_dashboard_markdown(dashboard),
        "dashboard.csv": render_support_case_incident_dashboard_csv(dashboard),
    }
    files: list[SupportCaseIncidentPacketFile] = []
    for file_name, text in contents.items():
        file_path = packet_dir / file_name
        file_path.write_text(text, encoding="utf-8")
        files.append(_packet_file_entry(root, file_path, file_name, _media_type(file_name), text))
    manifest_payload = {
        "schema_version": "gw2radar.support_case_incident_packet_manifest.v1",
        "packet_id": packet_id,
        "generated_at": generated_at.isoformat(),
        "source_dashboard_schema": dashboard.schema_version,
        "ready": dashboard.ready,
        "maturity_label": dashboard.maturity_label,
        "support_status": dashboard.support_status,
        "files": [file.model_dump(mode="json") for file in files],
        "contains_raw_key": False,
        "contains_raw_debug_bundle": False,
        "contains_private_source_payload": False,
        "contains_zip_bytes": False,
        "boundary": "Support case incident packets are deterministic metadata exports only.",
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path = packet_dir / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
    files.append(manifest_file)
    return SupportCaseIncidentPacketManifest(
        packet_id=packet_id,
        packet_root=root.as_posix(),
        generated_at=generated_at,
        source_dashboard_schema=dashboard.schema_version,
        ready=dashboard.ready,
        maturity_label=dashboard.maturity_label,
        support_status=dashboard.support_status,
        file_count=len(files),
        files=files,
        manifest_path=manifest_file.relative_path,
        checksum_sha256=_packet_checksum(files),
    )


def list_support_case_incident_packets(
    *,
    packet_root: Path | None = None,
    limit: int = 20,
) -> list[SupportCaseIncidentPacketManifest]:
    root = packet_root or SUPPORT_CASE_INCIDENT_PACKET_ROOT
    if not root.exists():
        return []
    packets: list[SupportCaseIncidentPacketManifest] = []
    safe_limit = max(1, min(limit, 100))
    for packet_dir in sorted([path for path in root.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)[:safe_limit]:
        manifest_path = packet_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        files = [
            SupportCaseIncidentPacketFile(**file)
            for file in manifest.get("files", [])
            if file.get("file_name") in SUPPORT_CASE_INCIDENT_PACKET_FILES
        ]
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
        if not any(file.file_name == "manifest.json" for file in files):
            files.append(manifest_file)
        packets.append(
            SupportCaseIncidentPacketManifest(
                packet_id=packet_dir.name,
                packet_root=root.as_posix(),
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
                source_dashboard_schema=manifest.get("source_dashboard_schema", ""),
                ready=bool(manifest.get("ready")),
                maturity_label=str(manifest.get("maturity_label") or "unknown"),
                support_status=str(manifest.get("support_status") or "unknown"),
                file_count=len(files),
                files=files,
                manifest_path=manifest_file.relative_path,
                checksum_sha256=_packet_checksum(files),
            )
        )
    return packets


def resolve_support_case_incident_packet_path(
    packet_id: str,
    file_name: str,
    *,
    packet_root: Path | None = None,
) -> Path | None:
    if "/" in packet_id or "\\" in packet_id or ".." in packet_id:
        return None
    if file_name not in SUPPORT_CASE_INCIDENT_PACKET_FILES:
        return None
    root = (packet_root or SUPPORT_CASE_INCIDENT_PACKET_ROOT).resolve()
    candidate = (root / packet_id / file_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_support_case_incident_packet_zip_bundle(
    *,
    packet_root: Path | None = None,
) -> tuple[SupportCaseIncidentPacketZipManifest, bytes]:
    packets = list_support_case_incident_packets(packet_root=packet_root, limit=1)
    if not packets:
        raise ValueError("No support case incident packets are available to bundle.")
    packet = packets[0]
    source_files: list[tuple[str, Path, str]] = []
    for file in packet.files:
        path = resolve_support_case_incident_packet_path(
            packet.packet_id,
            file.file_name,
            packet_root=packet_root,
        )
        if path is not None:
            source_files.append((file.file_name, path, file.media_type))
    included_files: list[SupportCaseIncidentPacketFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, path, media_type in sorted(source_files, key=lambda item: item[0]):
            if file_name not in SUPPORT_CASE_INCIDENT_PACKET_FILES:
                continue
            content = path.read_bytes()
            archive_path = f"support_case_incident_packet/{file_name}"
            info = ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
            included_files.append(
                SupportCaseIncidentPacketFile(
                    file_name=file_name,
                    relative_path=archive_path,
                    media_type=media_type,
                    size_bytes=len(content),
                    checksum_sha256=hashlib.sha256(content).hexdigest(),
                )
            )
    bundle_bytes = buffer.getvalue()
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    return (
        SupportCaseIncidentPacketZipManifest(
            bundle_id=f"support-case-incident-packet-zip:{checksum[:16]}",
            source_packet_id=packet.packet_id,
            generated_at=datetime.now(timezone.utc),
            filename=f"{packet.packet_id}_support_case_incident_packet.zip",
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
        ),
        bundle_bytes,
    )


def verify_support_case_incident_packet_zip_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> SupportCaseIncidentPacketZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    allowed_names = {f"support_case_incident_packet/{file_name}" for file_name in SUPPORT_CASE_INCIDENT_PACKET_FILES}
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("support case incident packet checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    blockers.append(f"support case incident packet contains unsafe path: {name}")
            extra_names = sorted(set(names) - allowed_names)
            missing_names = sorted(allowed_names - set(names))
            if extra_names:
                blockers.append("support case incident packet contains non-whitelisted files: " + ", ".join(extra_names))
            if missing_names:
                blockers.append("support case incident packet is missing required files: " + ", ".join(missing_names))
            for name in names:
                lowered = archive.read(name).lower()
                if b"secret-key" in lowered:
                    blockers.append(f"support case incident packet file contains prohibited secret marker: {name}")
            _verify_support_case_incident_packet_payloads(archive, names, blockers)
    except Exception as exc:
        blockers.append(f"support case incident packet zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("support case incident packet zip is larger than the MVP verification target of 5 MB")
    return SupportCaseIncidentPacketZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def _csv(value: str) -> str:
    text = str(value).replace('"', '""')
    if any(character in text for character in [",", "\n", '"']):
        return f'"{text}"'
    return text


def _packet_file_entry(
    root: Path,
    file_path: Path,
    file_name: str,
    media_type: str,
    text: str,
) -> SupportCaseIncidentPacketFile:
    return SupportCaseIncidentPacketFile(
        file_name=file_name,
        relative_path=file_path.relative_to(root).as_posix(),
        media_type=media_type,
        size_bytes=len(text.encode("utf-8")),
        checksum_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _packet_checksum(files: list[SupportCaseIncidentPacketFile]) -> str:
    payload = "\n".join(f"{file.relative_path}:{file.checksum_sha256}" for file in sorted(files, key=lambda item: item.relative_path))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _media_type(file_name: str) -> str:
    if file_name.endswith(".json"):
        return "application/json"
    if file_name.endswith(".md"):
        return "text/markdown"
    if file_name.endswith(".csv"):
        return "text/csv"
    return "text/plain"


def _verify_support_case_incident_packet_payloads(archive: ZipFile, names: list[str], blockers: list[str]) -> None:
    manifest_name = "support_case_incident_packet/manifest.json"
    dashboard_json_name = "support_case_incident_packet/dashboard.json"
    dashboard_md_name = "support_case_incident_packet/dashboard.md"
    dashboard_csv_name = "support_case_incident_packet/dashboard.csv"
    if manifest_name in names:
        try:
            manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
            if manifest.get("schema_version") != "gw2radar.support_case_incident_packet_manifest.v1":
                blockers.append("support case incident packet manifest schema mismatch")
            for flag in ["contains_raw_key", "contains_raw_debug_bundle", "contains_private_source_payload", "contains_zip_bytes"]:
                if manifest.get(flag) is not False:
                    blockers.append(f"support case incident packet manifest has unsafe flag: {flag}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            blockers.append(f"support case incident packet manifest validation failed: {exc}")
    if dashboard_json_name in names:
        try:
            dashboard = SupportCaseIncidentDashboard.model_validate_json(
                archive.read(dashboard_json_name).decode("utf-8")
            )
            if dashboard.schema_version != "gw2radar.support_case_incident_dashboard.v1":
                blockers.append("support case incident dashboard schema mismatch")
        except (UnicodeDecodeError, ValueError) as exc:
            blockers.append(f"support case incident dashboard JSON validation failed: {exc}")
    if dashboard_md_name in names:
        try:
            markdown = archive.read(dashboard_md_name).decode("utf-8")
            if "Support Case Incident Dashboard" not in markdown:
                blockers.append("support case incident dashboard Markdown title is missing")
        except UnicodeDecodeError as exc:
            blockers.append(f"support case incident dashboard Markdown is not UTF-8: {exc}")
    if dashboard_csv_name in names:
        try:
            csv_text = archive.read(dashboard_csv_name).decode("utf-8")
            if "ready,maturity_label,support_status" not in csv_text:
                blockers.append("support case incident dashboard CSV header mismatch")
        except UnicodeDecodeError as exc:
            blockers.append(f"support case incident dashboard CSV is not UTF-8: {exc}")
