from gw2radar.ops.aegisradar_borrowing import (
    build_aegisradar_borrowing_assessment,
    render_aegisradar_borrowing_markdown,
)


def test_aegisradar_borrowing_assessment_prioritizes_targeted_adaptation() -> None:
    assessment = build_aegisradar_borrowing_assessment()

    assert assessment.schema_version == "gw2radar.aegisradar_borrowing_assessment.v1"
    assert assessment.status == "ready_for_targeted_adaptation"
    assert assessment.reference_repo == "D:\\Projects\\AegisRadar"
    assert assessment.adopt_now[0].priority_id == "p0_trial_key_flow_visibility"
    assert "valid keys can connect without visible outputs" in assessment.adopt_now[0].reason
    assert any(signal.signal_id == "three_layer_graph" for signal in assessment.ontology_signals)
    assert any(signal.signal_id == "three_step_user_journey" for signal in assessment.ux_signals)


def test_aegisradar_borrowing_assessment_keeps_gw2_boundaries() -> None:
    assessment = build_aegisradar_borrowing_assessment()
    all_text = render_aegisradar_borrowing_markdown(assessment)

    assert "Do not copy AegisRadar CO2" in all_text
    assert "Do not make GW2Radar depend on D:\\Projects\\AegisRadar at runtime" in all_text
    assert "raw API keys" in all_text
    assert "automated trading" in all_text
    assert "Postgres pgvector GraphRAG parity" in all_text
    assert "p0_trial_key_flow_visibility" in assessment.next_priority


def test_aegisradar_borrowing_markdown_is_operator_readable() -> None:
    markdown = render_aegisradar_borrowing_markdown(build_aegisradar_borrowing_assessment())

    assert markdown.startswith("# AegisRadar Borrowing Assessment")
    assert "## Reference Signals" in markdown
    assert "## Adopt Now" in markdown
    assert "## Defer" in markdown
    assert "## Explicit Non-Goals" in markdown
    assert "`D:\\Projects\\AegisRadar\\docs\\graph_ontology.md`" in markdown
