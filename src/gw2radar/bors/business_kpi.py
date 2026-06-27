from dataclasses import dataclass, field
from enum import Enum


class BusinessKPIType(str, Enum):
    QUALITY = "quality"
    COMPLIANCE = "compliance"
    EVIDENCE_INTEGRITY = "evidence_integrity"
    RELIABILITY = "reliability"
    COVERAGE = "coverage"


@dataclass
class BusinessKPI:
    kpi_type: BusinessKPIType
    name: str
    value: float
    confidence: float = 1.0
    unit: str = "score"
    trend: str = "stable"


class BusinessKPICalculator:
    def calculate_all(self, **sources: dict) -> list[BusinessKPI]:
        kpis: list[BusinessKPI] = []

        qa_gate = sources.get("qa_gate", {})
        if qa_gate:
            passed = qa_gate.get("passed", 0)
            total = qa_gate.get("total", 1)
            value = passed / total if total > 0 else 0.0
            kpis.append(BusinessKPI(
                kpi_type=BusinessKPIType.QUALITY,
                name="quality_score",
                value=min(value, 1.0),
                confidence=qa_gate.get("confidence", 0.9),
                unit="score",
            ))

        compliance = sources.get("compliance", {})
        if compliance:
            passed = compliance.get("passed", 0)
            total = compliance.get("total", 1)
            value = passed / total if total > 0 else 0.0
            kpis.append(BusinessKPI(
                kpi_type=BusinessKPIType.COMPLIANCE,
                name="compliance_rate",
                value=min(value, 1.0),
                confidence=compliance.get("confidence", 0.85),
                unit="pct",
            ))

        evidence = sources.get("evidence", {})
        if evidence:
            chain_intact = evidence.get("chain_intact", False)
            kpis.append(BusinessKPI(
                kpi_type=BusinessKPIType.EVIDENCE_INTEGRITY,
                name="evidence_integrity",
                value=1.0 if chain_intact else 0.0,
                confidence=evidence.get("confidence", 0.95),
                unit="bool",
            ))

        action_history = sources.get("action_history", {})
        if action_history:
            total_actions = action_history.get("total", 0)
            failed = action_history.get("failed", 0)
            rate = (total_actions - failed) / total_actions if total_actions > 0 else 1.0
            kpis.append(BusinessKPI(
                kpi_type=BusinessKPIType.RELIABILITY,
                name="reliability",
                value=rate,
                confidence=0.8,
                unit="score",
            ))

        tool_stats = sources.get("tool_stats", {})
        if tool_stats:
            rates = [s.get("success_rate", 1.0) for s in tool_stats.values() if isinstance(s, dict)]
            avg_rate = sum(rates) / len(rates) if rates else 1.0
            kpis.append(BusinessKPI(
                kpi_type=BusinessKPIType.COVERAGE,
                name="tool_coverage",
                value=avg_rate,
                confidence=0.75,
                unit="score",
            ))

        return kpis
