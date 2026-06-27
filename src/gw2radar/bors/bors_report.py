from datetime import datetime, timezone
from typing import Any

from gw2radar.bors.business_kpi import BusinessKPI
from gw2radar.bors.business_risk import BusinessRisk
from gw2radar.bors.decision_engine import DecisionRecord


class BORSReport:
    def __init__(self, kpis: list[BusinessKPI],
                 risks: list[BusinessRisk],
                 decisions: list[DecisionRecord]) -> None:
        self.kpis = kpis
        self.risks = risks
        self.decisions = decisions
        self.generated_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "kpis": [
                {"name": k.name, "value": k.value, "confidence": k.confidence,
                 "unit": k.unit, "trend": k.trend}
                for k in self.kpis
            ],
            "risks": [
                {"name": r.name, "level": r.level.value, "score": r.score,
                 "confidence": r.confidence, "mitigation": r.mitigation}
                for r in self.risks
            ],
            "decisions": [
                {"decision": d.decision.value, "score": d.score,
                 "confidence": d.confidence, "reason": d.reason}
                for d in self.decisions
            ],
        }

    def to_html(self) -> str:
        rows = []
        for d in self.decisions:
            rows.append(f"<h3>Decision: {d.decision.value}</h3>"
                        f"<p>Score: {d.score:.2f} | "
                        f"Confidence: {d.confidence:.2f}</p>"
                        f"<p>{d.reason}</p>")
        kpi_rows = "".join(
            f"<tr><td>{k.name}</td><td>{k.value:.2f}</td>"
            f"<td>{k.unit}</td></tr>"
            for k in self.kpis
        )
        risk_rows = "".join(
            f"<tr><td>{r.name}</td><td>{r.level.value}</td>"
            f"<td>{r.score:.2f}</td></tr>"
            for r in self.risks
        )
        return (
            "<html><body>"
            f"<h2>BORS Report</h2>"
            f"{''.join(rows)}"
            f"<h3>KPIs</h3><table border='1'>{kpi_rows}</table>"
            f"<h3>Risks</h3><table border='1'>{risk_rows}</table>"
            f"<p>Generated: {self.generated_at.isoformat()}</p>"
            "</body></html>"
        )


class BORSReportGenerator:
    def generate(self, kpis: list[BusinessKPI],
                 risks: list[BusinessRisk],
                 decisions: list[DecisionRecord]) -> BORSReport:
        return BORSReport(kpis=kpis, risks=risks, decisions=decisions)
