from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.ops.release_readiness import (
    build_operational_hardening_readiness,
    render_operational_hardening_csv,
    render_operational_hardening_markdown,
)


def test_operational_hardening_readiness_is_ready_after_phases_a_f() -> None:
    readiness = build_operational_hardening_readiness()

    assert readiness.schema_version == "gw2radar.operational_hardening_readiness.v1"
    assert readiness.status == "ready"
    assert readiness.blocker_count == 0
    assert readiness.readiness_score == 100.0
    assert {gate.gate_id for gate in readiness.gates} >= {
        "mvp_closure_ready",
        "post_mvp_phases_a_f_implemented",
        "player_use_path_maturity",
        "release_command_declared",
        "gitnexus_command_declared",
    }
    assert "real billing provider integration" in readiness.deferred_tracks
    assert "no automated trading instruction" in readiness.safety_boundaries


def test_operational_hardening_readiness_exports_markdown_and_csv() -> None:
    readiness = build_operational_hardening_readiness()
    markdown = render_operational_hardening_markdown(readiness)
    csv = render_operational_hardening_csv(readiness)

    assert "# Operational Hardening Readiness" in markdown
    assert "## Required Commands" in markdown
    assert "gate_id,status,blocker,evidence" in csv
    assert "post_mvp_phases_a_f_implemented,pass,false" in csv


def test_operational_release_readiness_api_contract() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/ops/release-readiness")
    markdown = client.get("/api/v1/ops/release-readiness?format=markdown")
    csv = client.get("/api/v1/ops/release-readiness?format=csv")

    assert response.status_code == 200
    readiness = response.json()["data"]["release_readiness"]
    assert readiness["status"] == "ready"
    assert readiness["blocker_count"] == 0
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert "# Operational Hardening Readiness" in markdown.text
    assert csv.status_code == 200
    assert csv.headers["content-type"].startswith("text/csv")
    assert "gate_id,status,blocker,evidence" in csv.text
