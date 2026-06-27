import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


class MemoryGraph:
    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def store(self, key: str, value: Any, ttl: float = 0) -> None:
        expires = (time.time() + ttl) if ttl > 0 else 0.0
        self._store[key] = (value, expires)

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires = entry
        if expires > 0 and time.time() > expires:
            del self._store[key]
            return None
        return value

    def clear(self) -> None:
        self._store.clear()


@dataclass
class ToolCallRecord:
    tool: str
    success: bool
    duration_ms: float
    timestamp: float = field(default_factory=time.time)


class ToolMemory:
    def __init__(self) -> None:
        self._history: list[ToolCallRecord] = []

    def record(self, tool: str, success: bool, duration_ms: float) -> None:
        self._history.append(ToolCallRecord(tool=tool, success=success, duration_ms=duration_ms))

    def success_rate(self, tool: str) -> float:
        calls = [r for r in self._history if r.tool == tool]
        if not calls:
            return 0.0
        successes = sum(1 for r in calls if r.success)
        return successes / len(calls)

    def avg_duration(self, tool: str) -> float:
        calls = [r for r in self._history if r.tool == tool]
        if not calls:
            return 0.0
        return sum(r.duration_ms for r in calls) / len(calls)

    def stats(self) -> dict[str, dict]:
        stats: dict[str, dict] = {}
        for r in self._history:
            s = stats.setdefault(r.tool, {"total": 0, "successes": 0, "total_duration": 0.0})
            s["total"] += 1
            if r.success:
                s["successes"] += 1
            s["total_duration"] += r.duration_ms
        for tool, s in stats.items():
            s["success_rate"] = s["successes"] / s["total"] if s["total"] > 0 else 0.0
            s["avg_duration"] = s["total_duration"] / s["total"] if s["total"] > 0 else 0.0
        return stats


@dataclass
class EpisodeRecord:
    agent: str
    action: str
    success: bool
    timestamp: float = field(default_factory=time.time)


class EpisodicMemory:
    def __init__(self) -> None:
        self._episodes: list[EpisodeRecord] = []

    def record(self, agent: str, action: str, success: bool) -> None:
        self._episodes.append(EpisodeRecord(agent=agent, action=action, success=success))

    def detect_patterns(self, window: int = 5) -> list[dict]:
        if len(self._episodes) < window:
            return []
        recent = self._episodes[-window:]
        pattern_counts: dict[str, dict] = defaultdict(lambda: {"count": 0, "failures": 0})
        for ep in recent:
            key = f"{ep.agent}:{ep.action}"
            pattern_counts[key]["count"] += 1
            if not ep.success:
                pattern_counts[key]["failures"] += 1
        return [
            {"pattern": key, "count": v["count"], "failures": v["failures"],
             "failure_rate": v["failures"] / v["count"] if v["count"] > 0 else 0.0}
            for key, v in pattern_counts.items()
        ]
