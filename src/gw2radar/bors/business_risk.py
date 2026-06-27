from dataclasses import dataclass, field
from enum import Enum


class BusinessRiskType(str, Enum):
    QUALITY = "quality_risk"
    COMPLIANCE = "compliance_risk"
    EVIDENCE = "evidence_risk"
    STABILITY = "stability_risk"
    CALIBRATION = "calibration_risk"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BusinessRisk:
    risk_type: BusinessRiskType
    name: str
    level: RiskLevel = RiskLevel.NONE
    score: float = 0.0
    confidence: float = 1.0
    contributing_factors: list[str] = field(default_factory=list)
    mitigation: str = ""


class BusinessRiskModel:
    def assess_all(self, **sources: dict) -> list[BusinessRisk]:
        risks: list[BusinessRisk] = []

        qa_gate = sources.get("qa_gate", {})
        if qa_gate:
            passed = qa_gate.get("passed", 0)
            total = qa_gate.get("total", 1)
            fail_rate = 1.0 - (passed / total if total > 0 else 1.0)
            if fail_rate > 0.5:
                level, score = RiskLevel.HIGH, fail_rate
            elif fail_rate > 0.2:
                level, score = RiskLevel.MEDIUM, fail_rate
            elif fail_rate > 0:
                level, score = RiskLevel.LOW, fail_rate
            else:
                level, score = RiskLevel.NONE, 0.0
            risks.append(BusinessRisk(
                risk_type=BusinessRiskType.QUALITY,
                name="quality_risk",
                level=level,
                score=score,
                contributing_factors=qa_gate.get("failures", []) if isinstance(qa_gate.get("failures"), list) else [],
                mitigation="Review QA failures and re-run checks",
            ))

        compliance = sources.get("compliance", {})
        if compliance:
            failures = compliance.get("failures", []) if isinstance(compliance.get("failures"), list) else []
            if failures:
                risks.append(BusinessRisk(
                    risk_type=BusinessRiskType.COMPLIANCE,
                    name="compliance_risk",
                    level=RiskLevel.HIGH if len(failures) > 2 else RiskLevel.MEDIUM,
                    score=min(len(failures) * 0.3, 1.0),
                    contributing_factors=failures,
                    mitigation="Resolve all compliance violations before proceeding",
                ))

        evidence = sources.get("evidence", {})
        if evidence:
            chain_intact = evidence.get("chain_intact", True)
            if not chain_intact:
                risks.append(BusinessRisk(
                    risk_type=BusinessRiskType.EVIDENCE,
                    name="evidence_risk",
                    level=RiskLevel.CRITICAL,
                    score=1.0,
                    contributing_factors=["Evidence chain is broken"],
                    mitigation="Re-bind evidence chain before publishing",
                ))

        action_history = sources.get("action_history", {})
        if action_history:
            total = action_history.get("total", 0)
            failed = action_history.get("failed", 0)
            if total > 0 and failed / total > 0.3:
                risks.append(BusinessRisk(
                    risk_type=BusinessRiskType.STABILITY,
                    name="stability_risk",
                    level=RiskLevel.HIGH if failed / total > 0.5 else RiskLevel.MEDIUM,
                    score=failed / total,
                    contributing_factors=[f"{failed}/{total} actions failed"],
                    mitigation="Investigate recurring action failures",
                ))

        return risks
