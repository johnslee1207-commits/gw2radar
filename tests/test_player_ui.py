from pathlib import Path

from fastapi.testclient import TestClient

from gw2radar.api.main import app


client = TestClient(app)


def test_player_ui_page_serves_player_workbench() -> None:
    response = client.get("/player")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "GW2Radar Player Dashboard" in response.text
    assert "Welcome to GW2Radar" in response.text
    assert "Returner Diagnosis" in response.text
    assert "Readiness score" in response.text
    assert "Legendary Planner Pro" in response.text
    assert "Build Fit Advisor" in response.text
    assert "Character snapshot" in response.text
    assert "Load character snapshots" in response.text
    assert "Upgrade evidence rules" in response.text
    assert "Preview upgrade pack" in response.text
    assert "Import disabled rules" in response.text
    assert "Enable selected rule" in response.text
    assert "Data Freshness" in response.text
    assert "Privacy & Safety" in response.text
    assert "No gameplay automation" in response.text
    assert "Workflow readiness" in response.text
    assert "No dashboard summary yet." in response.text
    assert "Delete all private data" in response.text
    assert "Check permissions" in response.text
    assert "Sync now" in response.text
    assert "Permission status not checked." in response.text
    assert "Today / this week" in response.text
    assert "Generate full report" in response.text
    assert "Mock returner checkout" in response.text
    assert "Refresh freshness to load recommendation-level source confidence." in response.text


def test_player_ui_static_assets_are_served() -> None:
    css = client.get("/player-ui/styles.css")
    js = client.get("/player-ui/app.js")

    assert css.status_code == 200
    assert ".app-shell" in css.text
    assert ".dashboard-grid" in css.text
    assert js.status_code == 200
    assert "/api/v1/legendary/recompute" in js.text
    assert "/api/v1/builds/transition-plan" in js.text
    assert "/api/v1/builds/character-snapshots" in js.text
    assert "/api/v1/kb/rule-packs/build_upgrade_effects" in js.text
    assert "/api/v1/kb/rules?domain=build&name_contains=Build%20upgrade" in js.text
    assert "enableBuildUpgradeRule" in js.text
    assert "confirmed_reviewed" in js.text
    assert "applyAccountGearSnapshot" in js.text
    assert "/account/api-key" in js.text
    assert "/account/api-key/permissions" in js.text
    assert "/api/v1/player/dashboard" in js.text
    assert "/api/v1/player/freshness-annotations" in js.text
    assert "/api/v1/legendary/goals/catalog" in js.text
    assert "/api/v1/legendary/actions" in js.text
    assert "/api/v1/returner/report" in js.text
    assert "plan_returner_once" in js.text
    assert "renderPermissionReport" in js.text
    assert "renderSyncProgress" in js.text
    assert "renderFreshnessAnnotations" in js.text
    assert "gw2radar.api_key_permissions.v1" in js.text
    assert "gw2radar.player.activeView" in js.text
    assert "summarizeResult" in js.text
    assert "artifactPath.split" in js.text
    assert "Import or select a build before running this action." in js.text
    assert "gw2radar.player.intent" in js.text
    assert "gw2radar.player.reportHistory" in js.text
    assert "/api/v1/security/private-data" in js.text
    assert "refreshFreshness" in js.text
    assert "/api/v1/returner/readiness" in js.text
    assert "updateReturnerScores" in js.text
    assert "rune/sigil/relic effect checks" in js.text
    assert "payload?.is_configured" in js.text
    assert "Sync now queues one account snapshot job" in js.text
    assert "/api/v1/account/sync/drain-one" in js.text


def test_player_ui_styles_cover_workflow_and_summaries() -> None:
    css = client.get("/player-ui/styles.css")

    assert css.status_code == 200
    assert ".workflow-rail" in css.text
    assert ".workflow-step.ready" in css.text
    assert ".result-summary" in css.text
    assert ".readiness-grid" in css.text
    assert ".score-card" in css.text
    assert ".gear-summary" in css.text
    assert ".rule-pack-status" in css.text
    assert ".compact-fields" in css.text
    assert ".goal-choice-grid" in css.text
    assert ".permission-grid" in css.text
    assert ".permission-status-grid" in css.text
    assert ".permission-status.ready" in css.text
    assert ".freshness-annotation-grid" in css.text
    assert ".sync-checklist span.blocked" in css.text
    assert ".sync-checklist" in css.text


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
        "PLAYER_UI_SEMANTIC_GRAPH_AUDIT.md",
    ]

    combined = "\n".join((docs_root / name).read_text(encoding="utf-8") for name in required)

    assert "Returner Diagnosis" in combined
    assert "Legendary Planner Pro" in combined
    assert "Build Fit Advisor" in combined
    assert "No automatic trading" in combined
    assert "API key" in combined
    assert "python -m uvicorn gw2radar.api.main:app --reload" in combined
    assert "gw2radar.player.activeBuildId" in combined
    assert "PlayerIntent" in combined
    assert "FreshnessSignal" in combined
    assert "build_upgrade_effects" in combined
    assert "reviewed and enabled KB rules" in combined
    assert "Delete all private data" in combined
