from harness.validation_profiles import get_validation_profile, list_validation_profiles


def test_validation_profiles_are_staged_and_stable() -> None:
    profiles = {profile.profile_id: profile for profile in list_validation_profiles()}

    assert set(profiles) == {"fast", "full", "smoke"}
    assert [step.step_id for step in get_validation_profile("fast").steps] == [
        "delivery_lifecycle",
        "productized_report",
        "player_use_path_audit",
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
    assert any("harness\\run_smoke.py" in command for command in smoke_commands)
    assert any("harness\\run_player_ui_e2e_smoke.py" in command for command in smoke_commands)
    assert any("harness\\run_account_connection_diagnostic.py" in command for command in smoke_commands)
    assert full_commands == [f"{get_validation_profile('full').steps[0].command[0]} -m pytest -q"]

