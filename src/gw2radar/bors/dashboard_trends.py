"""Dashboard time-series tracking for KPI and risk history."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from gw2radar.bors.business_kpi import BusinessKPI
from gw2radar.bors.business_risk import BusinessRisk
from gw2radar.bors.decision_engine import DecisionRecord


@dataclass
class TimeSeriesPoint:
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    values: dict[str, float] = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)


class TrendTracker:
    def __init__(self, max_points: int = 100) -> None:
        self._points: list[TimeSeriesPoint] = []
        self._max_points = max_points

    def record(self, kpis: list[BusinessKPI],
               risks: list[BusinessRisk],
               decisions: list[DecisionRecord]) -> None:
        values: dict[str, float] = {}
        labels: dict[str, str] = {}
        for kpi in kpis:
            values[f"kpi:{kpi.name}"] = kpi.value
            labels[f"kpi:{kpi.name}"] = kpi.unit
        for risk in risks:
            values[f"risk:{risk.name}"] = risk.score
            labels[f"risk:{risk.name}"] = risk.level.value
        for dec in decisions:
            values["decision:score"] = dec.score
            labels["decision:value"] = dec.decision.value
        self._points.append(TimeSeriesPoint(values=values, labels=labels))
        if len(self._points) > self._max_points:
            self._points = self._points[-self._max_points:]

    def series(self, metric: str) -> list[dict]:
        return [
            {"timestamp": p.timestamp.isoformat(), "value": p.values.get(metric)}
            for p in self._points
            if metric in p.values
        ]

    def all_metrics(self) -> list[str]:
        seen: set[str] = set()
        for p in self._points:
            seen.update(p.values.keys())
        return sorted(seen)

    def latest(self) -> dict[str, Any]:
        if not self._points:
            return {}
        latest_point = self._points[-1]
        return {
            "timestamp": latest_point.timestamp.isoformat(),
            "values": dict(latest_point.values),
            "labels": dict(latest_point.labels),
        }

    def trend(self, metric: str) -> str:
        values = [p.values.get(metric) for p in self._points if metric in p.values]
        values = [v for v in values if v is not None]
        if len(values) < 2:
            return "insufficient_data"
        recent = values[-3:]
        older = values[:-3]
        if not older:
            return "stable"
        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)
        diff = avg_recent - avg_older
        if diff > 0.05:
            return "rising"
        if diff < -0.05:
            return "falling"
        return "stable"

    def summary(self) -> dict[str, Any]:
        metrics = self.all_metrics()
        return {
            "point_count": len(self._points),
            "metric_count": len(metrics),
            "metrics": {
                m: {
                    "latest_value": self._get_latest(m),
                    "trend": self.trend(m),
                    "data_points": len(self.series(m)),
                }
                for m in metrics
            },
        }

    def _get_latest(self, metric: str) -> float | None:
        for p in reversed(self._points):
            if metric in p.values:
                return p.values[metric]
        return None
