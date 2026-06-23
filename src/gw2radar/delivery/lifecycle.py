import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, Field


class DeliveryPacketFile(BaseModel):
    file_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    checksum_sha256: str


class DeliveryPacketZipManifest(BaseModel):
    schema_version: str = "gw2radar.delivery_packet_zip_manifest.v1"
    bundle_id: str
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    item_count: int
    file_count: int
    included_files: list[DeliveryPacketFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str


class DeliveryPacketZipVerification(BaseModel):
    schema_version: str = "gw2radar.delivery_packet_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str


class DeliveryLifecycleReadiness(BaseModel):
    schema_version: str = "gw2radar.delivery_lifecycle_readiness.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Delivery lifecycle readiness is metadata-only; it does not store secrets, execute files, "
        "publish artifacts, or certify live external state."
    )


@dataclass(frozen=True)
class DeliverySourceFile:
    item_id: str
    path: Path
    archive_path: str
    media_type: str


@dataclass(frozen=True)
class DeliveryZipPolicy:
    label: str
    root_prefix: str
    allowed_file_names_for_item: Callable[[str], set[str]]
    required_file_names_for_item: Callable[[str], set[str]]
    validate_item_files: Callable[[str, set[str]], list[str]] | None = None
    flat_root: bool = False
    flat_item_id: str = "root"
    prohibited_markers: tuple[bytes, ...] = (b"secret-key", b"private_source_payload")
    prohibited_marker_label: str = "private marker"
    max_size_bytes: int = 5_000_000
    boundary: str = (
        "Delivery packet zip verification reads bytes only and does not execute, publish, or store uploaded content."
    )


def build_delivery_packet_zip_bundle(
    source_files: list[DeliverySourceFile],
    *,
    item_count: int,
    bundle_id_prefix: str,
    filename_prefix: str,
    boundary: str,
) -> tuple[DeliveryPacketZipManifest, bytes]:
    if not source_files:
        raise ValueError("No delivery source files are available to bundle.")
    included_files: list[DeliveryPacketFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for source_file in sorted(source_files, key=lambda item: item.archive_path):
            if not source_file.path.exists() or not source_file.path.is_file():
                continue
            content = source_file.path.read_bytes()
            info = ZipInfo(source_file.archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
            included_files.append(
                DeliveryPacketFile(
                    file_name=source_file.path.name,
                    relative_path=source_file.archive_path,
                    media_type=source_file.media_type,
                    size_bytes=len(content),
                    checksum_sha256=hashlib.sha256(content).hexdigest(),
                )
            )
    if not included_files:
        raise ValueError("No existing delivery source files were available to bundle.")
    bundle_bytes = buffer.getvalue()
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    return (
        DeliveryPacketZipManifest(
            bundle_id=f"{bundle_id_prefix}:{checksum[:16]}",
            generated_at=datetime.now(timezone.utc),
            filename=f"{filename_prefix}_{checksum[:12]}.zip",
            item_count=item_count,
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
            boundary=boundary,
        ),
        bundle_bytes,
    )


def verify_delivery_packet_zip_bundle(
    bundle_bytes: bytes,
    *,
    policy: DeliveryZipPolicy,
    expected_checksum_sha256: str | None = None,
) -> DeliveryPacketZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append(f"{policy.label} checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            if not names:
                blockers.append(f"{policy.label} zip contains no files")
            item_files: dict[str, set[str]] = {}
            for name in names:
                path = Path(name)
                parts = path.parts
                if path.is_absolute() or ".." in parts:
                    blockers.append(f"{policy.label} contains unsafe path: {name}")
                    continue
                expected_parts = 2 if policy.flat_root else 3
                if len(parts) != expected_parts or parts[0] != policy.root_prefix:
                    blockers.append(f"{policy.label} contains non-whitelisted path: {name}")
                    continue
                item_id = policy.flat_item_id if policy.flat_root else parts[1]
                file_name = parts[1] if policy.flat_root else parts[2]
                if file_name not in policy.allowed_file_names_for_item(item_id):
                    blockers.append(f"{policy.label} contains non-whitelisted file: {name}")
                item_files.setdefault(item_id, set()).add(file_name)
            for item_id, files in item_files.items():
                for required_file_name in policy.required_file_names_for_item(item_id):
                    if required_file_name not in files:
                        blockers.append(f"{policy.label} item is missing {required_file_name}: {item_id}")
                if policy.validate_item_files is not None:
                    blockers.extend(policy.validate_item_files(item_id, files))
            for name in names:
                if name.endswith(".zip"):
                    blockers.append(f"{policy.label} contains nested zip content: {name}")
                lowered = archive.read(name).lower()
                for marker in policy.prohibited_markers:
                    if marker.lower() in lowered:
                        blockers.append(f"{policy.label} file contains prohibited {policy.prohibited_marker_label}: {name}")
                        break
    except Exception as exc:
        blockers.append(f"{policy.label} zip could not be read: {exc}")
    if len(bundle_bytes) > policy.max_size_bytes:
        warnings.append(f"{policy.label} zip is larger than the verification target of {policy.max_size_bytes} bytes")
    return DeliveryPacketZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
        boundary=policy.boundary,
    )


def build_delivery_lifecycle_readiness(
    *,
    checklist_items: list[str],
    missing_gates: list[str],
    blockers: list[str],
    warnings: list[str],
    ready_next_actions: list[str],
    evidence_refs: list[str],
) -> DeliveryLifecycleReadiness:
    next_actions = missing_gates if missing_gates else ready_next_actions
    ready = not missing_gates and not blockers
    return DeliveryLifecycleReadiness(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label="ready" if ready else "needs_review",
        checklist_items=checklist_items,
        missing_gates=missing_gates,
        blockers=blockers,
        warnings=warnings,
        next_actions=next_actions,
        evidence_refs=evidence_refs,
    )
