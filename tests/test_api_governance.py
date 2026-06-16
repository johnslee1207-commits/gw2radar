from pathlib import Path
from typing import Any

from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.evidence_writer import EvidenceWriter
from gw2radar.ingest.gw2_api_client import Gw2ApiRateLimitError, Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.security import mask_api_key


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        self.calls += 1
        return Gw2ApiResponse(
            endpoint=endpoint,
            params=params or {},
            payload={"ids": (params or {}).get("ids", [])},
            request_id=request_id,
        )


class RateLimitedClient:
    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        raise Gw2ApiRateLimitError(endpoint, request_id or "unknown")


def test_constitution_documents_exist() -> None:
    assert Path("GW2RADAR_PROJECT_CONSTITUTION.md").exists()
    assert Path("GW2RADAR_API_ACCESS_GOVERNANCE.md").exists()
    assert Path("docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md").exists()


def test_api_key_masking_and_evidence_sanitization() -> None:
    api_key = "12345678-abcdef-secret-key"
    assert mask_api_key(api_key) == "1234...-key"

    evidence = EvidenceWriter().from_api_payload(
        evidence_id="evidence:test",
        endpoint="/v2/account",
        payload={"api_key": api_key, "nested": {"access_token": api_key}},
    )

    assert api_key not in str(evidence.raw_payload)
    assert evidence.raw_payload["api_key"] == "1234...-key"
    assert evidence.source_type == "gw2_api"


def test_gateway_uses_cache_and_deduplicates_client_calls() -> None:
    client = FakeClient()
    gateway = Gw2ApiGateway(client=client)

    first = gateway.get("/v2/items", params={"ids": [1, 2, 3]}, api_key="12345678-abcdef-secret-key")
    second = gateway.get("/v2/items", params={"ids": [1, 2, 3]}, api_key="12345678-abcdef-secret-key")

    assert first.status == GatewayStatus.OK
    assert second.status == GatewayStatus.CACHE_HIT
    assert client.calls == 1
    assert first.evidence_id == second.evidence_id


def test_gateway_429_returns_retrying_without_proxy_or_ip_switch() -> None:
    gateway = Gw2ApiGateway(client=RateLimitedClient())

    result = gateway.get("/v2/account", api_key="12345678-abcdef-secret-key", priority="P1")

    assert result.status == GatewayStatus.RATE_LIMITED_RETRYING
    assert result.retry_after_seconds == 30
    delayed = gateway.queue.delayed()
    assert delayed
    assert delayed[0].attempts == 1
    assert delayed[0].next_attempt_at is not None
    assert "params_hash" in result.diagnostics


def test_business_modules_do_not_directly_call_external_http_clients() -> None:
    forbidden = ("requests.", "httpx.", "urllib.request", "aiohttp.")
    allowed_files = {
        Path("src/gw2radar/ingest/gw2_api_client.py"),
        Path("src/gw2radar/ingest/gw2_api_gateway.py"),
    }
    for path in Path("src/gw2radar").rglob("*.py"):
        if path in allowed_files:
            continue
        text = path.read_text(encoding="utf-8")
        assert not any(pattern in text for pattern in forbidden), path
