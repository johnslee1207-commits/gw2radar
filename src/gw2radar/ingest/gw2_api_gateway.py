from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any

from gw2radar.ingest.cache_store import InMemoryCacheStore, endpoint_ttl_seconds
from gw2radar.ingest.endpoint_schema import Gw2EndpointKind, batch_endpoints, endpoint_schema
from gw2radar.ingest.evidence_writer import EvidenceWriter
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import GW2ApiClient, Gw2ApiClientError, Gw2ApiRateLimitError, Gw2ApiResponse
from gw2radar.ingest.permission_validator import Gw2PermissionError, parse_tokeninfo, validate_endpoint_permissions
from gw2radar.ingest.rate_limiter import TokenBucketRateLimiter
from gw2radar.ingest.request_queue import QueuedRequest, RequestQueue

BATCH_ENDPOINTS = batch_endpoints()


@dataclass
class GatewayResult:
    status: GatewayStatus
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
        schema = endpoint_schema(endpoint)
        if schema.kind is Gw2EndpointKind.PRIVATE:
            permission_result = self._validate_private_access(endpoint, api_key, request.request_id)
            if permission_result is not None:
                return permission_result

        cache_key = self._cache_key(endpoint, params)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return GatewayResult(
                status=GatewayStatus.CACHE_HIT,
                endpoint=endpoint,
                request_id=request.request_id,
                payload=cached["payload"],
                evidence_id=cached["evidence_id"],
            )

        if not self.limiter.allow_request():
            request.mark_retry(retry_after_seconds=15, error=GatewayStatus.REFRESH_PENDING.value)
            self.queue.enqueue(request)
            return GatewayResult(
                status=GatewayStatus.REFRESH_PENDING,
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
            request.mark_retry(retry_after_seconds=30, error=GatewayStatus.RATE_LIMITED_RETRYING.value)
            self.queue.enqueue(request)
            return GatewayResult(
                status=GatewayStatus.RATE_LIMITED_RETRYING,
                endpoint=endpoint,
                request_id=request.request_id,
                retry_after_seconds=30,
                diagnostics={"params_hash": self._params_hash(params)},
            )
        except Gw2ApiClientError as error:
            return GatewayResult(
                status=GatewayStatus.ERROR,
                endpoint=endpoint,
                request_id=request.request_id,
                diagnostics={
                    "error_code": error.error_code,
                    "status_code": error.status_code,
                    "params_hash": self._params_hash(params),
                },
            )

        if response.status_code == 429:
            self.limiter.apply_429_penalty()
            request.mark_retry(retry_after_seconds=30, error=GatewayStatus.RATE_LIMITED_RETRYING.value)
            self.queue.enqueue(request)
            return GatewayResult(
                status=GatewayStatus.RATE_LIMITED_RETRYING,
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
        ttl = endpoint_ttl_seconds(endpoint)
        self.cache.set(cache_key, {"payload": response.payload, "evidence_id": evidence.id}, ttl)
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=request.request_id,
            payload=response.payload,
            evidence_id=evidence.id,
        )

    def get_batch(
        self,
        endpoint: str,
        *,
        ids: list[int | str],
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        priority: str = "P3",
    ) -> GatewayResult:
        if endpoint not in BATCH_ENDPOINTS:
            raise ValueError(f"Endpoint {endpoint} does not support MVP batch helper.")
        if not ids:
            raise ValueError("Batch ids must not be empty.")
        batch_params = dict(params or {})
        batch_params["ids"] = ",".join(str(item_id) for item_id in ids)
        batch_params["batch_count"] = len(ids)
        return self.get(endpoint, params=batch_params, api_key=api_key, priority=priority)

    def _validate_private_access(
        self,
        endpoint: str,
        api_key: str | None,
        request_id: str,
    ) -> GatewayResult | None:
        if not api_key:
            return GatewayResult(
                status=GatewayStatus.PERMISSION_DENIED,
                endpoint=endpoint,
                request_id=request_id,
                diagnostics={"error_code": "missing_api_key"},
            )
        try:
            tokeninfo_payload = self._fetch_tokeninfo(api_key, request_id=f"{request_id}:tokeninfo")
            tokeninfo = parse_tokeninfo(tokeninfo_payload)
            validate_endpoint_permissions(endpoint, tokeninfo)
        except Gw2PermissionError as error:
            return GatewayResult(
                status=GatewayStatus.PERMISSION_DENIED,
                endpoint=endpoint,
                request_id=request_id,
                diagnostics={
                    "error_code": "missing_permissions",
                    "missing_permissions": sorted(error.missing_permissions),
                },
            )
        except Gw2ApiRateLimitError:
            self.limiter.apply_429_penalty()
            request = QueuedRequest(endpoint="/v2/tokeninfo", params={"target_endpoint": endpoint}, priority="P1")
            request.mark_retry(retry_after_seconds=30, error=GatewayStatus.RATE_LIMITED_RETRYING.value)
            self.queue.enqueue(request)
            return GatewayResult(
                status=GatewayStatus.RATE_LIMITED_RETRYING,
                endpoint=endpoint,
                request_id=request_id,
                retry_after_seconds=30,
                diagnostics={
                    "error_code": "tokeninfo_rate_limited",
                    "params_hash": self._params_hash({"target_endpoint": endpoint}),
                },
            )
        except Gw2ApiClientError as error:
            return GatewayResult(
                status=GatewayStatus.ERROR,
                endpoint=endpoint,
                request_id=request_id,
                diagnostics={
                    "error_code": error.error_code,
                    "status_code": error.status_code,
                },
            )
        return None

    def _fetch_tokeninfo(self, api_key: str, *, request_id: str) -> dict[str, Any]:
        if hasattr(self.client, "fetch_tokeninfo"):
            return self.client.fetch_tokeninfo(api_key, request_id=request_id)
        response = self.client.get("/v2/tokeninfo", api_key=api_key, request_id=request_id)
        return response.payload

    def _cache_key(self, endpoint: str, params: dict[str, Any]) -> str:
        return f"{endpoint}:{self._params_hash(params)}"

    def _params_hash(self, params: dict[str, Any]) -> str:
        encoded = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
        return sha256(encoded).hexdigest()
