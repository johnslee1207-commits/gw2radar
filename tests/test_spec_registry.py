from harness.spec_registry import build_registry, render_markdown


def test_spec_registry_links_specs_to_backlog() -> None:
    registry = build_registry()

    assert registry["schema_version"] == "gw2radar.spec_registry_backlog.v1"
    assert registry["spec_count"] >= 40
    assert registry["player_use_path"]["checks"] >= 40
    assert registry["maturity_counts"]
    assert registry["next_tranche"]


def test_spec_registry_keeps_safety_and_test_evidence() -> None:
    registry = build_registry()
    records = registry["records"]

    assert any("privacy/safety boundary referenced" in record["evidence"] for record in records)
    assert any(record["related_tests"] for record in records)
    assert any("docs/analysis/GW2Radar_Official_GW2_API_Compatibility_Layer_Codex_Spec.md" == record["source_path"] for record in records)


def test_spec_registry_markdown_has_operator_sections() -> None:
    markdown = render_markdown(build_registry())

    assert "# Spec Registry And Backlog Index" in markdown
    assert "## Maturity Counts" in markdown
    assert "## Next Stage Tranche" in markdown
    assert "## Registry" in markdown
