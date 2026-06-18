from harness import run_account_connection_diagnostic


def test_account_connection_diagnostic_harness_passes() -> None:
    assert run_account_connection_diagnostic.main() == 0
