"""Cross-layer pipeline audit trail."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEntry:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    layer: str = ""
    operation: str = ""
    input_summary: str = ""
    output_summary: str = ""
    duration_ms: float = 0.0
    success: bool = True
    details: dict[str, Any] = field(default_factory=dict)


class AuditTrail:
    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def record(self, layer: str, operation: str, duration_ms: float = 0.0,
               success: bool = True, input_summary: str = "",
               output_summary: str = "", **details: Any) -> AuditEntry:
        entry = AuditEntry(
            layer=layer,
            operation=operation,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            success=success,
            details=details,
        )
        self._entries.append(entry)
        return entry

    def get_entries(self, layer: str | None = None,
                    operation: str | None = None,
                    limit: int = 50) -> list[AuditEntry]:
        result = list(self._entries)
        if layer:
            result = [e for e in result if e.layer == layer]
        if operation:
            result = [e for e in result if e.operation == operation]
        return result[-limit:]

    def summary(self) -> dict[str, Any]:
        total = len(self._entries)
        by_layer: dict[str, int] = {}
        failures = 0
        for e in self._entries:
            by_layer[e.layer] = by_layer.get(e.layer, 0) + 1
            if not e.success:
                failures += 1
        return {
            "total_executions": total,
            "failures": failures,
            "success_rate": (total - failures) / total if total > 0 else 1.0,
            "by_layer": by_layer,
            "latest": [
                {"timestamp": e.timestamp.isoformat(), "layer": e.layer,
                 "operation": e.operation, "success": e.success,
                 "duration_ms": e.duration_ms}
                for e in self._entries[-5:]
            ],
        }

    def latest_by_layer(self, layer: str, n: int = 3) -> list[AuditEntry]:
        layer_entries = [e for e in self._entries if e.layer == layer]
        return layer_entries[-n:]

    def clear(self) -> None:
        self._entries.clear()
