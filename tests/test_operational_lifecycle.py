from datetime import UTC, datetime

from gw2radar.ops.lifecycle import (
    DEFAULT_RELEASE_LIFECYCLE,
    OperationalLifecycleStage,
    build_delivery_operational_lifecycle_summary,
    build_operational_lifecycle_summary_from_gates,
    build_operational_lifecycle_summary,
    lifecycle_gate,
    lifecycle_event,
)


def test_operational_lifecycle_summary_tracks_review_chain() -> None:
    summary = build_operational_lifecycle_summary(
        object_id="patch:2026-06-02",
        object_type="kb_patch_rule_candidate",
        events=[
            lifecycle_event("draft", actor="source_registry", occurred_at=datetime(2026, 6, 1, tzinfo=UTC)),
            lifecycle_event("reviewed", actor="reviewer", occurred_at=datetime(2026, 6, 2, tzinfo=UTC)),
            lifecycle_event("persisted", actor="operator", occurred_at=datetime(2026, 6, 3, tzinfo=UTC)),
        ],
    )

    assert summary.schema_version == "gw2radar.operational_lifecycle_summary.v1"
    assert summary.current_stage == OperationalLifecycleStage.PERSISTED
    assert summary.completed_stages == [
        OperationalLifecycleStage.DRAFT,
        OperationalLifecycleStage.REVIEWED,
        OperationalLifecycleStage.PERSISTED,
    ]
    assert summary.missing_stages == [OperationalLifecycleStage.ENABLED]
    assert summary.ready is False
    assert summary.progress_percent == 75.0
    assert summary.latest_actor == "operator"
    assert summary.next_action == "Enable reviewed persisted rules only after separate confirmation."


def test_operational_lifecycle_summary_supports_release_signoff_chain() -> None:
    summary = build_operational_lifecycle_summary(
        object_id="achievement-route-release",
        object_type="achievement_route_release",
        stage_order=DEFAULT_RELEASE_LIFECYCLE,
        events=[
            lifecycle_event("draft", actor="planner", occurred_at=datetime(2026, 6, 1, tzinfo=UTC)),
            lifecycle_event("reviewed", actor="route_reviewer", occurred_at=datetime(2026, 6, 2, tzinfo=UTC)),
            lifecycle_event("exported", actor="operator", occurred_at=datetime(2026, 6, 3, tzinfo=UTC)),
            lifecycle_event("archived", actor="operator", occurred_at=datetime(2026, 6, 4, tzinfo=UTC)),
            lifecycle_event("signed_off", actor="release_lead", occurred_at=datetime(2026, 6, 5, tzinfo=UTC)),
        ],
    )

    assert summary.ready is True
    assert summary.current_stage == OperationalLifecycleStage.SIGNED_OFF
    assert summary.progress_percent == 100.0
    assert summary.latest_actor == "release_lead"
    assert summary.next_action == "Lifecycle is complete for the configured gate."


def test_operational_lifecycle_summary_projects_boolean_gates() -> None:
    summary = build_operational_lifecycle_summary_from_gates(
        object_id="release:gate",
        object_type="achievement_route_release",
        stage_order=[
            OperationalLifecycleStage.DRAFT,
            OperationalLifecycleStage.ARCHIVED,
            OperationalLifecycleStage.DIFF_REVIEWED,
            OperationalLifecycleStage.SIGNED_OFF,
        ],
        gates=[
            lifecycle_gate("draft", complete=True, actor="builder"),
            lifecycle_gate("archived", complete=True, actor="archiver", evidence_refs=["archive:1"]),
            lifecycle_gate("diff_reviewed", complete=False, actor="diff"),
            lifecycle_gate("signed_off", complete=False, actor="lead"),
        ],
    )

    assert summary.current_stage == OperationalLifecycleStage.ARCHIVED
    assert summary.completed_stages == ["draft", "archived"]
    assert summary.missing_stages == ["diff_reviewed", "signed_off"]
    assert summary.ready is False
    assert summary.progress_percent == 50.0
    assert summary.evidence_refs == ["archive:1"]
    assert summary.next_action == "Review archive diff evidence and resolve regressions before sign-off."


def test_delivery_operational_lifecycle_summary_tracks_packet_handoff_chain() -> None:
    summary = build_delivery_operational_lifecycle_summary(
        object_id="delivery:packet",
        object_type="productized_report_delivery",
        draft_ready=True,
        exported_ready=True,
        packaged_ready=True,
        verified_ready=True,
        audited_ready=False,
        handoff_ready=False,
        evidence_refs=["artifact:1", "packet:checksum"],
    )

    assert summary.current_stage == OperationalLifecycleStage.VERIFIED
    assert summary.completed_stages == ["draft", "exported", "packaged", "verified"]
    assert summary.missing_stages == ["audited", "handoff_ready"]
    assert summary.ready is False
    assert summary.progress_percent == 66.7
    assert summary.next_action == "Record a metadata-only verification audit before handoff."
