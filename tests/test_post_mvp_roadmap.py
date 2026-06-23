from harness.post_mvp_roadmap import build_roadmap, render_markdown


def test_post_mvp_roadmap_preserves_current_mvp_closure() -> None:
    roadmap = build_roadmap()

    assert roadmap["schema_version"] == "gw2radar.post_mvp_production_roadmap.v1"
    assert roadmap["current_mvp_status"] == "ready_to_close_mvp_stage"
    assert roadmap["blocking_current_mvp"] is False
    assert roadmap["phase_count"] == 6
    assert roadmap["next_phase"] == "phase_c_progression_decision_engine_v1"


def test_post_mvp_roadmap_defers_saas_and_automation() -> None:
    roadmap = build_roadmap()
    phases = {phase["phase_id"]: phase for phase in roadmap["phases"]}

    assert phases["phase_a_trust_credential_mvp"]["status"] == "implemented_mvp"
    assert phases["phase_b_report_product_close_loop"]["status"] == "implemented_mvp"
    assert phases["phase_c_progression_decision_engine_v1"]["status"] == "next_recommended"
    assert "real payment integration" in phases["phase_e_production_saas_foundation"]["defer"]
    assert "automatic trading" in phases["phase_c_progression_decision_engine_v1"]["defer"]
    assert "team workspace credential sharing" in phases["phase_a_trust_credential_mvp"]["defer"]


def test_post_mvp_roadmap_source_coverage() -> None:
    coverage = build_roadmap()["source_coverage"]

    assert all(coverage["trust"].values())
    assert all(coverage["saas"].values())
    assert all(coverage["master"].values())


def test_post_mvp_roadmap_markdown_sections() -> None:
    markdown = render_markdown(build_roadmap())

    assert "# Post-MVP Production Roadmap" in markdown
    assert "## Decision" in markdown
    assert "## Phases" in markdown
    assert "Phase A Trust & Credential MVP" in markdown
