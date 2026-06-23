from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.ops.final_closeout import (
    build_final_closeout_dashboard,
    build_stop_line_review,
    render_final_closeout_dashboard_csv,
    render_final_closeout_dashboard_markdown,
    render_stop_line_review_csv,
    render_stop_line_review_markdown,
)


def test_final_closeout_dashboard_marks_project_ready_for_trial() -> None:
    dashboard = build_final_closeout_dashboard()

    assert dashboard.schema_version == "gw2radar.final_closeout_dashboard.v1"
    assert dashboard.status == "ready_for_user_trial"
    assert dashboard.closeout_score == 100.0
    assert dashboard.stop_line_count == 0
    assert "Operator Release Packet Handoff" in dashboard.completed_tracks
    assert "/player" in dashboard.trial_entrypoints
    assert "privacy-safe account debug bundle review" in dashboard.defect_intake_channels
    assert dashboard.stop_line_review.decision == "stop_new_phase_expansion"
    assert dashboard.stop_line_review.no_more_horizontal_copy is True


def test_final_closeout_dashboard_exports_markdown_csv_and_stop_line_review() -> None:
    dashboard = build_final_closeout_dashboard()
    review = build_stop_line_review()
    markdown = render_final_closeout_dashboard_markdown(dashboard)
    csv = render_final_closeout_dashboard_csv(dashboard)
    review_markdown = render_stop_line_review_markdown(review)
    review_csv = render_stop_line_review_csv(review)

    assert "# Final Closeout Dashboard" in markdown
    assert "## Stop-Line Review" in markdown
    assert "area_id,status,stop_line,evidence" in csv
    assert "work_mode_stop_line,ready,false" in csv
    assert "# Stop-Line Review" in review_markdown
    assert "real_user_trial_and_defect_fix" in review_markdown
    assert "field,value" in review_csv


def test_final_closeout_dashboard_api_contract() -> None:
    client = TestClient(app)

    dashboard = client.get("/api/v1/ops/final-closeout-dashboard")
    dashboard_markdown = client.get("/api/v1/ops/final-closeout-dashboard?format=markdown")
    dashboard_csv = client.get("/api/v1/ops/final-closeout-dashboard?format=csv")
    stop_line = client.get("/api/v1/ops/stop-line-review")
    stop_line_markdown = client.get("/api/v1/ops/stop-line-review?format=markdown")

    assert dashboard.status_code == 200
    payload = dashboard.json()["data"]["final_closeout_dashboard"]
    assert payload["status"] == "ready_for_user_trial"
    assert payload["stop_line_count"] == 0
    assert payload["stop_line_review"]["no_more_horizontal_copy"] is True
    assert dashboard_markdown.status_code == 200
    assert dashboard_markdown.headers["content-type"].startswith("text/markdown")
    assert "# Final Closeout Dashboard" in dashboard_markdown.text
    assert dashboard_csv.status_code == 200
    assert dashboard_csv.headers["content-type"].startswith("text/csv")
    assert stop_line.status_code == 200
    assert stop_line.json()["data"]["stop_line_review"]["decision"] == "stop_new_phase_expansion"
    assert stop_line_markdown.status_code == 200
    assert "# Stop-Line Review" in stop_line_markdown.text
