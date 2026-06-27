from datetime import datetime, timezone
from typing import Any

from gw2radar.bors.business_kpi import BusinessKPI
from gw2radar.bors.business_risk import BusinessRisk
from gw2radar.bors.decision_engine import DecisionRecord


class BORSDashboard:
    def snapshot(self, kpis: list[BusinessKPI],
                 risks: list[BusinessRisk],
                 decisions: list[DecisionRecord]) -> dict[str, Any]:
        return {
            "snapshot_at": datetime.now(timezone.utc).isoformat(),
            "kpi_count": len(kpis),
            "risk_count": len(risks),
            "decision_count": len(decisions),
            "top_kpis": [
                {"name": k.name, "value": k.value, "trend": k.trend}
                for k in sorted(kpis, key=lambda x: x.value, reverse=True)[:5]
            ],
            "critical_risks": [
                {"name": r.name, "level": r.level.value, "score": r.score}
                for r in risks if r.level.value in ("high", "critical")
            ],
            "latest_decisions": [
                {"decision": d.decision.value, "score": d.score, "reason": d.reason}
                for d in decisions[-5:]
            ],
        }
