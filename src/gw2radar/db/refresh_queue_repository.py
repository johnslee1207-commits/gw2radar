from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.db.models import RefreshQueueModel
from gw2radar.ingest.refresh_queue import (
    RefreshQueueCreate,
    RefreshQueueItem,
    RefreshQueuePriority,
    RefreshQueueStatus,
    RefreshTaskType,
)
from gw2radar.ingest.request_queue import QueuedRequest

SENSITIVE_PARAM_KEYS = {"api_key", "access_token", "authorization", "token", "proxy_url", "outbound_ip"}


class RefreshQueueRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(
        self,
        request: QueuedRequest | RefreshQueueCreate,
        *,
        status: RefreshQueueStatus = RefreshQueueStatus.QUEUED,
    ) -> QueuedRequest | RefreshQueueItem:
        now = datetime.now(timezone.utc)
        if isinstance(request, QueuedRequest):
            item = _create_from_queued_request(request)
            task_id = request.request_id
            queued_at = _ensure_aware(request.queued_at)
        else:
            item = request
            task_id = f"refresh:{uuid4().hex}"
            queued_at = now

        params = _sanitize_params(item.params_json or {})
        params_hash = _params_hash(params)
        model = self.session.get(RefreshQueueModel, task_id)
        if model is None:
            self.session.add(
                RefreshQueueModel(
                    request_id=task_id,
                    task_type=item.task_type.value,
                    endpoint=item.endpoint,
                    method=item.method,
                    params_hash=params_hash,
                    params_json=params,
                    priority=item.priority.value,
                    status=status.value,
                    attempts=0,
                    max_attempts=item.max_attempts,
                    account_id=item.account_id,
                    feature_scope=item.feature_scope,
                    created_at=queued_at,
                    updated_at=now,
                )
            )
        else:
            model.task_type = item.task_type.value
            model.endpoint = item.endpoint
            model.method = item.method
            model.params_hash = params_hash
            model.params_json = params
            model.priority = item.priority.value
            model.status = status.value
            model.max_attempts = item.max_attempts
            model.account_id = item.account_id
            model.feature_scope = item.feature_scope
            model.updated_at = now
        self.session.commit()
        if isinstance(request, QueuedRequest):
            return request
        return _model_to_item(self._get_required(task_id))

    def list_by_status(
        self,
        status: RefreshQueueStatus,
        limit: int = 100,
        *,
        as_items: bool = False,
    ) -> list[QueuedRequest] | list[RefreshQueueItem]:
        models = self.session.scalars(
            select(RefreshQueueModel)
            .where(RefreshQueueModel.status == status.value)
            .order_by(RefreshQueueModel.priority, RefreshQueueModel.created_at)
            .limit(limit)
        )
        if as_items:
            return [_model_to_item(model) for model in models]
        return [_model_to_request(model) for model in models]

    def lease_next(
        self,
        worker_id: str,
        now: datetime,
        lease_seconds: int = 60,
    ) -> RefreshQueueItem | None:
        now = _ensure_aware(now)
        models = self.session.scalars(
            select(RefreshQueueModel)
            .where(
                RefreshQueueModel.status.in_(
                    [RefreshQueueStatus.QUEUED.value, RefreshQueueStatus.DELAYED.value, RefreshQueueStatus.PROCESSING.value]
                )
            )
            .order_by(RefreshQueueModel.priority, RefreshQueueModel.created_at)
        )
        for model in models:
            next_attempt_at = _ensure_aware(model.next_attempt_at)
            leased_until = _ensure_aware(model.leased_until)
            if model.status == RefreshQueueStatus.DELAYED.value and next_attempt_at and next_attempt_at > now:
                continue
            if model.status == RefreshQueueStatus.PROCESSING.value and leased_until and leased_until > now:
                continue
            model.status = RefreshQueueStatus.PROCESSING.value
            model.worker_id = worker_id
            model.leased_until = now + timedelta(seconds=lease_seconds)
            model.updated_at = now
            self.session.commit()
            return _model_to_item(model)
        return None

    def next_due(self, *, now: datetime | None = None) -> QueuedRequest | None:
        item = self.lease_next(worker_id="legacy-worker", now=now or datetime.now(timezone.utc))
        if item is None:
            return None
        return _item_to_request(item)

    def mark_done(self, task_id: str) -> RefreshQueueItem:
        model = self._get_required(task_id)
        now = datetime.now(timezone.utc)
        model.status = RefreshQueueStatus.SUCCEEDED.value
        model.worker_id = None
        model.leased_until = None
        model.updated_at = now
        model.completed_at = now
        self.session.commit()
        return _model_to_item(model)

    def mark_retry(
        self,
        task_id: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        next_attempt_at: datetime | None = None,
        retry_after_seconds: int | None = None,
        error: str | None = None,
    ) -> RefreshQueueItem:
        model = self._get_required(task_id)
        now = datetime.now(timezone.utc)
        retry_seconds = retry_after_seconds if retry_after_seconds is not None else 30
        model.status = RefreshQueueStatus.DELAYED.value
        model.attempts += 1
        model.retry_after_seconds = retry_after_seconds
        model.next_attempt_at = _ensure_aware(next_attempt_at) or now + timedelta(seconds=retry_seconds)
        model.worker_id = None
        model.leased_until = None
        model.last_status_code = status_code
        model.last_error_code = error_code or error or "refresh_retry"
        model.last_error = error_message or error or model.last_error_code
        model.updated_at = now
        self.session.commit()
        return _model_to_item(model)

    def mark_processing(self, task_id: str) -> None:
        model = self._get_required(task_id)
        now = datetime.now(timezone.utc)
        model.status = RefreshQueueStatus.PROCESSING.value
        model.updated_at = now
        self.session.commit()

    def mark_succeeded(self, task_id: str) -> None:
        self.mark_done(task_id)

    def mark_failed(
        self,
        task_id: str,
        error: str | None = None,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> RefreshQueueItem:
        model = self._get_required(task_id)
        now = datetime.now(timezone.utc)
        model.status = RefreshQueueStatus.FAILED.value
        model.worker_id = None
        model.leased_until = None
        model.last_status_code = status_code
        model.last_error_code = error_code or error or "refresh_failed"
        model.last_error = error_message or error or model.last_error_code
        model.updated_at = now
        model.completed_at = now
        self.session.commit()
        return _model_to_item(model)

    def delete_completed_older_than(self, before: datetime) -> int:
        before = _ensure_aware(before)
        models = list(
            self.session.scalars(
                select(RefreshQueueModel).where(
                    RefreshQueueModel.status.in_(
                        [RefreshQueueStatus.SUCCEEDED.value, RefreshQueueStatus.FAILED.value]
                    )
                )
            )
        )
        deleted = 0
        for model in models:
            completed_at = _ensure_aware(model.completed_at)
            if completed_at is not None and completed_at < before:
                self.session.delete(model)
                deleted += 1
        self.session.commit()
        return deleted

    def _get_required(self, task_id: str) -> RefreshQueueModel:
        model = self.session.get(RefreshQueueModel, task_id)
        if model is None:
            raise KeyError(f"Refresh request not found: {task_id}")
        return model


def _create_from_queued_request(request: QueuedRequest) -> RefreshQueueCreate:
    return RefreshQueueCreate(
        task_type=RefreshTaskType.PUBLIC_STATIC_REFRESH,
        priority=_priority_from_legacy(request.priority),
        endpoint=request.endpoint,
        method="GET",
        params_json=request.params,
        max_attempts=3,
    )


def _priority_from_legacy(priority: str) -> RefreshQueuePriority:
    mapping = {
        "P0": RefreshQueuePriority.P0_USER_TRIGGERED_ACTIVE_GOAL,
        "P1": RefreshQueuePriority.P1_ACCOUNT_SNAPSHOT,
        "P2": RefreshQueuePriority.P2_GOAL_RELATED_PRICE,
        "P3": RefreshQueuePriority.P3_PUBLIC_STATIC,
        "P4": RefreshQueuePriority.P4_MARKET_HISTORY_BACKFILL,
    }
    return mapping.get(priority, RefreshQueuePriority.P3_PUBLIC_STATIC)


def _model_to_request(model: RefreshQueueModel) -> QueuedRequest:
    return QueuedRequest(
        endpoint=model.endpoint,
        params=model.params_json or {},
        priority=_legacy_priority(model.priority),
        request_id=model.request_id,
        queued_at=_ensure_aware(model.created_at) or datetime.now(timezone.utc),
        attempts=model.attempts,
        retry_after_seconds=model.retry_after_seconds,
        next_attempt_at=_ensure_aware(model.next_attempt_at),
        last_error=model.last_error,
    )


def _model_to_item(model: RefreshQueueModel) -> RefreshQueueItem:
    return RefreshQueueItem(
        id=model.request_id,
        task_type=RefreshTaskType(model.task_type),
        priority=RefreshQueuePriority(model.priority),
        status=RefreshQueueStatus(model.status),
        endpoint=model.endpoint,
        method=model.method,
        params_hash=model.params_hash,
        params_json=model.params_json,
        account_id=model.account_id,
        feature_scope=model.feature_scope,
        attempt_count=model.attempts,
        max_attempts=model.max_attempts,
        next_attempt_at=_ensure_aware(model.next_attempt_at),
        leased_until=_ensure_aware(model.leased_until),
        worker_id=model.worker_id,
        last_status_code=model.last_status_code,
        last_error_code=model.last_error_code,
        last_error_message=model.last_error,
        created_at=_ensure_aware(model.created_at) or datetime.now(timezone.utc),
        updated_at=_ensure_aware(model.updated_at) or datetime.now(timezone.utc),
        completed_at=_ensure_aware(model.completed_at),
    )


def _item_to_request(item: RefreshQueueItem) -> QueuedRequest:
    return QueuedRequest(
        endpoint=item.endpoint,
        params=item.params_json or {},
        priority=_legacy_priority(item.priority.value),
        request_id=item.id,
        queued_at=item.created_at,
        attempts=item.attempt_count,
        next_attempt_at=item.next_attempt_at,
        last_error=item.last_error_message,
    )


def _legacy_priority(priority: str) -> str:
    if priority.startswith("P0"):
        return "P0"
    if priority.startswith("P1"):
        return "P1"
    if priority.startswith("P2"):
        return "P2"
    if priority.startswith("P4"):
        return "P4"
    return "P3"


def _sanitize_params(params: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in params.items():
        key_lower = key.lower()
        if key_lower in SENSITIVE_PARAM_KEYS or "authorization" in key_lower or "proxy" in key_lower:
            continue
        if isinstance(value, dict):
            sanitized[key] = _sanitize_params(value)
        else:
            sanitized[key] = value
    return sanitized


def _params_hash(params: dict[str, Any]) -> str:
    encoded = json.dumps(params, sort_keys=True, default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _ensure_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
