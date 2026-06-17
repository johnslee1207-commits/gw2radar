from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from sqlalchemy.orm import Session

from gw2radar.acquisition.models import (
    AcquisitionJob,
    AcquisitionSourceType,
    ContentType,
    RawEvidenceInput,
)
from gw2radar.acquisition.repository import (
    create_raw_evidence,
    get_job,
    get_source,
    mark_job_delayed,
    mark_job_failed,
    mark_job_succeeded,
)
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult, Gw2ApiGateway


@dataclass(frozen=True)
class OfficialApiAcquisitionResult:
    job: AcquisitionJob
    gateway_status: str
    evidence_created: bool
    gateway_evidence_id: str | None = None


def run_official_api_acquisition_job(
    session: Session,
    job_id: str,
    *,
    gateway: Gw2ApiGateway | None = None,
    api_key: str | None = None,
) -> OfficialApiAcquisitionResult:
    job = get_job(session, job_id)
    if job is None:
        raise ValueError("Acquisition job not found.")
    source = get_source(session, job.source_id)
    if source is None:
        raise ValueError("Acquisition source not found.")
    if source.source_type not in {
        AcquisitionSourceType.OFFICIAL_API_PUBLIC,
        AcquisitionSourceType.OFFICIAL_API_PRIVATE,
    }:
        raise ValueError("Official API adapter can only run official API acquisition sources.")
    if source.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE and not api_key:
        failed = mark_job_failed(session, job.job_id, "missing_api_key", "Private official API acquisition requires a runtime API key.")
        return OfficialApiAcquisitionResult(job=failed, gateway_status=GatewayStatus.PERMISSION_DENIED.value, evidence_created=False)

    endpoint = _endpoint_from_job(job)
    request_params = _request_params_from_job(job)
    gateway = gateway or Gw2ApiGateway()
    result = _call_gateway(gateway, endpoint, request_params, api_key=api_key, priority=_priority_value(job.priority))

    if result.status in {GatewayStatus.OK, GatewayStatus.CACHE_HIT}:
        create_raw_evidence(
            session,
            RawEvidenceInput(
                source_id=source.source_id,
                job_id=job.job_id,
                content_type=ContentType.API_JSON,
                title=f"Official GW2 API response: {endpoint}",
                source_url=_source_url(source.base_url, endpoint),
                payload_hash=_payload_hash(result.payload),
                summary=f"Official GW2 API acquisition for {endpoint}; payload omitted from raw evidence.",
                metadata={
                    "endpoint": endpoint,
                    "params_hash": _payload_hash(request_params),
                    "gateway_status": result.status.value,
                    "gateway_evidence_id": result.evidence_id,
                    "payload_shape": _payload_shape(result.payload),
                    "private_source": source.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE,
                },
            ),
        )
        succeeded = mark_job_succeeded(session, job.job_id)
        return OfficialApiAcquisitionResult(
            job=succeeded,
            gateway_status=result.status.value,
            evidence_created=True,
            gateway_evidence_id=result.evidence_id,
        )

    if result.status in {GatewayStatus.REFRESH_PENDING, GatewayStatus.RATE_LIMITED_RETRYING}:
        delayed = mark_job_delayed(
            session,
            job.job_id,
            result.status.value,
            f"Official GW2 API acquisition delayed for {endpoint}.",
            retry_after_seconds=result.retry_after_seconds,
        )
        return OfficialApiAcquisitionResult(job=delayed, gateway_status=result.status.value, evidence_created=False)

    failed = mark_job_failed(
        session,
        job.job_id,
        result.diagnostics.get("error_code", result.status.value),
        f"Official GW2 API acquisition failed for {endpoint}.",
    )
    return OfficialApiAcquisitionResult(job=failed, gateway_status=result.status.value, evidence_created=False)


def _call_gateway(
    gateway: Gw2ApiGateway,
    endpoint: str,
    request_params: dict[str, Any],
    *,
    api_key: str | None,
    priority: str,
) -> GatewayResult:
    ids = request_params.pop("ids", None)
    if isinstance(ids, list):
        return gateway.get_batch(endpoint, ids=ids, params=request_params, api_key=api_key, priority=priority)
    return gateway.get(endpoint, params=request_params, api_key=api_key, priority=priority)


def _endpoint_from_job(job: AcquisitionJob) -> str:
    endpoint = job.params.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith("/v2/"):
        raise ValueError("Official API acquisition jobs require an endpoint beginning with /v2/.")
    return endpoint


def _request_params_from_job(job: AcquisitionJob) -> dict[str, Any]:
    raw = job.params.get("request_params", {})
    if not isinstance(raw, dict):
        raise ValueError("Official API acquisition job request_params must be an object.")
    return dict(raw)


def _payload_hash(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _payload_shape(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        return {"type": "list", "count": len(payload)}
    if isinstance(payload, dict):
        return {"type": "object", "keys": sorted(str(key) for key in payload.keys())}
    return {"type": type(payload).__name__}


def _source_url(base_url: str | None, endpoint: str) -> str | None:
    if not base_url:
        return None
    return f"{str(base_url).rstrip('/')}{endpoint}"


def _priority_value(priority: Any) -> str:
    return priority.value if hasattr(priority, "value") else str(priority)
