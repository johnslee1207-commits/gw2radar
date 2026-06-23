import shutil
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.config.settings import get_settings
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_productized_report_templates_generate_artifacts_and_preserve_boundaries() -> None:
    temp_dir = Path(".test_tmp") / f"productized-reports-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        templates = client.get("/api/v1/reports/productized/templates")
        assert templates.status_code == 200
        template_payload = templates.json()["data"]["templates"]
        assert {template["template_id"] for template in template_payload} == {
            "account_value_analysis",
            "legendary_gap_analysis",
            "build_readiness_advisor",
        }
        assert all("csv" in template["export_formats"] for template in template_payload)

        locked = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "account_value_analysis", "format": "markdown"},
        )
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "account_value_report")
            create_report_entitlement(session, "local-user", "legendary_planner_pro_report")
            create_report_entitlement(session, "local-user", "build_fit_report")

        account_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "account_value_analysis", "format": "markdown"},
        )
        legendary_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "legendary_gap_analysis", "format": "csv"},
        )
        build_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "build_readiness_advisor", "format": "html"},
        )

        assert account_report.status_code == 200
        assert legendary_report.status_code == 200
        assert build_report.status_code == 200
        account_manifest = account_report.json()["data"]["productized_report"]
        legendary_manifest = legendary_report.json()["data"]["productized_report"]
        build_manifest = build_report.json()["data"]["productized_report"]

        assert account_manifest["schema_version"] == "gw2radar.productized_report_artifact.v1"
        assert account_manifest["product_id"] == "account_value_report"
        assert account_manifest["format"] == "markdown"
        assert "Account Value Snapshot" in account_manifest["sections"]
        assert len(account_manifest["checksum_sha256"]) == 64
        assert legendary_manifest["format"] == "csv"
        assert "Do-Not-Sell List" in legendary_manifest["sections"]
        assert build_manifest["format"] == "html"
        assert "Transition Plan" in build_manifest["sections"]

        account_artifact = client.get(f"/api/v1/reports/artifacts/{Path(account_manifest['artifact_path']).name}")
        legendary_artifact = client.get(f"/api/v1/reports/artifacts/{Path(legendary_manifest['artifact_path']).name}")
        build_artifact = client.get(f"/api/v1/reports/artifacts/{Path(build_manifest['artifact_path']).name}")

        assert account_artifact.status_code == 200
        assert "# Account Value Analysis Report" in account_artifact.text
        assert "Account Value Snapshot" in account_artifact.text
        assert legendary_artifact.status_code == 200
        assert "row_type,entity_id,name,quantity,detail" in legendary_artifact.text
        assert build_artifact.status_code == 200
        assert "<!doctype html>" in build_artifact.text
        assert "Build Readiness And Gear Transition Report" in build_artifact.text

        combined = (
            str(account_manifest)
            + str(legendary_manifest)
            + str(build_manifest)
            + account_artifact.text
            + legendary_artifact.text
            + build_artifact.text
        ).lower()
        assert "secret-key" not in combined
        assert "private_source_payload" not in combined
        assert "manual player review" in account_manifest["manual_action_boundary"]

        zip_manifest = client.get("/api/v1/reports/productized/artifacts/bundle?format=manifest&limit=10")
        zip_bundle = client.get("/api/v1/reports/productized/artifacts/bundle?limit=10")
        zip_verify = client.post("/api/v1/reports/productized/artifacts/bundle/verify?limit=10")
        zip_audit_record = client.post(
            "/api/v1/reports/productized/artifacts/bundle/verification-audit",
            json={"reviewer": "report lead", "notes": ["Verified productized report packet before delivery."]},
        )
        zip_audit_list = client.get(
            "/api/v1/reports/productized/artifacts/bundle/verification-audit?reviewer=report%20lead&limit=10"
        )
        zip_audit_markdown = client.get(
            "/api/v1/reports/productized/artifacts/bundle/verification-audit?format=markdown"
        )
        zip_audit_csv = client.get(
            "/api/v1/reports/productized/artifacts/bundle/verification-audit?format=csv"
        )

        assert zip_manifest.status_code == 200
        zip_manifest_payload = zip_manifest.json()["data"]["productized_report_packet_zip_bundle"]
        assert zip_manifest_payload["schema_version"] == "gw2radar.productized_report_packet_zip_manifest.v1"
        assert zip_manifest_payload["artifact_count"] >= 3
        assert zip_manifest_payload["file_count"] >= 6
        assert len(zip_manifest_payload["checksum_sha256"]) == 64
        assert zip_bundle.status_code == 200
        assert zip_bundle.headers["x-checksum-sha256"] == zip_manifest_payload["checksum_sha256"]
        names = set(ZipFile(BytesIO(zip_bundle.content)).namelist())
        assert any(name.endswith("/manifest.json") for name in names)
        assert any(name.endswith(".md") for name in names)
        assert any(name.endswith(".csv") for name in names)
        assert any(name.endswith(".html") for name in names)
        assert all(name.startswith("productized_report_packet/") for name in names)

        assert zip_verify.status_code == 200
        verification = zip_verify.json()["data"]["productized_report_packet_zip_verification"]
        assert verification["schema_version"] == "gw2radar.productized_report_packet_zip_verification.v1"
        assert verification["ready"] is True
        assert verification["checksum_sha256"] == zip_manifest_payload["checksum_sha256"]

        tampered_buffer = BytesIO()
        with ZipFile(BytesIO(zip_bundle.content), mode="r") as source_archive:
            with ZipFile(tampered_buffer, mode="w") as tampered_archive:
                for name in source_archive.namelist():
                    tampered_archive.writestr(name, source_archive.read(name))
                tampered_archive.writestr("productized_report_packet/bad/secret.txt", "secret-key")
        tampered_verify = client.post(
            "/api/v1/reports/productized/artifacts/bundle/verify",
            content=tampered_buffer.getvalue(),
            headers={"Content-Type": "application/zip"},
        )
        tampered_audit = client.post(
            "/api/v1/reports/productized/artifacts/bundle/verification-audit/upload?reviewer=tamper%20report",
            content=tampered_buffer.getvalue(),
            headers={"Content-Type": "application/zip"},
        )
        assert tampered_verify.status_code == 200
        tampered_verification = tampered_verify.json()["data"]["productized_report_packet_zip_verification"]
        assert tampered_verification["ready"] is False
        assert "secret-key" not in str(tampered_verification).lower()

        assert zip_audit_record.status_code == 200
        audit_record = zip_audit_record.json()["data"]["productized_report_packet_zip_verification_audit_record"]
        assert audit_record["schema_version"] == "gw2radar.productized_report_packet_zip_verification_audit.v1"
        assert audit_record["reviewer"] == "report lead"
        assert audit_record["ready"] is True
        assert audit_record["checksum_sha256"] == zip_manifest_payload["checksum_sha256"]
        assert zip_audit_list.status_code == 200
        audit_list = zip_audit_list.json()["data"]["productized_report_packet_zip_verification_audit"]
        assert audit_list["schema_version"] == "gw2radar.productized_report_packet_zip_verification_audit_list.v1"
        assert audit_list["records"][0]["reviewer"] == "report lead"
        assert zip_audit_markdown.status_code == 200
        assert "# Productized Report Packet Zip Verification Audit" in zip_audit_markdown.text
        assert zip_audit_csv.status_code == 200
        assert "audit_id,recorded_at,reviewer,ready,checksum_sha256" in zip_audit_csv.text
        assert tampered_audit.status_code == 200
        tampered_record = tampered_audit.json()["data"]["productized_report_packet_zip_verification_audit_record"]
        assert tampered_record["ready"] is False
        assert tampered_record["blocker_count"] >= 1
        assert "secret-key" not in (
            str(audit_record)
            + str(audit_list)
            + zip_audit_markdown.text
            + zip_audit_csv.text
            + str(tampered_record)
        ).lower()
    finally:
        close_database()
        configure_database(get_settings().database_url)
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
