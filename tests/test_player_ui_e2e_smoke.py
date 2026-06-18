from harness import run_player_ui_e2e_smoke


def test_player_ui_e2e_smoke_harness_passes() -> None:
    assert run_player_ui_e2e_smoke.main() == 0
