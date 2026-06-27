import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class LockEntry:
    entity_id: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    acquired_by: str = ""


class LockManager:
    def __init__(self) -> None:
        self._locks: dict[str, LockEntry] = {}

    @contextmanager
    def acquire(self, entity_ids: list[str], owner: str = "") -> Iterator[list[str]]:
        sorted_ids = sorted(entity_ids)
        acquired: list[str] = []
        try:
            for eid in sorted_ids:
                entry = self._locks.setdefault(eid, LockEntry(entity_id=eid))
                entry.lock.acquire()
                entry.acquired_by = owner
                acquired.append(eid)
            yield acquired
        finally:
            for eid in reversed(acquired):
                entry = self._locks.get(eid)
                if entry:
                    entry.acquired_by = ""
                    entry.lock.release()

    def is_locked(self, entity_id: str) -> bool:
        entry = self._locks.get(entity_id)
        return entry is not None and entry.lock.locked()

    def locked_by(self, entity_id: str) -> str:
        entry = self._locks.get(entity_id)
        return entry.acquired_by if entry else ""


class ConcurrentActionRegistry:
    def __init__(self, registry: dict[str, Any]) -> None:
        self._registry = registry
        self._lock_manager = LockManager()

    @contextmanager
    def execute(self, action_id: str, entity_ids: list[str], owner: str = "") -> Iterator[dict]:
        with self._lock_manager.acquire(entity_ids, owner):
            entry = self._registry.get(action_id)
            if not entry:
                raise KeyError(f"Action '{action_id}' not found")
            yield {"action_id": action_id, "status": "acquired", "locked_entities": entity_ids}

    def lock_manager(self) -> LockManager:
        return self._lock_manager
