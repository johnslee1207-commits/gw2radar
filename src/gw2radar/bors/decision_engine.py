from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    REVIEW = "review"
    CERTIFY = "certify"
    DEFER = "defer"
    PENDING_EVIDENCE = "pending_evidence"


@dataclass
class DecisionFactor:
    name: str
    value: float
    weight: float = 1.0
    impact: str = "positive"
    detail: str = ""


@dataclass
class DecisionRecord:
    decision: Decision
    score: float
    confidence: float = 1.0
    factors: list[DecisionFactor] = field(default_factory=list)
    reason: str = ""


class DecisionEngine:
    def __init__(self, threshold: float = 0.6, evidence_threshold: float = 0.7) -> None:
        self._threshold = threshold
        self._evidence_threshold = evidence_threshold

    def decide(
        self,
        decision_type: str,
        kpis: list | None = None,
        risks: list | None = None,
        entities: list | None = None,
    ) -> DecisionRecord:
        kpis = kpis or []
        risks = risks or []
        entities = entities or []
        factors: list[DecisionFactor] = []

        for kpi in kpis:
            value = getattr(kpi, "value", 0.0)
            factors.append(DecisionFactor(
                name=f"kpi:{getattr(kpi, 'name', 'unknown')}",
                value=float(value),
                weight=0.25,
                impact="positive",
                detail=f"{getattr(kpi, 'name', '')} = {value:.2f}",
            ))

        has_critical_evidence_gap = False
        for risk in risks:
            score = getattr(risk, "score", 0.0)
            risk_name = getattr(risk, "name", "unknown")
            risk_type = getattr(risk, "risk_type", "")
            inverse = 1.0 - float(score)
            factors.append(DecisionFactor(
                name=f"risk:{risk_name}",
                value=inverse,
                weight=0.25,
                impact="negative" if float(score) > 0.3 else "positive",
                detail=f"{risk_name} = {float(score):.2f}",
            ))
            if risk_type in ("evidence_risk", "calibration_risk") and float(score) > 0.5:
                has_critical_evidence_gap = True

        for entity in entities:
            value = getattr(entity, "value", 0.0)
            factors.append(DecisionFactor(
                name=f"entity:{getattr(entity, 'entity_type', 'unknown')}",
                value=float(value),
                weight=0.2,
                impact="positive",
                detail=f"{getattr(entity, 'entity_type', '')} value = {float(value):.2f}",
            ))

        if not factors:
            return DecisionRecord(
                decision=Decision.DEFER,
                score=0.0,
                confidence=0.0,
                reason="No decision factors available (score=0.00 < 0.60)",
            )

        total_weight = sum(f.weight for f in factors)
        score = sum(f.value * f.weight for f in factors) / total_weight if total_weight > 0 else 0.0
        score = min(max(score, 0.0), 1.0)

        evidence_factor = next(
            (f for f in factors if "evidence" in f.name.lower() or "calibration" in f.name.lower()),
            None,
        )
        if has_critical_evidence_gap or (
            evidence_factor and evidence_factor.value < self._evidence_threshold
            and score < self._threshold
        ):
            decision = Decision.PENDING_EVIDENCE
            reason = (
                f"Evidence gap detected (evidence_score={evidence_factor.value if evidence_factor else 0.0:.2f}); "
                f"need more evidence before decision (score={score:.2f})"
            )
        elif score >= self._threshold:
            blocking = [f for f in factors if f.impact == "negative" and f.value < 0.5]
            if blocking:
                decision = Decision.REVIEW
                reason = f"Score adequate but negative factors present (score={score:.2f})"
            else:
                decision = Decision.APPROVE
                reason = f"All gates passed (score={score:.2f} >= {self._threshold:.2f})"
        else:
            decision = Decision.REJECT
            blocking = [f for f in factors if f.value < 0.5]
            blocking_names = "; ".join(f.name for f in blocking[:3])
            reason = f"Insufficient score (score={score:.2f} < {self._threshold:.2f}); blocking: {blocking_names}"

        confidence = sum(f.value for f in factors) / len(factors) if factors else 0.0
        return DecisionRecord(
            decision=decision,
            score=score,
            confidence=min(confidence, 1.0),
            factors=factors,
            reason=reason,
        )
