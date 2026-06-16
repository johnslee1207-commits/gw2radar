from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.db.models import RefreshQueueModel
from gw2radar.ingest.refresh_queue_status import RefreshQueueStatus
from gw2radar.ingest.request_queue import QueuedRequest


class RefreshQueueRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self, request: QueuedRequest, *, status: RefreshQueueStatus = RefreshQueueStatus.QUEUED) -> QueuedRequest:
        existing = self.session.get(RefreshQueueModel, request.request_id)
        now = datetime.now(timezone.utc)
        if existing is None:
            self.session.add(
                RefreshQueueModel(
                    request_id=request.request_id,
                    endpoint=request.endpoint,
                    params_json=request.params,
                    priority=request.priority,
                    status=status.value,
                    attempts=request.attempts,
                    retry_after_seconds=request.retry_after_seconds,
                    next_attempt_at=request.next_attempt_at,
                    last_error=request.last_error,
                    created_at=request.queued_at,
                    updated_at=now,
                )
            )
        else:
            existing.endpoint = request.endpoint
            existing.params_json = request.params
            existing.priority = request.priority
            existing.status = status.value
            existing.attempts = request.attempts
            existing.retry_after_seconds = request.retry_after_seconds
            existing.next_attempt_at = request.next_attempt_at
            existing.last_error = request.last_error
            existing.updated_at = now
        self.session.commit()
        return request

    def mark_retry(self, request_id: str, *, retry_after_seconds: int, error: str) -> QueuedRequest:
        model = self._get_required(request_id)
        request = _model_to_request(model)
        request.mark_retry(retry_after_seconds=retry_after_seconds, error=error)
        model.status = RefreshQueueStatus.DELAYED.value
        model.attempts = request.attempts
        model.retry_after_seconds = retry_after_seconds
        model.next_attempt_at = request.next_attempt_at
        model.last_error = error
        model.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return request

    def mark_processing(self, request_id: str) -> None:
        self._set_status(request_id, RefreshQueueStatus.PROCESSING)

    def mark_succeeded(self, request_id: str) -> None:
        self._set_status(request_id, RefreshQueueStatus.SUCCEEDED)

    def mark_failed(self, request_id: str, error: str) -> None:
        model = self._get_required(request_id)
        model.status = RefreshQueueStatus.FAILED.value
        model.last_error = error
        model.updated_at = datetime.now(timezone.utc)
        self.session.commit()

    def list_by_status(self, status: RefreshQueueStatus) -> list[QueuedRequest]:
        models = self.session.scalars(
            select(RefreshQueueModel)
            .where(RefreshQueueModel.status == status.value)
            .order_by(RefreshQueueModel.priority, RefreshQueueModel.created_at)
        )
        return [_model_to_request(model) for model in models]

    def next_due(self, *, now: datetime | None = None) -> QueuedRequest | None:
        now = now or datetime.now(timezone.utc)
        model = self.session.scalars(
            select(RefreshQueueModel)
            .where(
                RefreshQueueModel.status.in_(
                    [RefreshQueueStatus.QUEUED.value, RefreshQueueStatus.DELAYED.value]
                )
            )
            .order_by(RefreshQueueModel.priority, RefreshQueueModel.created_at)
        ).first()
        if model is None:
            return None
        if model.next_attempt_at is not None and model.next_attempt_at > now:
            return None
        return _model_to_request(model)

    def _set_status(self, request_id: str, status: RefreshQueueStatus) -> None:
        model = self._get_required(request_id)
        model.status = status.value
        model.updated_at = datetime.now(timezone.utc)
        self.session.commit()

    def _get_required(self, request_id: str) -> RefreshQueueModel:
        model = self.session.get(RefreshQueueModel, request_id)
        if model is None:
            raise KeyError(f"Refresh request not found: {request_id}")
        return model


def _model_to_request(model: RefreshQueueModel) -> QueuedRequest:
    return QueuedRequest(
        endpoint=model.endpoint,
        params=model.params_json or {},
        priority=model.priority,
        request_id=model.request_id,
        queued_at=model.created_at,
        attempts=model.attempts,
        retry_after_seconds=model.retry_after_seconds,
        next_attempt_at=model.next_attempt_at,
        last_error=model.last_error,
    )
