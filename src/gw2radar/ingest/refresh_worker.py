from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.refresh_queue_status import RefreshQueueStatus


class RefreshWorker:
    def __init__(self, repository: RefreshQueueRepository, gateway: Gw2ApiGateway) -> None:
        self.repository = repository
        self.gateway = gateway

    def process_next(self) -> dict:
        request = self.repository.next_due()
        if request is None:
            return {"status": "idle"}
        self.repository.mark_processing(request.request_id)
        result = self.gateway.get(request.endpoint, params=request.params, priority=request.priority)
        if result.status in {GatewayStatus.OK, GatewayStatus.CACHE_HIT}:
            self.repository.mark_succeeded(request.request_id)
            return {"status": RefreshQueueStatus.SUCCEEDED.value, "request_id": request.request_id}
        if result.status in {GatewayStatus.REFRESH_PENDING, GatewayStatus.RATE_LIMITED_RETRYING}:
            self.repository.mark_retry(
                request.request_id,
                retry_after_seconds=result.retry_after_seconds or 30,
                error=result.status.value,
            )
            return {"status": RefreshQueueStatus.DELAYED.value, "request_id": request.request_id}
        self.repository.mark_failed(request.request_id, result.status.value)
        return {"status": RefreshQueueStatus.FAILED.value, "request_id": request.request_id}
