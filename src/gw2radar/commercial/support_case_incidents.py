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
SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT = Path("src/gw2radar/reports/artifacts/support_case_incident_packet_audits")
SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_ROOT = Path("src/gw2radar/reports/artifacts/support_case_incident_operator_packets")
SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES = {
    "operator_packet.json",
    "operator_packet.md",
    "operator_packet.csv",
    "checklist.md",
    "dashboard.md",
    "packet_manifest.json",
    "zip_manifest.json",
    "verification_audit.csv",
    "manifest.json",
}
SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_ROOT = Path(
    "src/gw2radar/reports/artifacts/support_case_incident_final_handoff_packets"
)
SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES = {
    "checklist.json",
    "checklist.md",
    "checklist.csv",
    "operator_artifact_manifest.json",
    "operator_zip_verification_audit.csv",
    "manifest.json",
}


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


class SupportCaseIncidentPacketZipVerificationAuditRequest(BaseModel):
    reviewer: str = "support"
    notes: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class SupportCaseIncidentPacketZipVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_packet_zip_verification_audit.v1"
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
    source: str = "support_case_incident_packet_zip_verification"
    boundary: str = (
        "Support case incident packet verification audit is metadata-only; it records checksum, "
        "file names, blockers, warnings, and reviewer notes without storing zip bytes, raw API keys, "
        "raw debug bundles, or private account payloads."
    )


class SupportCaseIncidentPacketZipVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_packet_zip_verification_audit_list.v1"
    records: list[SupportCaseIncidentPacketZipVerificationAuditRecord]
    boundary: str = (
        "Support case incident packet verification audit exports are metadata-only and exclude zip "
        "content, raw API keys, raw debug bundles, and private account payloads."
    )


class SupportCaseIncidentHandoffChecklist(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_handoff_checklist.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    dashboard_ready: bool = False
    latest_packet_id: str | None = None
    packet_file_count: int = 0
    zip_checksum_sha256: str | None = None
    zip_file_count: int = 0
    zip_verification_ready: bool = False
    verification_audit_count: int = 0
    latest_verification_audit_id: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident handoff checklist is metadata-only; it summarizes dashboard, packet, "
        "zip, verification, and audit gates without storing zip bytes, raw API keys, raw debug bundles, "
        "or private account payloads."
    )


class SupportCaseIncidentOperatorPacket(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet.v1"
    packet_id: str
    generated_at: datetime
    ready: bool
    maturity_label: str
    checklist: SupportCaseIncidentHandoffChecklist
    dashboard_summary: dict = Field(default_factory=dict)
    packet_manifest: dict = Field(default_factory=dict)
    zip_manifest: dict = Field(default_factory=dict)
    audit_summary: dict = Field(default_factory=dict)
    runbook_steps: list[str] = Field(default_factory=list)
    transfer_files: list[str] = Field(default_factory=list)
    support_next_actions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident operator packet is metadata-only; it packages checklist, dashboard, "
        "manifest, zip manifest, and audit export references without storing zip bytes, raw API keys, "
        "raw debug bundles, or private account payloads."
    )


class SupportCaseIncidentOperatorPacketManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet_manifest.v1"
    artifact_id: str
    artifact_root: str
    generated_at: datetime
    source_operator_packet_id: str
    ready: bool
    maturity_label: str
    file_count: int
    files: list[SupportCaseIncidentPacketFile]
    manifest_path: str
    checksum_sha256: str
    contains_raw_key: bool = False
    contains_raw_debug_bundle: bool = False
    contains_private_source_payload: bool = False
    contains_zip_bytes: bool = False
    contains_executable_content: bool = False
    allowed_files: list[str] = Field(default_factory=lambda: sorted(SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES))
    boundary: str = (
        "Support case incident operator packet files are deterministic metadata exports and exclude "
        "zip bytes, raw API keys, raw debug bundles, private account payloads, and executable content."
    )


class SupportCaseIncidentOperatorPacketZipManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet_zip_manifest.v1"
    bundle_id: str
    source_artifact_id: str
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    file_count: int
    included_files: list[SupportCaseIncidentPacketFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str = (
        "Support case incident operator packet zip bundles are read-only metadata transfer files; "
        "they exclude raw API keys, raw debug bundles, private account payloads, nested zip bytes, "
        "and executable content."
    )


class SupportCaseIncidentOperatorPacketZipVerification(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident operator packet zip verification reads bytes only; it does not execute, "
        "publish, or store uploaded content."
    )


class SupportCaseIncidentOperatorPacketZipVerificationAuditRequest(BaseModel):
    reviewer: str = "support"
    notes: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class SupportCaseIncidentOperatorPacketZipVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet_zip_verification_audit.v1"
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
    source: str = "support_case_incident_operator_packet_zip_verification"
    boundary: str = (
        "Support case incident operator packet zip verification audit is metadata-only; it records "
        "checksum, file names, blockers, warnings, and reviewer notes without storing zip bytes, "
        "raw API keys, raw debug bundles, or private account payloads."
    )


class SupportCaseIncidentOperatorPacketZipVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_operator_packet_zip_verification_audit_list.v1"
    records: list[SupportCaseIncidentOperatorPacketZipVerificationAuditRecord]
    boundary: str = (
        "Support case incident operator packet zip verification audit exports are metadata-only and "
        "exclude zip content, raw API keys, raw debug bundles, and private account payloads."
    )


class SupportCaseIncidentFinalHandoffChecklist(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_checklist.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    latest_operator_artifact_id: str | None = None
    operator_artifact_file_count: int = 0
    operator_zip_checksum_sha256: str | None = None
    operator_zip_file_count: int = 0
    operator_zip_verification_ready: bool = False
    operator_zip_audit_count: int = 0
    latest_operator_zip_audit_id: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident final handoff checklist is metadata-only; it summarizes operator "
        "artifact, zip, verification, and audit gates without storing zip bytes, raw API keys, "
        "raw debug bundles, or private account payloads."
    )


class SupportCaseIncidentFinalHandoffPacketManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_packet_manifest.v1"
    packet_id: str
    artifact_root: str
    generated_at: datetime
    source_checklist_schema_version: str
    ready: bool
    maturity_label: str
    file_count: int
    files: list[SupportCaseIncidentPacketFile]
    manifest_path: str
    checksum_sha256: str
    contains_raw_key: bool = False
    contains_raw_debug_bundle: bool = False
    contains_private_source_payload: bool = False
    contains_zip_bytes: bool = False
    contains_executable_content: bool = False
    allowed_files: list[str] = Field(default_factory=lambda: sorted(SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES))
    boundary: str = (
        "Support case incident final handoff packet files are deterministic metadata exports and "
        "exclude zip bytes, raw API keys, raw debug bundles, private account payloads, and executable content."
    )


class SupportCaseIncidentFinalHandoffPacketZipManifest(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_packet_zip_manifest.v1"
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
        "Support case incident final handoff packet zip bundles are read-only metadata transfer files; "
        "they exclude raw API keys, raw debug bundles, private account payloads, nested zip bytes, "
        "and executable content."
    )


class SupportCaseIncidentFinalHandoffPacketZipVerification(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_packet_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support case incident final handoff packet zip verification reads bytes only; it does not execute, "
        "publish, or store uploaded content."
    )


class SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRequest(BaseModel):
    reviewer: str = "support"
    notes: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_packet_zip_verification_audit.v1"
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
    source: str = "support_case_incident_final_handoff_packet_zip_verification"
    boundary: str = (
        "Support case incident final handoff packet zip verification audit is metadata-only; it records "
        "checksum, file names, blockers, warnings, and reviewer notes without storing zip bytes, "
        "raw API keys, raw debug bundles, or private account payloads."
    )


class SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.support_case_incident_final_handoff_packet_zip_verification_audit_list.v1"
    records: list[SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord]
    boundary: str = (
        "Support case incident final handoff packet zip verification audit exports are metadata-only and "
        "exclude zip content, raw API keys, raw debug bundles, and private account payloads."
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


def record_support_case_incident_packet_zip_verification_audit(
    request: SupportCaseIncidentPacketZipVerificationAuditRequest,
    *,
    bundle_bytes: bytes | None = None,
    packet_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentPacketZipVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        manifest, bundle_bytes = build_support_case_incident_packet_zip_bundle(packet_root=packet_root)
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_support_case_incident_packet_zip_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    recorded_at = datetime.now(timezone.utc)
    record = SupportCaseIncidentPacketZipVerificationAuditRecord(
        audit_id=f"support-case-incident-packet-zip-audit-{recorded_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        recorded_at=recorded_at,
        reviewer=_safe_text(request.reviewer or "support", max_length=80),
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
        or ["Support case incident packet zip verification audit recorded."],
    )
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with (root / "verification_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_support_case_incident_packet_zip_verification_audits(
    *,
    audit_root: Path | None = None,
    reviewer: str | None = None,
    limit: int = 20,
) -> SupportCaseIncidentPacketZipVerificationAuditList:
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    path = root / "verification_audit.jsonl"
    if not path.exists():
        return SupportCaseIncidentPacketZipVerificationAuditList(records=[])
    safe_reviewer = _safe_text(reviewer, max_length=80) if reviewer else None
    records: list[SupportCaseIncidentPacketZipVerificationAuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = SupportCaseIncidentPacketZipVerificationAuditRecord.model_validate_json(line)
        except ValueError:
            continue
        if safe_reviewer and record.reviewer != safe_reviewer:
            continue
        records.append(record)
    records.sort(key=lambda item: item.recorded_at, reverse=True)
    return SupportCaseIncidentPacketZipVerificationAuditList(records=records[: max(1, min(limit, 100))])


def render_support_case_incident_packet_zip_verification_audit_markdown(
    audit: SupportCaseIncidentPacketZipVerificationAuditList,
) -> str:
    lines = [
        "# Support Case Incident Packet Zip Verification Audit",
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


def render_support_case_incident_packet_zip_verification_audit_csv(
    audit: SupportCaseIncidentPacketZipVerificationAuditList,
) -> str:
    rows = [
        "audit_id,recorded_at,reviewer,ready,checksum_sha256,size_bytes,file_count,blocker_count,warning_count"
    ]
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


def build_support_case_incident_handoff_checklist(
    *,
    dashboard: SupportCaseIncidentDashboard | None = None,
    packet_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentHandoffChecklist:
    packets = list_support_case_incident_packets(packet_root=packet_root, limit=1)
    latest_packet = packets[0] if packets else None
    missing_gates: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    zip_manifest: SupportCaseIncidentPacketZipManifest | None = None
    zip_verification: SupportCaseIncidentPacketZipVerification | None = None
    dashboard_ready = bool(dashboard.ready) if dashboard else bool(latest_packet and latest_packet.ready)
    if dashboard is None and latest_packet is None:
        missing_gates.append("support case incident dashboard")
    if dashboard is not None:
        blockers.extend(dashboard.blockers)
        warnings.extend(dashboard.warnings)
    if not dashboard_ready:
        missing_gates.append("support case incident dashboard ready state")
    if latest_packet is None:
        missing_gates.append("support case incident packet")
    else:
        if latest_packet.file_count < len(SUPPORT_CASE_INCIDENT_PACKET_FILES):
            missing_gates.append("support case incident packet required files")
        if not latest_packet.ready:
            missing_gates.append("support case incident packet ready state")
    if latest_packet is not None:
        try:
            zip_manifest, zip_bytes = build_support_case_incident_packet_zip_bundle(packet_root=packet_root)
            zip_verification = verify_support_case_incident_packet_zip_bundle(
                zip_bytes,
                expected_checksum_sha256=zip_manifest.checksum_sha256,
            )
        except ValueError as exc:
            blockers.append(str(exc))
    if zip_manifest is None or zip_manifest.file_count < len(SUPPORT_CASE_INCIDENT_PACKET_FILES):
        missing_gates.append("support case incident packet zip bundle")
    if zip_verification is None or not zip_verification.ready:
        missing_gates.append("support case incident packet zip verification")
    audit = list_support_case_incident_packet_zip_verification_audits(audit_root=audit_root, limit=1)
    latest_audit = audit.records[0] if audit.records else None
    if latest_audit is None:
        missing_gates.append("support case incident packet zip verification audit")
    elif not latest_audit.ready:
        missing_gates.append("latest support case incident packet zip verification audit ready state")
    if zip_verification:
        blockers.extend(zip_verification.blockers)
        warnings.extend(zip_verification.warnings)
    if latest_audit:
        blockers.extend(latest_audit.blockers)
        warnings.extend(latest_audit.warnings)
    ready = not missing_gates and not blockers
    if blockers:
        maturity_label = "blocked"
    elif missing_gates or warnings:
        maturity_label = "review_needed"
    else:
        maturity_label = "ready"
    next_actions = (
        [
            "Resolve missing support case incident handoff gates before attaching the incident packet.",
            "Re-run zip verification and record a fresh metadata-only audit after blockers are fixed.",
        ]
        if not ready
        else [
            "Attach the incident packet zip, verification audit export, and handoff checklist to the support case.",
            "Continue support triage without requesting raw API keys or private account payloads.",
        ]
    )
    return SupportCaseIncidentHandoffChecklist(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label=maturity_label,
        dashboard_ready=dashboard_ready,
        latest_packet_id=latest_packet.packet_id if latest_packet else None,
        packet_file_count=latest_packet.file_count if latest_packet else 0,
        zip_checksum_sha256=zip_manifest.checksum_sha256 if zip_manifest else None,
        zip_file_count=zip_manifest.file_count if zip_manifest else 0,
        zip_verification_ready=zip_verification.ready if zip_verification else False,
        verification_audit_count=len(audit.records),
        latest_verification_audit_id=latest_audit.audit_id if latest_audit else None,
        checklist_items=[
            "Support case incident dashboard reviewed and ready.",
            "Support case incident packet files written and indexed.",
            "Support case incident packet zip generated from whitelist files.",
            "Support case incident packet zip verified without executing content.",
            "Support case incident packet zip verification audit recorded as metadata only.",
        ],
        missing_gates=_unique(missing_gates),
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        next_actions=next_actions,
        evidence_refs=[
            "/api/v1/player/support-case/incident-dashboard",
            "/api/v1/player/support-case/incident-packet",
            "/api/v1/player/support-case/incident-packet/bundle",
            "/api/v1/player/support-case/incident-packet/bundle/verify",
            "/api/v1/player/support-case/incident-packet/bundle/verification-audit",
        ],
    )


def render_support_case_incident_handoff_checklist_markdown(
    checklist: SupportCaseIncidentHandoffChecklist,
) -> str:
    lines = [
        "# Support Case Incident Handoff Checklist",
        "",
        f"- Ready: {checklist.ready}",
        f"- Maturity: {checklist.maturity_label}",
        f"- Dashboard ready: {checklist.dashboard_ready}",
        f"- Latest packet: {checklist.latest_packet_id or 'None'}",
        f"- Packet files: {checklist.packet_file_count}",
        f"- Zip files: {checklist.zip_file_count}",
        f"- Zip checksum: {checklist.zip_checksum_sha256 or 'None'}",
        f"- Zip verification ready: {checklist.zip_verification_ready}",
        f"- Verification audit records: {checklist.verification_audit_count}",
        f"- Boundary: {checklist.boundary}",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist.checklist_items)
    lines.extend(["", "## Missing Gates"])
    lines.extend(f"- {item}" for item in checklist.missing_gates) if checklist.missing_gates else lines.append("- None")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in checklist.blockers) if checklist.blockers else lines.append("- None")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in checklist.warnings) if checklist.warnings else lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in checklist.next_actions)
    return "\n".join(lines) + "\n"


def render_support_case_incident_handoff_checklist_csv(
    checklist: SupportCaseIncidentHandoffChecklist,
) -> str:
    rows = [
        "ready,maturity_label,dashboard_ready,latest_packet_id,packet_file_count,zip_file_count,zip_verification_ready,verification_audit_count,missing_gate_count,blocker_count,warning_count",
        ",".join(
            [
                _csv(str(checklist.ready)),
                _csv(checklist.maturity_label),
                _csv(str(checklist.dashboard_ready)),
                _csv(checklist.latest_packet_id or ""),
                _csv(str(checklist.packet_file_count)),
                _csv(str(checklist.zip_file_count)),
                _csv(str(checklist.zip_verification_ready)),
                _csv(str(checklist.verification_audit_count)),
                _csv(str(len(checklist.missing_gates))),
                _csv(str(len(checklist.blockers))),
                _csv(str(len(checklist.warnings))),
            ]
        ),
    ]
    rows.extend(f"checklist_item,{_csv(item)}" for item in checklist.checklist_items)
    rows.extend(f"missing_gate,{_csv(item)}" for item in checklist.missing_gates)
    rows.extend(f"blocker,{_csv(item)}" for item in checklist.blockers)
    rows.extend(f"warning,{_csv(item)}" for item in checklist.warnings)
    rows.extend(f"next_action,{_csv(item)}" for item in checklist.next_actions)
    return "\n".join(rows) + "\n"


def build_support_case_incident_operator_packet(
    *,
    dashboard: SupportCaseIncidentDashboard | None = None,
    packet_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentOperatorPacket:
    checklist = build_support_case_incident_handoff_checklist(
        dashboard=dashboard,
        packet_root=packet_root,
        audit_root=audit_root,
    )
    packets = list_support_case_incident_packets(packet_root=packet_root, limit=1)
    latest_packet = packets[0] if packets else None
    packet_manifest = latest_packet.model_dump(mode="json") if latest_packet else {}
    zip_manifest_payload: dict = {}
    try:
        zip_manifest, _bundle_bytes = build_support_case_incident_packet_zip_bundle(packet_root=packet_root)
        zip_manifest_payload = zip_manifest.model_dump(mode="json")
    except ValueError:
        zip_manifest_payload = {}
    audit = list_support_case_incident_packet_zip_verification_audits(audit_root=audit_root, limit=5)
    latest_audit = audit.records[0] if audit.records else None
    audit_summary = {
        "schema_version": audit.schema_version,
        "record_count": len(audit.records),
        "latest_audit_id": latest_audit.audit_id if latest_audit else None,
        "latest_reviewer": latest_audit.reviewer if latest_audit else None,
        "latest_ready": latest_audit.ready if latest_audit else None,
        "latest_checksum_sha256": latest_audit.checksum_sha256 if latest_audit else None,
    }
    dashboard_summary = (
        {
            "schema_version": dashboard.schema_version,
            "ready": dashboard.ready,
            "maturity_label": dashboard.maturity_label,
            "support_status": dashboard.support_status,
            "gateway_note_count": dashboard.gateway_note_count,
            "support_audit_count": dashboard.support_audit_count,
            "handoff_ready": dashboard.handoff_ready,
        }
        if dashboard
        else {}
    )
    support_next_actions = checklist.next_actions + [
        "Attach the operator packet artifact manifest with the incident support case.",
        "Use manifest checksums to verify every metadata file before closing the incident.",
    ]
    return SupportCaseIncidentOperatorPacket(
        packet_id=f"support-case-incident-operator-packet-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        generated_at=datetime.now(timezone.utc),
        ready=checklist.ready,
        maturity_label=checklist.maturity_label,
        checklist=checklist,
        dashboard_summary=dashboard_summary,
        packet_manifest=packet_manifest,
        zip_manifest=zip_manifest_payload,
        audit_summary=audit_summary,
        runbook_steps=[
            "Confirm the handoff checklist is ready before attaching incident packet files.",
            "Attach metadata files and the verified incident packet zip; never attach raw API keys or raw debug bundles.",
            "Compare zip checksum with the latest verification audit before sending or closing the case.",
            "Use dashboard Markdown for human triage and CSV exports for queue/reporting views.",
            "Record a fresh verification audit if the packet zip changes.",
        ],
        transfer_files=[
            "support_case_incident_packet.zip",
            "support_case_incident_handoff_checklist.md",
            "support_case_incident_packet_zip_verification_audit.csv",
            "support_case_incident_operator_packet_manifest.json",
        ],
        support_next_actions=_unique(support_next_actions),
        safety_boundaries=[
            "Do not request or store raw GW2 API keys.",
            "Do not request raw debug bundles after metadata evidence is available.",
            "Do not execute files from incident packet archives.",
            "Do not treat readiness as a live game-state or support-resolution guarantee.",
        ],
        evidence_refs=_unique(
            checklist.evidence_refs
            + [
                "/api/v1/player/support-case/incident-handoff-checklist",
                "/api/v1/player/support-case/incident-operator-packet",
            ]
        ),
    )


def render_support_case_incident_operator_packet_markdown(packet: SupportCaseIncidentOperatorPacket) -> str:
    lines = [
        "# Support Case Incident Operator Packet",
        "",
        f"- Packet id: {packet.packet_id}",
        f"- Ready: {packet.ready}",
        f"- Maturity: {packet.maturity_label}",
        f"- Generated: {packet.generated_at.isoformat()}",
        f"- Zip checksum: {packet.zip_manifest.get('checksum_sha256') or 'None'}",
        f"- Latest audit: {packet.audit_summary.get('latest_audit_id') or 'None'}",
        f"- Boundary: {packet.boundary}",
        "",
        "## Runbook Steps",
    ]
    lines.extend(f"- {item}" for item in packet.runbook_steps)
    lines.extend(["", "## Transfer Files"])
    lines.extend(f"- {item}" for item in packet.transfer_files)
    lines.extend(["", "## Support Next Actions"])
    lines.extend(f"- {item}" for item in packet.support_next_actions)
    lines.extend(["", "## Safety Boundaries"])
    lines.extend(f"- {item}" for item in packet.safety_boundaries)
    lines.extend(["", "## Evidence Refs"])
    lines.extend(f"- {item}" for item in packet.evidence_refs)
    return "\n".join(lines) + "\n"


def render_support_case_incident_operator_packet_csv(packet: SupportCaseIncidentOperatorPacket) -> str:
    rows = [
        "packet_id,ready,maturity_label,zip_checksum_sha256,audit_record_count,latest_audit_id",
        ",".join(
            [
                _csv(packet.packet_id),
                _csv(str(packet.ready)),
                _csv(packet.maturity_label),
                _csv(str(packet.zip_manifest.get("checksum_sha256") or "")),
                _csv(str(packet.audit_summary.get("record_count") or 0)),
                _csv(str(packet.audit_summary.get("latest_audit_id") or "")),
            ]
        ),
        "section,value",
    ]
    rows.extend(f"runbook_step,{_csv(item)}" for item in packet.runbook_steps)
    rows.extend(f"transfer_file,{_csv(item)}" for item in packet.transfer_files)
    rows.extend(f"next_action,{_csv(item)}" for item in packet.support_next_actions)
    rows.extend(f"safety_boundary,{_csv(item)}" for item in packet.safety_boundaries)
    return "\n".join(rows) + "\n"


def write_support_case_incident_operator_packet_artifacts(
    packet: SupportCaseIncidentOperatorPacket,
    *,
    artifact_root: Path | None = None,
) -> SupportCaseIncidentOperatorPacketManifest:
    root = artifact_root or SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_ROOT
    generated_at = datetime.now(timezone.utc)
    artifact_id = f"support-case-incident-operator-packet-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    artifact_dir = root / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    contents = {
        "operator_packet.json": packet.model_dump_json(indent=2),
        "operator_packet.md": render_support_case_incident_operator_packet_markdown(packet),
        "operator_packet.csv": render_support_case_incident_operator_packet_csv(packet),
        "checklist.md": render_support_case_incident_handoff_checklist_markdown(packet.checklist),
        "dashboard.md": _render_operator_dashboard_summary_markdown(packet),
        "packet_manifest.json": json.dumps(packet.packet_manifest, indent=2, sort_keys=True),
        "zip_manifest.json": json.dumps(packet.zip_manifest, indent=2, sort_keys=True),
        "verification_audit.csv": _render_operator_audit_summary_csv(packet),
    }
    files: list[SupportCaseIncidentPacketFile] = []
    for file_name, text in contents.items():
        file_path = artifact_dir / file_name
        file_path.write_text(text, encoding="utf-8")
        files.append(_packet_file_entry(root, file_path, file_name, _media_type(file_name), text))
    manifest_payload = {
        "schema_version": "gw2radar.support_case_incident_operator_packet_manifest.v1",
        "artifact_id": artifact_id,
        "generated_at": generated_at.isoformat(),
        "source_operator_packet_id": packet.packet_id,
        "ready": packet.ready,
        "maturity_label": packet.maturity_label,
        "files": [file.model_dump(mode="json") for file in files],
        "contains_raw_key": False,
        "contains_raw_debug_bundle": False,
        "contains_private_source_payload": False,
        "contains_zip_bytes": False,
        "contains_executable_content": False,
        "allowed_files": sorted(SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES),
        "boundary": "Support case incident operator packet artifacts store metadata only.",
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
    files.append(manifest_file)
    return SupportCaseIncidentOperatorPacketManifest(
        artifact_id=artifact_id,
        artifact_root=root.as_posix(),
        generated_at=generated_at,
        source_operator_packet_id=packet.packet_id,
        ready=packet.ready,
        maturity_label=packet.maturity_label,
        file_count=len(files),
        files=files,
        manifest_path=manifest_file.relative_path,
        checksum_sha256=_packet_checksum(files),
    )


def list_support_case_incident_operator_packet_artifacts(
    *,
    artifact_root: Path | None = None,
    limit: int = 20,
) -> list[SupportCaseIncidentOperatorPacketManifest]:
    root = artifact_root or SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_ROOT
    if not root.exists():
        return []
    artifacts: list[SupportCaseIncidentOperatorPacketManifest] = []
    for artifact_dir in sorted([path for path in root.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)[: max(1, min(limit, 100))]:
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        files = [
            SupportCaseIncidentPacketFile(**file)
            for file in manifest.get("files", [])
            if file.get("file_name") in SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES
        ]
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
        if not any(file.file_name == "manifest.json" for file in files):
            files.append(manifest_file)
        artifacts.append(
            SupportCaseIncidentOperatorPacketManifest(
                artifact_id=artifact_dir.name,
                artifact_root=root.as_posix(),
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
                source_operator_packet_id=str(manifest.get("source_operator_packet_id") or "unknown"),
                ready=bool(manifest.get("ready")),
                maturity_label=str(manifest.get("maturity_label") or "unknown"),
                file_count=len(files),
                files=files,
                manifest_path=manifest_file.relative_path,
                checksum_sha256=_packet_checksum(files),
            )
        )
    return artifacts


def resolve_support_case_incident_operator_packet_artifact_path(
    artifact_id: str,
    file_name: str,
    *,
    artifact_root: Path | None = None,
) -> Path | None:
    if "/" in artifact_id or "\\" in artifact_id or ".." in artifact_id:
        return None
    if file_name not in SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES:
        return None
    root = (artifact_root or SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_ROOT).resolve()
    candidate = (root / artifact_id / file_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_support_case_incident_operator_packet_zip_bundle(
    *,
    artifact_root: Path | None = None,
) -> tuple[SupportCaseIncidentOperatorPacketZipManifest, bytes]:
    artifacts = list_support_case_incident_operator_packet_artifacts(artifact_root=artifact_root, limit=1)
    if not artifacts:
        raise ValueError("No support case incident operator packet artifacts are available to bundle.")
    artifact = artifacts[0]
    source_files: list[tuple[str, Path, str]] = []
    for file in artifact.files:
        path = resolve_support_case_incident_operator_packet_artifact_path(
            artifact.artifact_id,
            file.file_name,
            artifact_root=artifact_root,
        )
        if path is not None:
            source_files.append((file.file_name, path, file.media_type))
    included_files: list[SupportCaseIncidentPacketFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, path, media_type in sorted(source_files, key=lambda item: item[0]):
            if file_name not in SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES:
                continue
            content = path.read_bytes()
            archive_path = f"support_case_incident_operator_packet/{file_name}"
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
        SupportCaseIncidentOperatorPacketZipManifest(
            bundle_id=f"support-case-incident-operator-packet-zip:{checksum[:16]}",
            source_artifact_id=artifact.artifact_id,
            generated_at=datetime.now(timezone.utc),
            filename=f"{artifact.artifact_id}_operator_packet.zip",
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
        ),
        bundle_bytes,
    )


def verify_support_case_incident_operator_packet_zip_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> SupportCaseIncidentOperatorPacketZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    allowed_names = {
        f"support_case_incident_operator_packet/{file_name}"
        for file_name in SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES
    }
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("support case incident operator packet checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    blockers.append(f"support case incident operator packet contains unsafe path: {name}")
            extra_names = sorted(set(names) - allowed_names)
            missing_names = sorted(allowed_names - set(names))
            if extra_names:
                blockers.append(
                    "support case incident operator packet contains non-whitelisted files: "
                    + ", ".join(extra_names)
                )
            if missing_names:
                blockers.append(
                    "support case incident operator packet is missing required files: "
                    + ", ".join(missing_names)
                )
            for name in names:
                lowered = archive.read(name).lower()
                if b"secret-key" in lowered:
                    blockers.append(f"support case incident operator packet file contains prohibited secret marker: {name}")
            _verify_support_case_incident_operator_packet_payloads(archive, names, blockers)
    except Exception as exc:
        blockers.append(f"support case incident operator packet zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("support case incident operator packet zip is larger than the MVP verification target of 5 MB")
    return SupportCaseIncidentOperatorPacketZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def record_support_case_incident_operator_packet_zip_verification_audit(
    request: SupportCaseIncidentOperatorPacketZipVerificationAuditRequest,
    *,
    bundle_bytes: bytes | None = None,
    artifact_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentOperatorPacketZipVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        manifest, bundle_bytes = build_support_case_incident_operator_packet_zip_bundle(artifact_root=artifact_root)
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_support_case_incident_operator_packet_zip_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    recorded_at = datetime.now(timezone.utc)
    record = SupportCaseIncidentOperatorPacketZipVerificationAuditRecord(
        audit_id=f"support-case-incident-operator-packet-zip-audit-{recorded_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        recorded_at=recorded_at,
        reviewer=_safe_text(request.reviewer or "support", max_length=80),
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
        or ["Support case incident operator packet zip verification audit recorded."],
    )
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with (root / "operator_packet_zip_verification_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_support_case_incident_operator_packet_zip_verification_audits(
    *,
    audit_root: Path | None = None,
    reviewer: str | None = None,
    limit: int = 20,
) -> SupportCaseIncidentOperatorPacketZipVerificationAuditList:
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    path = root / "operator_packet_zip_verification_audit.jsonl"
    if not path.exists():
        return SupportCaseIncidentOperatorPacketZipVerificationAuditList(records=[])
    safe_reviewer = _safe_text(reviewer, max_length=80) if reviewer else None
    records: list[SupportCaseIncidentOperatorPacketZipVerificationAuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = SupportCaseIncidentOperatorPacketZipVerificationAuditRecord.model_validate_json(line)
        except ValueError:
            continue
        if safe_reviewer and record.reviewer != safe_reviewer:
            continue
        records.append(record)
    records.sort(key=lambda item: item.recorded_at, reverse=True)
    return SupportCaseIncidentOperatorPacketZipVerificationAuditList(records=records[: max(1, min(limit, 100))])


def render_support_case_incident_operator_packet_zip_verification_audit_markdown(
    audit: SupportCaseIncidentOperatorPacketZipVerificationAuditList,
) -> str:
    lines = [
        "# Support Case Incident Operator Packet Zip Verification Audit",
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


def render_support_case_incident_operator_packet_zip_verification_audit_csv(
    audit: SupportCaseIncidentOperatorPacketZipVerificationAuditList,
) -> str:
    rows = [
        "audit_id,recorded_at,reviewer,ready,checksum_sha256,size_bytes,file_count,blocker_count,warning_count"
    ]
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


def build_support_case_incident_final_handoff_checklist(
    *,
    artifact_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentFinalHandoffChecklist:
    artifacts = list_support_case_incident_operator_packet_artifacts(artifact_root=artifact_root, limit=1)
    latest_artifact = artifacts[0] if artifacts else None
    missing_gates: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    zip_manifest: SupportCaseIncidentOperatorPacketZipManifest | None = None
    zip_verification: SupportCaseIncidentOperatorPacketZipVerification | None = None

    if latest_artifact is None:
        missing_gates.append("support case incident operator packet artifact")
    else:
        if latest_artifact.file_count < len(SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES):
            missing_gates.append("support case incident operator packet required files")
        if not latest_artifact.ready:
            missing_gates.append("support case incident operator packet artifact ready state")

    if latest_artifact is not None:
        try:
            zip_manifest, zip_bytes = build_support_case_incident_operator_packet_zip_bundle(
                artifact_root=artifact_root,
            )
            zip_verification = verify_support_case_incident_operator_packet_zip_bundle(
                zip_bytes,
                expected_checksum_sha256=zip_manifest.checksum_sha256,
            )
        except ValueError as exc:
            blockers.append(str(exc))

    if zip_manifest is None or zip_manifest.file_count < len(SUPPORT_CASE_INCIDENT_OPERATOR_PACKET_FILES):
        missing_gates.append("support case incident operator packet zip bundle")
    if zip_verification is None or not zip_verification.ready:
        missing_gates.append("support case incident operator packet zip verification")

    audit = list_support_case_incident_operator_packet_zip_verification_audits(
        audit_root=audit_root,
        limit=1,
    )
    latest_audit = audit.records[0] if audit.records else None
    if latest_audit is None:
        missing_gates.append("support case incident operator packet zip verification audit")
    elif not latest_audit.ready:
        missing_gates.append("latest support case incident operator packet zip verification audit ready state")

    if zip_verification:
        blockers.extend(zip_verification.blockers)
        warnings.extend(zip_verification.warnings)
    if latest_audit:
        blockers.extend(latest_audit.blockers)
        warnings.extend(latest_audit.warnings)

    ready = not missing_gates and not blockers
    if blockers:
        maturity_label = "blocked"
    elif missing_gates or warnings:
        maturity_label = "review_needed"
    else:
        maturity_label = "ready"
    next_actions = (
        [
            "Resolve missing final handoff gates before closing the support case incident.",
            "Re-run operator packet zip verification and record a fresh metadata-only audit.",
        ]
        if not ready
        else [
            "Attach final checklist, operator packet artifact manifest, zip checksum, and audit export to the support case.",
            "Close the incident only after a reviewer confirms no raw keys or private payloads were requested.",
        ]
    )
    return SupportCaseIncidentFinalHandoffChecklist(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label=maturity_label,
        latest_operator_artifact_id=latest_artifact.artifact_id if latest_artifact else None,
        operator_artifact_file_count=latest_artifact.file_count if latest_artifact else 0,
        operator_zip_checksum_sha256=zip_manifest.checksum_sha256 if zip_manifest else None,
        operator_zip_file_count=zip_manifest.file_count if zip_manifest else 0,
        operator_zip_verification_ready=zip_verification.ready if zip_verification else False,
        operator_zip_audit_count=len(audit.records),
        latest_operator_zip_audit_id=latest_audit.audit_id if latest_audit else None,
        checklist_items=[
            "Support case incident operator packet metadata artifacts are written and indexed.",
            "Support case incident operator packet zip is generated from whitelist files.",
            "Support case incident operator packet zip is verified without executing content.",
            "Support case incident operator packet zip verification audit is recorded as metadata only.",
            "Final support closure evidence is ready for handoff.",
        ],
        missing_gates=_unique(missing_gates),
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        next_actions=next_actions,
        evidence_refs=[
            "/api/v1/player/support-case/incident-operator-packet/artifacts",
            "/api/v1/player/support-case/incident-operator-packet/artifacts/bundle",
            "/api/v1/player/support-case/incident-operator-packet/artifacts/bundle/verify",
            "/api/v1/player/support-case/incident-operator-packet/artifacts/bundle/verification-audit",
        ],
    )


def render_support_case_incident_final_handoff_checklist_markdown(
    checklist: SupportCaseIncidentFinalHandoffChecklist,
) -> str:
    lines = [
        "# Support Case Incident Final Handoff Checklist",
        "",
        f"- Ready: {checklist.ready}",
        f"- Maturity: {checklist.maturity_label}",
        f"- Latest operator artifact: {checklist.latest_operator_artifact_id or 'None'}",
        f"- Operator artifact files: {checklist.operator_artifact_file_count}",
        f"- Operator zip files: {checklist.operator_zip_file_count}",
        f"- Operator zip checksum: {checklist.operator_zip_checksum_sha256 or 'None'}",
        f"- Operator zip verification ready: {checklist.operator_zip_verification_ready}",
        f"- Operator zip audit records: {checklist.operator_zip_audit_count}",
        f"- Boundary: {checklist.boundary}",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist.checklist_items)
    lines.extend(["", "## Missing Gates"])
    lines.extend(f"- {item}" for item in checklist.missing_gates) if checklist.missing_gates else lines.append("- None")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in checklist.blockers) if checklist.blockers else lines.append("- None")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in checklist.warnings) if checklist.warnings else lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in checklist.next_actions)
    return "\n".join(lines) + "\n"


def render_support_case_incident_final_handoff_checklist_csv(
    checklist: SupportCaseIncidentFinalHandoffChecklist,
) -> str:
    rows = [
        "ready,maturity_label,latest_operator_artifact_id,operator_artifact_file_count,operator_zip_file_count,operator_zip_verification_ready,operator_zip_audit_count,missing_gate_count,blocker_count,warning_count",
        ",".join(
            [
                _csv(str(checklist.ready)),
                _csv(checklist.maturity_label),
                _csv(checklist.latest_operator_artifact_id or ""),
                _csv(str(checklist.operator_artifact_file_count)),
                _csv(str(checklist.operator_zip_file_count)),
                _csv(str(checklist.operator_zip_verification_ready)),
                _csv(str(checklist.operator_zip_audit_count)),
                _csv(str(len(checklist.missing_gates))),
                _csv(str(len(checklist.blockers))),
                _csv(str(len(checklist.warnings))),
            ]
        ),
    ]
    rows.extend(f"checklist_item,{_csv(item)}" for item in checklist.checklist_items)
    rows.extend(f"missing_gate,{_csv(item)}" for item in checklist.missing_gates)
    rows.extend(f"blocker,{_csv(item)}" for item in checklist.blockers)
    rows.extend(f"warning,{_csv(item)}" for item in checklist.warnings)
    rows.extend(f"next_action,{_csv(item)}" for item in checklist.next_actions)
    return "\n".join(rows) + "\n"


def write_support_case_incident_final_handoff_packet_artifacts(
    checklist: SupportCaseIncidentFinalHandoffChecklist,
    *,
    artifact_root: Path | None = None,
) -> SupportCaseIncidentFinalHandoffPacketManifest:
    root = artifact_root or SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_ROOT
    generated_at = datetime.now(timezone.utc)
    packet_id = f"support-case-incident-final-handoff-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    packet_dir = root / packet_id
    packet_dir.mkdir(parents=True, exist_ok=False)
    operator_artifacts = list_support_case_incident_operator_packet_artifacts(limit=1)
    operator_artifact = operator_artifacts[0] if operator_artifacts else None
    operator_audit = list_support_case_incident_operator_packet_zip_verification_audits(limit=20)
    contents = {
        "checklist.json": checklist.model_dump_json(indent=2),
        "checklist.md": render_support_case_incident_final_handoff_checklist_markdown(checklist),
        "checklist.csv": render_support_case_incident_final_handoff_checklist_csv(checklist),
        "operator_artifact_manifest.json": (
            operator_artifact.model_dump_json(indent=2) if operator_artifact else json.dumps({}, indent=2)
        ),
        "operator_zip_verification_audit.csv": render_support_case_incident_operator_packet_zip_verification_audit_csv(
            operator_audit
        ),
    }
    files: list[SupportCaseIncidentPacketFile] = []
    for file_name, text in contents.items():
        file_path = packet_dir / file_name
        file_path.write_text(text, encoding="utf-8")
        files.append(_packet_file_entry(root, file_path, file_name, _media_type(file_name), text))
    manifest_payload = {
        "schema_version": "gw2radar.support_case_incident_final_handoff_packet_manifest.v1",
        "packet_id": packet_id,
        "generated_at": generated_at.isoformat(),
        "source_checklist_schema_version": checklist.schema_version,
        "ready": checklist.ready,
        "maturity_label": checklist.maturity_label,
        "files": [file.model_dump(mode="json") for file in files],
        "contains_raw_key": False,
        "contains_raw_debug_bundle": False,
        "contains_private_source_payload": False,
        "contains_zip_bytes": False,
        "contains_executable_content": False,
        "allowed_files": sorted(SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES),
        "boundary": "Support case incident final handoff packet artifacts store metadata only.",
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path = packet_dir / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
    files.append(manifest_file)
    return SupportCaseIncidentFinalHandoffPacketManifest(
        packet_id=packet_id,
        artifact_root=root.as_posix(),
        generated_at=generated_at,
        source_checklist_schema_version=checklist.schema_version,
        ready=checklist.ready,
        maturity_label=checklist.maturity_label,
        file_count=len(files),
        files=files,
        manifest_path=manifest_file.relative_path,
        checksum_sha256=_packet_checksum(files),
    )


def list_support_case_incident_final_handoff_packets(
    *,
    artifact_root: Path | None = None,
    limit: int = 20,
) -> list[SupportCaseIncidentFinalHandoffPacketManifest]:
    root = artifact_root or SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_ROOT
    if not root.exists():
        return []
    packets: list[SupportCaseIncidentFinalHandoffPacketManifest] = []
    for packet_dir in sorted([path for path in root.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)[: max(1, min(limit, 100))]:
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
            if file.get("file_name") in SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES
        ]
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_file = _packet_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
        if not any(file.file_name == "manifest.json" for file in files):
            files.append(manifest_file)
        packets.append(
            SupportCaseIncidentFinalHandoffPacketManifest(
                packet_id=packet_dir.name,
                artifact_root=root.as_posix(),
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
                source_checklist_schema_version=str(
                    manifest.get("source_checklist_schema_version") or "unknown"
                ),
                ready=bool(manifest.get("ready")),
                maturity_label=str(manifest.get("maturity_label") or "unknown"),
                file_count=len(files),
                files=files,
                manifest_path=manifest_file.relative_path,
                checksum_sha256=_packet_checksum(files),
            )
        )
    return packets


def resolve_support_case_incident_final_handoff_packet_path(
    packet_id: str,
    file_name: str,
    *,
    artifact_root: Path | None = None,
) -> Path | None:
    if "/" in packet_id or "\\" in packet_id or ".." in packet_id:
        return None
    if file_name not in SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES:
        return None
    root = artifact_root or SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_ROOT
    candidate = root / packet_id / file_name
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_support_case_incident_final_handoff_packet_zip_bundle(
    *,
    artifact_root: Path | None = None,
) -> tuple[SupportCaseIncidentFinalHandoffPacketZipManifest, bytes]:
    packets = list_support_case_incident_final_handoff_packets(artifact_root=artifact_root, limit=1)
    if not packets:
        raise ValueError("No support case incident final handoff packet artifacts are available to bundle.")
    packet = packets[0]
    source_files: list[tuple[str, Path, str]] = []
    for file in packet.files:
        path = resolve_support_case_incident_final_handoff_packet_path(
            packet.packet_id,
            file.file_name,
            artifact_root=artifact_root,
        )
        if path is not None:
            source_files.append((file.file_name, path, file.media_type))
    included_files: list[SupportCaseIncidentPacketFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, path, media_type in sorted(source_files, key=lambda item: item[0]):
            if file_name not in SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES:
                continue
            content = path.read_bytes()
            archive_path = f"support_case_incident_final_handoff_packet/{file_name}"
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
        SupportCaseIncidentFinalHandoffPacketZipManifest(
            bundle_id=f"support-case-incident-final-handoff-packet-zip:{checksum[:16]}",
            source_packet_id=packet.packet_id,
            generated_at=datetime.now(timezone.utc),
            filename=f"{packet.packet_id}_final_handoff_packet.zip",
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
        ),
        bundle_bytes,
    )


def verify_support_case_incident_final_handoff_packet_zip_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> SupportCaseIncidentFinalHandoffPacketZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    allowed_names = {
        f"support_case_incident_final_handoff_packet/{file_name}"
        for file_name in SUPPORT_CASE_INCIDENT_FINAL_HANDOFF_PACKET_FILES
    }
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("support case incident final handoff packet checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    blockers.append(f"support case incident final handoff packet contains unsafe path: {name}")
            extra_names = sorted(set(names) - allowed_names)
            missing_names = sorted(allowed_names - set(names))
            if extra_names:
                blockers.append(
                    "support case incident final handoff packet contains non-whitelisted files: "
                    + ", ".join(extra_names)
                )
            if missing_names:
                blockers.append(
                    "support case incident final handoff packet is missing required files: "
                    + ", ".join(missing_names)
                )
            for name in names:
                lowered = archive.read(name).lower()
                if b"secret-key" in lowered:
                    blockers.append(f"support case incident final handoff packet file contains prohibited secret marker: {name}")
                if name.endswith(".zip"):
                    blockers.append(f"support case incident final handoff packet contains nested zip content: {name}")
    except Exception as exc:
        blockers.append(f"support case incident final handoff packet zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("support case incident final handoff packet zip is larger than the MVP verification target of 5 MB")
    return SupportCaseIncidentFinalHandoffPacketZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def record_support_case_incident_final_handoff_packet_zip_verification_audit(
    request: SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRequest,
    *,
    bundle_bytes: bytes | None = None,
    artifact_root: Path | None = None,
    audit_root: Path | None = None,
) -> SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        manifest, bundle_bytes = build_support_case_incident_final_handoff_packet_zip_bundle(
            artifact_root=artifact_root
        )
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_support_case_incident_final_handoff_packet_zip_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    recorded_at = datetime.now(timezone.utc)
    record = SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord(
        audit_id=f"support-case-incident-final-handoff-packet-zip-audit-{recorded_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        recorded_at=recorded_at,
        reviewer=_safe_text(request.reviewer or "support", max_length=80),
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
        or ["Support case incident final handoff packet zip verification audit recorded."],
    )
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    with (root / "final_handoff_packet_zip_verification_audit.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_support_case_incident_final_handoff_packet_zip_verification_audits(
    *,
    audit_root: Path | None = None,
    reviewer: str | None = None,
    limit: int = 20,
) -> SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList:
    root = audit_root or SUPPORT_CASE_INCIDENT_PACKET_AUDIT_ROOT
    path = root / "final_handoff_packet_zip_verification_audit.jsonl"
    if not path.exists():
        return SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList(records=[])
    safe_reviewer = _safe_text(reviewer, max_length=80) if reviewer else None
    records: list[SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = SupportCaseIncidentFinalHandoffPacketZipVerificationAuditRecord.model_validate_json(line)
        except ValueError:
            continue
        if safe_reviewer and record.reviewer != safe_reviewer:
            continue
        records.append(record)
    records.sort(key=lambda item: item.recorded_at, reverse=True)
    return SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList(
        records=records[: max(1, min(limit, 100))]
    )


def render_support_case_incident_final_handoff_packet_zip_verification_audit_markdown(
    audit: SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList,
) -> str:
    lines = [
        "# Support Case Incident Final Handoff Packet Zip Verification Audit",
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


def render_support_case_incident_final_handoff_packet_zip_verification_audit_csv(
    audit: SupportCaseIncidentFinalHandoffPacketZipVerificationAuditList,
) -> str:
    rows = [
        "audit_id,recorded_at,reviewer,ready,checksum_sha256,size_bytes,file_count,blocker_count,warning_count"
    ]
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


def _render_operator_dashboard_summary_markdown(packet: SupportCaseIncidentOperatorPacket) -> str:
    dashboard = packet.dashboard_summary
    lines = [
        "# Support Case Incident Dashboard Summary",
        "",
        f"- Schema: {dashboard.get('schema_version') or 'unknown'}",
        f"- Ready: {dashboard.get('ready')}",
        f"- Maturity: {dashboard.get('maturity_label') or 'unknown'}",
        f"- Support status: {dashboard.get('support_status') or 'unknown'}",
        f"- Gateway notes: {dashboard.get('gateway_note_count') or 0}",
        f"- Support audits: {dashboard.get('support_audit_count') or 0}",
        f"- Handoff ready: {dashboard.get('handoff_ready')}",
        "",
        "## Boundary",
        "",
        "- Dashboard summary is metadata-only and excludes raw API keys, raw debug bundles, and private payloads.",
    ]
    return "\n".join(lines) + "\n"


def _render_operator_audit_summary_csv(packet: SupportCaseIncidentOperatorPacket) -> str:
    audit = packet.audit_summary
    rows = [
        "record_count,latest_audit_id,latest_reviewer,latest_ready,latest_checksum_sha256",
        ",".join(
            [
                _csv(str(audit.get("record_count") or 0)),
                _csv(str(audit.get("latest_audit_id") or "")),
                _csv(str(audit.get("latest_reviewer") or "")),
                _csv(str(audit.get("latest_ready") or "")),
                _csv(str(audit.get("latest_checksum_sha256") or "")),
            ]
        ),
    ]
    return "\n".join(rows) + "\n"


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


def _safe_text(value: str | None, *, max_length: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    text = " ".join(text.split())
    return text[:max_length]


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


def _verify_support_case_incident_operator_packet_payloads(
    archive: ZipFile,
    names: list[str],
    blockers: list[str],
) -> None:
    prefix = "support_case_incident_operator_packet/"
    manifest_name = f"{prefix}manifest.json"
    operator_json_name = f"{prefix}operator_packet.json"
    operator_md_name = f"{prefix}operator_packet.md"
    checklist_md_name = f"{prefix}checklist.md"
    audit_csv_name = f"{prefix}verification_audit.csv"
    if manifest_name in names:
        try:
            manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
            if manifest.get("schema_version") != "gw2radar.support_case_incident_operator_packet_manifest.v1":
                blockers.append("support case incident operator packet manifest schema mismatch")
            for flag in [
                "contains_raw_key",
                "contains_raw_debug_bundle",
                "contains_private_source_payload",
                "contains_zip_bytes",
                "contains_executable_content",
            ]:
                if manifest.get(flag) is not False:
                    blockers.append(f"support case incident operator packet manifest has unsafe flag: {flag}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            blockers.append(f"support case incident operator packet manifest validation failed: {exc}")
    if operator_json_name in names:
        try:
            packet = SupportCaseIncidentOperatorPacket.model_validate_json(
                archive.read(operator_json_name).decode("utf-8")
            )
            if packet.schema_version != "gw2radar.support_case_incident_operator_packet.v1":
                blockers.append("support case incident operator packet schema mismatch")
        except (UnicodeDecodeError, ValueError) as exc:
            blockers.append(f"support case incident operator packet JSON validation failed: {exc}")
    if operator_md_name in names:
        try:
            markdown = archive.read(operator_md_name).decode("utf-8")
            if "Support Case Incident Operator Packet" not in markdown:
                blockers.append("support case incident operator packet Markdown title is missing")
        except UnicodeDecodeError as exc:
            blockers.append(f"support case incident operator packet Markdown is not UTF-8: {exc}")
    if checklist_md_name in names:
        try:
            markdown = archive.read(checklist_md_name).decode("utf-8")
            if "Support Case Incident Handoff Checklist" not in markdown:
                blockers.append("support case incident handoff checklist Markdown title is missing")
        except UnicodeDecodeError as exc:
            blockers.append(f"support case incident handoff checklist Markdown is not UTF-8: {exc}")
    if audit_csv_name in names:
        try:
            csv_text = archive.read(audit_csv_name).decode("utf-8")
            if "record_count,latest_audit_id,latest_reviewer" not in csv_text:
                blockers.append("support case incident operator packet audit CSV header mismatch")
        except UnicodeDecodeError as exc:
            blockers.append(f"support case incident operator packet audit CSV is not UTF-8: {exc}")
