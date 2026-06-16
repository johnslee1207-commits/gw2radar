from dataclasses import dataclass, field
from datetime import datetime, timezone
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


class RequestQueue:
    def __init__(self) -> None:
        self._items: list[QueuedRequest] = []

    def enqueue(self, request: QueuedRequest) -> QueuedRequest:
        self._items.append(request)
        return request

    def delayed(self) -> list[QueuedRequest]:
        return list(self._items)
