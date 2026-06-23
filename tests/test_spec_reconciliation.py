from harness.spec_reconciliation import build_reconciliation, render_markdown


def test_partial_spec_reconciliation_covers_all_partial_specs() -> None:
    reconciliation = build_reconciliation()

    assert reconciliation["schema_version"] == "gw2radar.partial_spec_reconciliation.v1"
    assert reconciliation["partial_count"] == 12
    assert reconciliation["reconciled_count"] == 12
    assert reconciliation["needs_review_count"] == 0


def test_partial_spec_reconciliation_keeps_key_gap_types() -> None:
    reconciliation = build_reconciliation()
    gap_types = reconciliation["gap_type_counts"]

    assert gap_types["implemented_with_live_gateway_limit"] == 2
    assert gap_types["legacy_spec_drift"] == 2
    assert gap_types["broad_roadmap"] == 2
    assert gap_types["implemented_for_mock_payment"] == 1


def test_partial_spec_reconciliation_has_evidence_tests_and_next_priority() -> None:
    reconciliation = build_reconciliation()

    assert all(record["evidence_tests"] for record in reconciliation["records"])
    assert any(
        "tests/test_gw2_api_client_official_contract.py" in record["evidence_tests"]
        for record in reconciliation["records"]
    )
    assert "reviewed content depth" in reconciliation["next_priority"]


def test_partial_spec_reconciliation_markdown_sections() -> None:
    markdown = render_markdown(build_reconciliation())

    assert "# Partial Spec Reconciliation" in markdown
    assert "## Gap Type Counts" in markdown
    assert "## Reconciliation Table" in markdown
    assert "## Next Priority" in markdown
