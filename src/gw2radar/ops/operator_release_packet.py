from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from gw2radar.delivery.lifecycle import (
    DeliveryPacketZipManifest,
    DeliveryPacketZipVerification,
    DeliverySourceFile,
    DeliveryZipPolicy,
    build_delivery_packet_zip_bundle,
    verify_delivery_packet_zip_bundle,
)
from gw2radar.ops.release_readiness import (
    ROOT,
    build_operational_hardening_readiness,
    render_operational_hardening_markdown,
)


DEFAULT_RELEASE_PACKET_ROOT = ROOT / "outputs" / "operator_release_packet" / "latest"


class OperatorReleasePacketEvidenceFile(BaseModel):
    source_path: str
    packet_file_name: str
    size_bytes: int
    checksum_sha256: str


class OperatorReleasePacketSummary(BaseModel):
    schema_version: str = "gw2radar.operator_release_packet_summary.v1"
    status: str
    readiness_score: float
    blocker_count: int
    evidence_file_count: int
    required_commands: list[str]
    deferred_tracks: list[str]
    safety_boundaries: list[str]
    packet_files: list[str]
    next_priority: str


class OperatorReleasePacketArtifactIndex(BaseModel):
    schema_version: str = "gw2radar.operator_release_packet_artifact_index.v1"
    packet_id: str
    output_root: str
    file_count: int
    evidence_files: list[OperatorReleasePacketEvidenceFile]
    manifest_file: str
    ready: bool
    boundary: str = (
        "Operator release packet artifacts are metadata-only copies of release evidence; "
        "they do not include raw secrets, private account payloads, executable content, or external publication."
    )


PACKET_FILE_NAMES = {
    "summary.md",
    "operational_hardening_readiness.md",
    "operational_hardening_readiness.json",
    "mvp_closure_readiness.json",
    "post_mvp_production_roadmap.json",
    "spec_registry_backlog.json",
    "partial_spec_reconciliation.json",
    "player_use_path_completeness_audit.md",
    "manifest.json",
}


def build_operator_release_packet_summary() -> OperatorReleasePacketSummary:
    readiness = build_operational_hardening_readiness()
    packet_files = sorted(PACKET_FILE_NAMES)
    return OperatorReleasePacketSummary(
        status=readiness.status,
        readiness_score=readiness.readiness_score,
        blocker_count=readiness.blocker_count,
        evidence_file_count=len(readiness.evidence_files),
        required_commands=readiness.required_commands,
        deferred_tracks=readiness.deferred_tracks,
        safety_boundaries=readiness.safety_boundaries,
        packet_files=packet_files,
        next_priority="Hand this packet to the operator only after stage, release, and GitNexus checks are current.",
    )


def render_operator_release_packet_summary_markdown(summary: OperatorReleasePacketSummary) -> str:
    lines = [
        "# Operator Release Packet",
        "",
        f"- Schema: {summary.schema_version}",
        f"- Status: {summary.status}",
        f"- Readiness score: {summary.readiness_score}",
        f"- Blocker count: {summary.blocker_count}",
        f"- Evidence file count: {summary.evidence_file_count}",
        "",
        "## Required Commands",
        "",
    ]
    for command in summary.required_commands:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Packet Files", ""])
    for file_name in summary.packet_files:
        lines.append(f"- {file_name}")
    lines.extend(["", "## Deferred Tracks", ""])
    for track in summary.deferred_tracks:
        lines.append(f"- {track}")
    lines.extend(["", "## Safety Boundaries", ""])
    for boundary in summary.safety_boundaries:
        lines.append(f"- {boundary}")
    lines.extend(["", "## Next Priority", "", summary.next_priority, ""])
    return "\n".join(lines)


def render_operator_release_packet_summary_csv(summary: OperatorReleasePacketSummary) -> str:
    rows = ["metric,value"]
    rows.append(f"status,{summary.status}")
    rows.append(f"readiness_score,{summary.readiness_score}")
    rows.append(f"blocker_count,{summary.blocker_count}")
    rows.append(f"evidence_file_count,{summary.evidence_file_count}")
    return "\n".join(rows) + "\n"


