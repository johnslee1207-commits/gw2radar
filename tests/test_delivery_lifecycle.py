from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4
from zipfile import ZipFile

from gw2radar.delivery.lifecycle import (
    DeliverySourceFile,
    DeliveryZipPolicy,
    build_delivery_lifecycle_readiness,
    build_delivery_packet_zip_bundle,
    verify_delivery_packet_zip_bundle,
)


def test_delivery_packet_zip_bundle_verification_and_readiness() -> None:
    temp_dir = Path(".test_tmp") / f"delivery-lifecycle-{uuid4().hex}"
    try:
        item_dir = temp_dir / "item-a"
        item_dir.mkdir(parents=True)
        report_path = item_dir / "item-a.md"
        manifest_path = item_dir / "manifest.json"
        report_path.write_text("# Report\n", encoding="utf-8")
        manifest_path.write_text('{"schema_version":"example.v1"}\n', encoding="utf-8")

        policy = DeliveryZipPolicy(
            label="example packet",
            root_prefix="example_packet",
            allowed_file_names_for_item=lambda item_id: {"manifest.json", f"{item_id}.md"},
            required_file_names_for_item=lambda _item_id: {"manifest.json"},
            validate_item_files=lambda item_id, files: []
            if f"{item_id}.md" in files
            else [f"example packet item is missing a report file: {item_id}"],
        )
        manifest, bundle_bytes = build_delivery_packet_zip_bundle(
            [
                DeliverySourceFile(
                    item_id="item-a",
                    path=report_path,
                    archive_path="example_packet/item-a/item-a.md",
                    media_type="text/markdown",
                ),
                DeliverySourceFile(
                    item_id="item-a",
                    path=manifest_path,
                    archive_path="example_packet/item-a/manifest.json",
                    media_type="application/json",
                ),
            ],
            item_count=1,
            bundle_id_prefix="example-packet",
            filename_prefix="example_packet",
            boundary="Example packet excludes secrets and executable content.",
        )

        assert manifest.schema_version == "gw2radar.delivery_packet_zip_manifest.v1"
        assert manifest.item_count == 1
        assert manifest.file_count == 2
        assert len(manifest.checksum_sha256) == 64
        verification = verify_delivery_packet_zip_bundle(
            bundle_bytes,
            policy=policy,
            expected_checksum_sha256=manifest.checksum_sha256,
        )
        assert verification.schema_version == "gw2radar.delivery_packet_zip_verification.v1"
        assert verification.ready is True
        assert verification.file_count == 2

        readiness = build_delivery_lifecycle_readiness(
            checklist_items=["Files included: 2."],
            missing_gates=[],
            blockers=[],
            warnings=[],
            ready_next_actions=["Deliver manually after checksum review."],
            evidence_refs=[f"packet_checksum:{manifest.checksum_sha256}"],
        )
        assert readiness.ready is True
        assert readiness.maturity_label == "ready"
        assert readiness.next_actions == ["Deliver manually after checksum review."]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_delivery_packet_zip_verification_blocks_unsafe_files_and_private_markers() -> None:
    policy = DeliveryZipPolicy(
        label="example packet",
        root_prefix="example_packet",
        allowed_file_names_for_item=lambda item_id: {"manifest.json", f"{item_id}.md"},
        required_file_names_for_item=lambda _item_id: {"manifest.json"},
    )
    buffer = BytesIO()
    with ZipFile(buffer, mode="w") as archive:
        archive.writestr("example_packet/item-a/item-a.md", "secret-key")
        archive.writestr("example_packet/item-a/bad.exe", "bad")
        archive.writestr("other_root/item-a/manifest.json", "{}")

    verification = verify_delivery_packet_zip_bundle(buffer.getvalue(), policy=policy)

    assert verification.ready is False
    assert any("prohibited private marker" in blocker for blocker in verification.blockers)
    assert any("non-whitelisted file" in blocker for blocker in verification.blockers)
    assert any("non-whitelisted path" in blocker for blocker in verification.blockers)
    assert any("missing manifest.json" in blocker for blocker in verification.blockers)
