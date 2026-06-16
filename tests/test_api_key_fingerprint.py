from gw2radar.security.crypto import fingerprint_api_key


def test_api_key_fingerprint_is_stable_and_non_reversible() -> None:
    raw_key = "12345678-abcdef-secret-key"
    first = fingerprint_api_key(raw_key, server_secret="unit-test-secret")
    second = fingerprint_api_key(raw_key, server_secret="unit-test-secret")

    assert first == second
    assert len(first) == 8
    assert raw_key not in first
    assert fingerprint_api_key(raw_key, server_secret="other-secret") != first
