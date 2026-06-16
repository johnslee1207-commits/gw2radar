from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any

from gw2radar.ingest.cache_store import ENDPOINT_TTL_SECONDS, InMemoryCacheStore
from gw2radar.ingest.evidence_writer import EvidenceWriter
from gw2radar.ingest.gw2_api_client import GW2ApiClient, Gw2ApiRateLimitError, Gw2ApiResponse
from gw2radar.ingest.rate_limiter import TokenBucketRateLimiter
from gw2radar.ingest.request_queue import QueuedRequest, RequestQueue


@dataclass
class GatewayResult:
    status: str
    endpoint: str
    request_id: str
    payload: Any | None = None
    evidence_id: str | None = None
    retry_after_seconds: int | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


class Gw2ApiGateway:
    def __init__(
        self,
        *,
        client: GW2ApiClient | None = None,
        cache: InMemoryCacheStore | None = None,
        limiter: TokenBucketRateLimiter | None = None,
        queue: RequestQueue | None = None,
        evidence_writer: EvidenceWriter | None = None,
    ) -> None:
        self.client = client or GW2ApiClient()
        self.cache = cache or InMemoryCacheStore()
        self.limiter = limiter or TokenBucketRateLimiter()
        self.queue = queue or RequestQueue()
        self.evidence_writer = evidence_writer or EvidenceWriter()

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        priority: str = "P3",
    ) -> GatewayResult:
        params = params or {}
        request = QueuedRequest(endpoint=endpoint, params=params, priority=priority)
        cache_key = self._cache_key(endpoint, params)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return GatewayResult(
                status="cache_hit",
                endpoint=endpoint,
                request_id=request.request_id,
                payload=cached["payload"],
                evidence_id=cached["evidence_id"],
            )

        if not self.limiter.allow_request():
            self.queue.enqueue(request)
            return GatewayResult(
                status="refresh_pending",
                endpoint=endpoint,
                request_id=request.request_id,
                retry_after_seconds=15,
            )

        try:
            response = self.client.get(
                endpoint,
                params=params,
                api_key=api_key,
                request_id=request.request_id,
            )
        except Gw2ApiRateLimitError:
            self.limiter.apply_429_penalty()
            self.queue.enqueue(request)
            return GatewayResult(
                status="rate_limited_retrying",
                endpoint=endpoint,
                request_id=request.request_id,
                retry_after_seconds=30,
                diagnostics={"params_hash": self._params_hash(params)},
            )

        if response.status_code == 429:
            self.limiter.apply_429_penalty()
            self.queue.enqueue(request)
            return GatewayResult(
                status="rate_limited_retrying",
                endpoint=endpoint,
                request_id=request.request_id,
                retry_after_seconds=30,
                diagnostics={"params_hash": self._params_hash(params)},
            )

        evidence = self.evidence_writer.from_api_payload(
            evidence_id=f"evidence:{request.request_id}",
            endpoint=endpoint,
            payload={"endpoint": endpoint, "params": params, "payload": response.payload},
        )
        ttl = self._ttl_seconds(endpoint)
        self.cache.set(cache_key, {"payload": response.payload, "evidence_id": evidence.id}, ttl)
        return GatewayResult(
            status="ok",
            endpoint=endpoint,
            request_id=request.request_id,
            payload=response.payload,
            evidence_id=evidence.id,
        )

    def _ttl_seconds(self, endpoint: str) -> int:
        normalized = endpoint.strip("/").replace("/", "_")
        return ENDPOINT_TTL_SECONDS.get(normalized, 30 * 60)

    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        return f"{endpoint}:{self._params_hash(params)}"

    def _params_hash(self, params: dict[str, Any]) -> str:
        encoded = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
        return sha256(encoded).hexdigest()
