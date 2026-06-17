from collections.abc import Callable

from sqlalchemy.orm import Session

from gw2radar.acquisition.models import AcquisitionSourceType
from gw2radar.acquisition.official_api_adapter import run_official_api_acquisition_job
from gw2radar.acquisition.repository import get_source, lease_next_job, mark_job_failed, mark_job_skipped
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway


class AcquisitionWorker:
    def __init__(
        self,
        session: Session,
        *,
        gateway_factory: Callable[[], Gw2ApiGateway] | None = None,
        api_key_provider: Callable[[], str | None] | None = None,
    ) -> None:
        self.session = session
        self.gateway_factory = gateway_factory or Gw2ApiGateway
        self.api_key_provider = api_key_provider or (lambda: None)

    def drain_one(self, worker_id: str = "acquisition-drain-one") -> dict:
        job = lease_next_job(self.session, worker_id=worker_id)
        if job is None:
            return {"status": "idle"}
        source = get_source(self.session, job.source_id)
        if source is None:
            failed = mark_job_failed(
                self.session,
                job.job_id,
                error_code="source_missing",
                error="Acquisition job source is missing.",
            )
            return {"status": "failed", "job_id": failed.job_id, "error_code": failed.last_error_code}

        if source.source_type in {
            AcquisitionSourceType.OFFICIAL_API_PUBLIC,
            AcquisitionSourceType.OFFICIAL_API_PRIVATE,
        }:
            api_key = self.api_key_provider() if source.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE else None
            result = run_official_api_acquisition_job(
                self.session,
                job.job_id,
                gateway=self.gateway_factory(),
                api_key=api_key,
            )
            return {
                "status": result.job.status.value if hasattr(result.job.status, "value") else str(result.job.status),
                "job_id": result.job.job_id,
                "source_id": source.source_id,
                "gateway_status": result.gateway_status,
                "evidence_created": result.evidence_created,
            }

        skipped = mark_job_skipped(
            self.session,
            job.job_id,
            error_code="adapter_not_worker_executable",
            error=f"Acquisition source type {source.source_type.value} is imported by a dedicated manual/local adapter.",
        )
        return {
            "status": "skipped",
            "job_id": skipped.job_id,
            "source_id": source.source_id,
            "error_code": skipped.last_error_code,
        }
