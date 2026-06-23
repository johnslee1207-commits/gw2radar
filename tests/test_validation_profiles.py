from harness.validation_profiles import (
    get_validation_profile,
    get_validation_stage_gate,
    list_validation_profiles,
    list_validation_stage_gates,
)


def test_validation_profiles_are_staged_and_stable() -> None:
    profiles = {profile.profile_id: profile for profile in list_validation_profiles()}

    assert set(profiles) == {"fast", "full", "smoke"}
    assert [step.step_id for step in get_validation_profile("fast").steps] == [
        "delivery_lifecycle",
        "productized_report",
        "player_use_path_audit",
        "spec_registry",
        "spec_reconciliation",
    ]
    assert [step.step_id for step in get_validation_profile("smoke").steps] == [
        "mvp_smoke",
        "player_ui_e2e",
        "account_connection",
    ]
    assert [step.step_id for step in get_validation_profile("full").steps] == ["pytest_full"]


def test_validation_profile_commands_use_project_entrypoints() -> None:
    fast_commands = [" ".join(step.command) for step in get_validation_profile("fast").steps]
    smoke_commands = [" ".join(step.command) for step in get_validation_profile("smoke").steps]
    full_commands = [" ".join(step.command) for step in get_validation_profile("full").steps]

    assert any("tests\\test_delivery_lifecycle.py" in command for command in fast_commands)
    assert any("harness\\run_player_use_path_audit.py" in command for command in fast_commands)
    assert any("harness\\run_spec_registry.py --check" in command for command in fast_commands)
    assert any("harness\\run_spec_reconciliation.py --check" in command for command in fast_commands)
    assert any("harness\\run_smoke.py" in command for command in smoke_commands)
    assert any("harness\\run_player_ui_e2e_smoke.py" in command for command in smoke_commands)
    assert any("harness\\run_account_connection_diagnostic.py" in command for command in smoke_commands)
    assert full_commands == [f"{get_validation_profile('full').steps[0].command[0]} -m pytest -q"]


def test_validation_stage_gates_keep_full_regression_for_release_only() -> None:
    gates = {gate.gate_id: gate for gate in list_validation_stage_gates()}

    assert set(gates) == {"release", "stage"}
    assert get_validation_stage_gate("stage").profile_ids == ("fast", "smoke")
    assert get_validation_stage_gate("release").profile_ids == ("fast", "smoke", "full")
    assert "full" not in get_validation_stage_gate("stage").profile_ids
