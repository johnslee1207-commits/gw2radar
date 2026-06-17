from pathlib import Path

from fastapi.testclient import TestClient

from gw2radar.api.main import app


client = TestClient(app)


def test_player_ui_page_serves_player_workbench() -> None:
    response = client.get("/player")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "GW2Radar Player Dashboard" in response.text
    assert "Returner Diagnosis" in response.text
    assert "Legendary Planner Pro" in response.text
    assert "Build Fit Advisor" in response.text
    assert "Privacy & Safety" in response.text
    assert "No gameplay automation" in response.text


def test_player_ui_static_assets_are_served() -> None:
    css = client.get("/player-ui/styles.css")
    js = client.get("/player-ui/app.js")

    assert css.status_code == 200
    assert ".app-shell" in css.text
    assert ".dashboard-grid" in css.text
    assert js.status_code == 200
    assert "/api/v1/legendary/recompute" in js.text
    assert "/api/v1/builds/transition-plan" in js.text
    assert "/account/api-key" in js.text


def test_player_ui_docs_cover_required_flows() -> None:
    docs_root = Path("docs/ui")
    required = [
        "PLAYER_UI_GUIDE.md",
        "UI_INFORMATION_ARCHITECTURE.md",
        "RETURNER_DIAGNOSIS_UI_FLOW.md",
        "LEGENDARY_PLANNER_UI_FLOW.md",
        "BUILD_FIT_UI_FLOW.md",
        "REPORT_CENTER_UI_FLOW.md",
        "PRIVACY_SAFETY_UI_FLOW.md",
    ]

    combined = "\n".join((docs_root / name).read_text(encoding="utf-8") for name in required)

    assert "Returner Diagnosis" in combined
    assert "Legendary Planner Pro" in combined
    assert "Build Fit Advisor" in combined
    assert "No automatic trading" in combined
    assert "API key" in combined