def write_operator_release_packet_artifacts(output_root: Path = DEFAULT_RELEASE_PACKET_ROOT) -> OperatorReleasePacketArtifactIndex:
    output_root.mkdir(parents=True, exist_ok=True)
    summary = build_operator_release_packet_summary()
    readiness = build_operational_hardening_readiness()
    planned_files: list[tuple[str, str | Path, str]] = [
        ("summary.md", render_operator_release_packet_summary_markdown(summary), "text"),
        ("operational_hardening_readiness.md", render_operational_hardening_markdown(readiness), "text"),
        ("operational_hardening_readiness.json", json.dumps(readiness.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", "text"),
        ("mvp_closure_readiness.json", ROOT / "docs" / "analysis" / "MVP_CLOSURE_READINESS.json", "copy"),
        ("post_mvp_production_roadmap.json", ROOT / "docs" / "analysis" / "POST_MVP_PRODUCTION_ROADMAP.json", "copy"),
        ("spec_registry_backlog.json", ROOT / "docs" / "analysis" / "SPEC_REGISTRY_BACKLOG.json", "copy"),
        ("partial_spec_reconciliation.json", ROOT / "docs" / "analysis" / "PARTIAL_SPEC_RECONCILIATION.json", "copy"),
        ("player_use_path_completeness_audit.md", ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md", "copy"),
    ]
    evidence_files: list[OperatorReleasePacketEvidenceFile] = []
    for file_name, source, mode in planned_files:
        destination = output_root / file_name
        if mode == "copy":
            source_path = Path(source)
            if not source_path.exists():
                raise FileNotFoundError(f"Missing release packet evidence file: {source_path}")
            shutil.copyfile(source_path, destination)
            source_label = str(source_path.relative_to(ROOT)).replace("\\", "/")
        else:
            destination.write_text(str(source), encoding="utf-8")
            source_label = "generated"
        content = destination.read_bytes()
        evidence_files.append(
            OperatorReleasePacketEvidenceFile(
                source_path=source_label,
                packet_file_name=file_name,
                size_bytes=len(content),
                checksum_sha256=hashlib.sha256(content).hexdigest(),
            )
        )
    index_without_manifest = OperatorReleasePacketArtifactIndex(
        packet_id=_packet_id(evidence_files),
        output_root=str(output_root),
        file_count=len(evidence_files) + 1,
        evidence_files=evidence_files,
        manifest_file="manifest.json",
        ready=summary.status == "ready" and summary.blocker_count == 0,
    )
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(index_without_manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_content = manifest_path.read_bytes()
    evidence_files.append(
        OperatorReleasePacketEvidenceFile(
            source_path="generated",
            packet_file_name="manifest.json",
            size_bytes=len(manifest_content),
            checksum_sha256=hashlib.sha256(manifest_content).hexdigest(),
        )
    )
    return OperatorReleasePacketArtifactIndex(
        packet_id=_packet_id(evidence_files),
        output_root=str(output_root),
        file_count=len(evidence_files),
        evidence_files=evidence_files,
        manifest_file="manifest.json",
        ready=summary.status == "ready" and summary.blocker_count == 0,
    )


def build_operator_release_packet_bundle(
    output_root: Path = DEFAULT_RELEASE_PACKET_ROOT,
) -> tuple[DeliveryPacketZipManifest, bytes]:
    if not output_root.exists() or not (output_root / "manifest.json").exists():
        write_operator_release_packet_artifacts(output_root)
    source_files = [
        DeliverySourceFile(
            item_id="operator_release_packet",
            path=output_root / file_name,
            archive_path=f"operator_release_packet/{file_name}",
            media_type=_media_type(file_name),
        )
        for file_name in sorted(PACKET_FILE_NAMES)
    ]
    return build_delivery_packet_zip_bundle(
        source_files,
        item_count=1,
        bundle_id_prefix="operator_release_packet",
        filename_prefix="operator_release_packet",
        boundary=(
            "Operator release packet zip is a read-only metadata handoff; it does not execute, publish, "
            "or certify live external state."
        ),
    )


def verify_operator_release_packet_bundle(
    bundle_bytes: bytes,
    expected_checksum_sha256: str | None = None,
) -> DeliveryPacketZipVerification:
    policy = DeliveryZipPolicy(
        label="operator release packet",
        root_prefix="operator_release_packet",
        flat_root=True,
        flat_item_id="operator_release_packet",
        allowed_file_names_for_item=lambda _item_id: PACKET_FILE_NAMES,
        required_file_names_for_item=lambda _item_id: PACKET_FILE_NAMES,
        prohibited_markers=(b"secret-key", b"private_source_payload", b"raw_api_key"),
        prohibited_marker_label="secret/private payload marker",
        max_size_bytes=5_000_000,
    )
    return verify_delivery_packet_zip_bundle(
        bundle_bytes,
        policy=policy,
        expected_checksum_sha256=expected_checksum_sha256,
    )


def _packet_id(evidence_files: list[OperatorReleasePacketEvidenceFile]) -> str:
    seed = "|".join(f"{item.packet_file_name}:{item.checksum_sha256}" for item in sorted(evidence_files, key=lambda item: item.packet_file_name))
    return f"operator_release_packet:{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:16]}"


def _media_type(file_name: str) -> str:
    if file_name.endswith(".json"):
        return "application/json"
    if file_name.endswith(".csv"):
        return "text/csv"
    return "text/markdown"
