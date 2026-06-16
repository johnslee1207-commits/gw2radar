from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


@dataclass
class QueuedRequest:
    endpoint: str
    params: dict[str, Any] = field(default_factory=dict)
    priority: str = "P3"
    request_id: str = field(default_factory=lambda: f"gw2req:{uuid4().hex}")
    queued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    attempts: int = 0
    retry_after_seconds: int | None = None
    next_attempt_at: datetime | None = None
    last_error: str | None = None

    def mark_retry(self, *, retry_after_seconds: int, error: str) -> None:
        self.attempts += 1
        self.retry_after_seconds = retry_after_seconds
        self.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=retry_after_seconds)
        self.last_error = error


class RequestQueue:
    def __init__(self) -> None:
        self._items: list[QueuedRequest] = []

    def enqueue(self, request: QueuedRequest) -> QueuedRequest:
        self._items.append(request)
        return request

    def delayed(self) -> list[QueuedRequest]:
        return list(self._items)


class DurableRequestQueue(RequestQueue):
    def __init__(self, repository) -> None:
        super().__init__()
        self.repository = repository

    def enqueue(self, request: QueuedRequest) -> QueuedRequest:
        super().enqueue(request)
        self.repository.enqueue(request)
        return request
