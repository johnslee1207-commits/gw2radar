from gw2radar.ops.delivery_maturity_audit import (
    build_delivery_maturity_audit,
    render_delivery_maturity_audit_markdown,
)


def test_delivery_maturity_audit_is_ready_and_evidence_backed() -> None:
    audit = build_delivery_maturity_audit()

    assert audit.status == "ready"
    assert audit.maturity_label == "mature_for_stage"
    assert audit.blocker_count == 0
    assert audit.score == 100.0
    assert all(check.status == "ready" for check in audit.code_checks)
    assert all(metric.status == "ready" for metric in audit.residual_duplication_metrics)
    assert any(edge.target == "delivery_lifecycle_readiness" for edge in audit.semantic_edges)


def test_delivery_maturity_markdown_names_limits_and_next_priority() -> None:
    markdown = render_delivery_maturity_audit_markdown(build_delivery_maturity_audit())

    assert "# Delivery Maturity Audit" in markdown
    assert "## Semantic Graph" in markdown
    assert "## Known Limits" in markdown
    assert "Run release gate for milestone closure" in markdown
