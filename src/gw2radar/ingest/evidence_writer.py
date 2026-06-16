from hashlib import sha256
import json
from typing import Any

from gw2radar.ingest.security import mask_api_key
from gw2radar.ontology.schemas import Evidence


SENSITIVE_KEYS = {"access_token", "api_key", "token", "authorization"}


def sanitize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key.lower() in SENSITIVE_KEYS:
                sanitized[key] = mask_api_key(str(value))
            else:
                sanitized[key] = sanitize_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


class EvidenceWriter:
    def from_api_payload(
        self,
        *,
        evidence_id: str,
        endpoint: str,
        payload: Any,
        confidence: float = 1.0,
    ) -> Evidence:
        sanitized = sanitize_payload(payload)
        encoded = json.dumps(sanitized, sort_keys=True, default=str).encode("utf-8")
        return Evidence(
            id=evidence_id,
            source="gw2_api",
            source_type="gw2_api",
            source_url=f"https://api.guildwars2.com{endpoint}",
            raw_hash=sha256(encoded).hexdigest(),
            raw_payload=sanitized,
            payload_ref=evidence_id,
            confidence=confidence,
            license_note="Official Guild Wars 2 API payload metadata; sensitive fields masked.",
        )
