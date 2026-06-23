from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.ops.operator_release_packet import (
    PACKET_FILE_NAMES,
    build_operator_release_packet_bundle,
    build_operator_release_packet_summary,
    render_operator_release_packet_summary_csv,
    render_operator_release_packet_summary_markdown,
    verify_operator_release_packet_bundle,
    write_operator_release_packet_artifacts,
)


def test_operator_release_packet_summary_is_ready_and_metadata_only() -> None:
    summary = build_operator_release_packet_summary()
    markdown = render_operator_release_packet_summary_markdown(summary)
    csv = render_operator_release_packet_summary_csv(summary)

    assert summary.schema_version == "gw2radar.operator_release_packet_summary.v1"
    assert summary.status == "ready"
    assert summary.blocker_count == 0
    assert "manifest.json" in summary.packet_files
    assert "python harness/run_stage_gate.py release" in summary.required_commands
    assert "no raw secret or private payload export" in summary.safety_boundaries
    assert "# Operator Release Packet" in markdown
    assert "metric,value" in csv
    assert "secret-key" not in markdown.lower()


def test_operator_release_packet_artifacts_bundle_and_verification() -> None:
    output_root = Path(".test_tmp") / f"operator-release-packet-{uuid4().hex}"
    index = write_operator_release_packet_artifacts(output_root)
    manifest, bundle_bytes = build_operator_release_packet_bundle(output_root)
    verification = verify_operator_release_packet_bundle(bundle_bytes, manifest.checksum_sha256)

    assert index.ready is True
    assert index.file_count == len(PACKET_FILE_NAMES)
    assert (output_root / "manifest.json").exists()
    assert manifest.file_count == len(PACKET_FILE_NAMES)
    assert verification.ready is True
    assert verification.blockers == []
    with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
        assert set(archive.namelist()) == {f"operator_release_packet/{file_name}" for file_name in PACKET_FILE_NAMES}
    assert b"secret-key" not in bundle_bytes.lower()
    assert b"private_source_payload" not in bundle_bytes.lower()


def test_operator_release_packet_api_contract() -> None:
    client = TestClient(app)

    summary = client.get("/api/v1/ops/release-packet")
    markdown = client.get("/api/v1/ops/release-packet?format=markdown")
    artifacts = client.post("/api/v1/ops/release-packet/artifacts")
    manifest = client.get("/api/v1/ops/release-packet/artifacts/bundle?format=manifest")
    bundle = client.get("/api/v1/ops/release-packet/artifacts/bundle")
    verification = client.post("/api/v1/ops/release-packet/artifacts/bundle/verify")

    assert summary.status_code == 200
    assert summary.json()["data"]["operator_release_packet"]["status"] == "ready"
    assert markdown.status_code == 200
    assert "# Operator Release Packet" in markdown.text
    assert artifacts.status_code == 200
    assert artifacts.json()["data"]["operator_release_packet_artifacts"]["ready"] is True
    assert manifest.status_code == 200
    manifest_payload = manifest.json()["data"]["operator_release_packet_bundle"]
    assert manifest_payload["file_count"] == len(PACKET_FILE_NAMES)
    assert bundle.status_code == 200
    assert bundle.headers["content-type"] == "application/zip"
    assert bundle.headers["x-checksum-sha256"] == manifest_payload["checksum_sha256"]
    assert verification.status_code == 200
    assert verification.json()["data"]["operator_release_packet_bundle_verification"]["ready"] is True
