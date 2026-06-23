from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import ReportExportJobModel, utc_now
from gw2radar.db.session import close_database, configure_database


def test_growth_retention_api_exposes_safe_weekly_history_share_and_mock_email() -> None:
    temp_dir = Path(".test_tmp") / f"growth-retention-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth_retention.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            now = utc_now()
            session.add(
                ReportExportJobModel(
                    job_id="job_growth_retention_sample",
                    user_id="local-user",
                    report_type="legendary_pro",
                    export_format="markdown",
                    status="succeeded",
                    artifact_path=str(temp_dir / "private" / "legendary_report.md"),
                    manifest_path=str(temp_dir / "private" / "manifest.json"),
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

        client = TestClient(app)
        history = client.get("/api/v1/growth/retention/report-history")
        weekly = client.post("/api/v1/growth/retention/weekly-report", json={"focus": "legendary_goals"})
        share = client.get("/api/v1/growth/retention/share-preview")
        email = client.post(
            "/api/v1/growth/retention/mock-email",
            json={"recipient_label": "account_owner", "include_share_preview": True},
        )
        status = client.get("/api/v1/growth/retention/status")

        assert history.status_code == 200
        assert weekly.status_code == 200
        assert share.status_code == 200
        assert email.status_code == 200
        assert status.status_code == 200

        history_entry = history.json()["data"]["history"][0]
        assert history_entry["artifact_name"] == "legendary_report.md"
        assert str(temp_dir) not in str(history_entry)

        weekly_report = weekly.json()["data"]["weekly_report"]
        weekly_text = weekly_report["summary_markdown"].lower()
        assert weekly_report["status"] == "ready"
        assert weekly_report["history_count"] == 1
        assert "manual player review only" in weekly_text
        assert "guaranteed profit" not in weekly_text
        assert "automatic trading instructions" not in weekly_text

        share_preview = share.json()["data"]["share_preview"]
        assert share_preview["public_url"] is None
        assert share_preview["contains_private_payload"] is False
        assert share_preview["contains_raw_secret"] is False
        assert "legendary_report.md" in share_preview["artifact_names"]

        delivery = email.json()["data"]["delivery"]
        assert delivery["provider"] == "mock_email"
        assert delivery["real_provider_used"] is False
        assert delivery["contains_private_payload"] is False
        assert delivery["preview"]["review_required"] is True

        retention = status.json()["data"]["retention"]
        assert retention["unsubscribe_available"] is True
        assert retention["private_data_delete_path"] == "/api/v1/security/private-data"
        assert retention["real_email_provider_locked"] is False
    finally:
        close_database()
