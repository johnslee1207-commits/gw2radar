from collections.abc import Mapping
from typing import Any

SENSITIVE_LOG_KEYS = {"api_key", "access_token", "authorization", "token", "secret", "password"}


def sanitize_log_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in payload.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_LOG_KEYS or any(sensitive in key_lower for sensitive in SENSITIVE_LOG_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            sanitized[key] = sanitize_log_payload(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_payload(item) if isinstance(item, Mapping) else item for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized
