from gw2radar.player_os.governance.gates import run_governance_gates
from gw2radar.player_os.orchestration.player_os_orchestrator import start_intent, what_if_plan, revise_existing_plan


def test_plan_revision_extracts_time_and_avoid_constraints() -> None:
    started = start_intent("I want to craft Aurora cheaply.")
    result = revise_existing_plan(started.plan.plan_id, "I only have 30 minutes per day and avoid WvW.")

    assert result is not None
    revised, diff, report = result
    assert revised.constraints["daily_time_limit"] == "30m"
    assert revised.constraints["avoid_modes"] == ["wvw"]
    assert diff.changed_constraints["daily_time_limit"] == "30m"
    assert report.version == 1


def test_what_if_preserves_plan_and_returns_warning_for_budget() -> None:
    started = start_intent("Can I play Power Reaper?")
    result = what_if_plan(started.plan.plan_id, "What if I spend 100g?")

    assert result is not None
    assert result.changed_constraints["budget_gold_limit"] == 100
    assert result.feasibility == "feasible_with_review"
    assert result.warnings


def test_governance_blocks_unsafe_trading_and_raw_key_shaped_text() -> None:
    started = start_intent("Guaranteed profit with automated trading 12345678-1234-1234-1234-123456789abc-1234-1234-1234-123456789abc")

    governance = run_governance_gates(started.intent, started.plan)

    assert governance["status"] == "blocked"
    rendered = str(governance)
    assert "Automated trading" in rendered or "guaranteed-profit" in rendered
    assert "Potential raw API key" in rendered
