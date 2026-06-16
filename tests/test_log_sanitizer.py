from gw2radar.security.log_sanitizer import sanitize_log_payload


def test_log_sanitizer_redacts_nested_secret_fields() -> None:
    raw_key = "12345678-abcdef-secret-key"
    payload = {
        "user_id": "local-user",
        "api_key": raw_key,
        "headers": {"Authorization": f"Bearer {raw_key}"},
        "nested": [{"access_token": raw_key, "safe": "ok"}],
    }

    sanitized = sanitize_log_payload(payload)

    assert raw_key not in str(sanitized)
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["headers"]["Authorization"] == "[REDACTED]"
    assert sanitized["nested"][0]["access_token"] == "[REDACTED]"
    assert sanitized["nested"][0]["safe"] == "ok"
