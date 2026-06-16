from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.schemas import Evidence

MIN_STRONG_CONFIDENCE = 0.75
DEFAULT_STALE_AFTER = timedelta(days=7)
MOCK_STALE_AFTER = timedelta(days=3650)


@dataclass(frozen=True)
class EvidenceQuality:
    evidence_id: str
    confidence: float
    is_stale: bool
    is_low_confidence: bool
    source_type: str

    @property
    def reason_codes(self) -> list[str]:
        codes: list[str] = []
        if self.is_stale:
            codes.append("stale_evidence")
        if self.is_low_confidence:
            codes.append("low_confidence_evidence")
        return codes


@dataclass(frozen=True)
class EvidenceQualitySummary:
    qualities: list[EvidenceQuality]
    min_confidence: float
    has_stale: bool
    has_low_confidence: bool
    reason_codes: list[str]

    @property
    def confidence_label(self) -> str:
        if self.has_low_confidence:
            return "low"
        if self.min_confidence < 0.9:
            return "medium"
        return "high"


def evaluate_evidence_quality(
    graph: GraphData,
    evidence_refs: list[str],
    *,
    now: datetime | None = None,
) -> EvidenceQualitySummary:
    now = now or datetime.now(timezone.utc)
    qualities = [
        evaluate_evidence(graph.evidence[evidence_id], now=now)
        for evidence_id in evidence_refs
        if evidence_id in graph.evidence
    ]
    if not qualities:
        return EvidenceQualitySummary(
            qualities=[],
            min_confidence=0.0,
            has_stale=True,
            has_low_confidence=True,
            reason_codes=["missing_evidence", "low_confidence_evidence"],
        )

    min_confidence = min(quality.confidence for quality in qualities)
    has_stale = any(quality.is_stale for quality in qualities)
    has_low_confidence = any(quality.is_low_confidence for quality in qualities)
    reason_codes = sorted({code for quality in qualities for code in quality.reason_codes})
    return EvidenceQualitySummary(
        qualities=qualities,
        min_confidence=min_confidence,
        has_stale=has_stale,
        has_low_confidence=has_low_confidence,
        reason_codes=reason_codes,
    )


def evaluate_evidence(evidence: Evidence, *, now: datetime) -> EvidenceQuality:
    stale_after = MOCK_STALE_AFTER if evidence.source_type == "mock" else DEFAULT_STALE_AFTER
    fetched_at = evidence.fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return EvidenceQuality(
        evidence_id=evidence.id,
        confidence=evidence.confidence,
        is_stale=(now - fetched_at) > stale_after,
        is_low_confidence=evidence.confidence < MIN_STRONG_CONFIDENCE,
        source_type=evidence.source_type,
    )


def apply_evidence_quality_to_action(graph: GraphData, action):
    summary = evaluate_evidence_quality(graph, action.evidence_refs)
    reason_codes = list(dict.fromkeys([*action.reason_codes, *summary.reason_codes]))
    constraints = {
        **action.constraints,
        "evidence_confidence": summary.confidence_label,
        "evidence_stale": summary.has_stale,
    }
    properties = {
        **action.properties,
        "evidence_quality": {
            "confidence_label": summary.confidence_label,
            "min_confidence": summary.min_confidence,
            "has_stale": summary.has_stale,
            "has_low_confidence": summary.has_low_confidence,
        },
    }
    priority_score = action.priority_score
    urgency = action.urgency
    explanation = action.explanation
    if summary.has_low_confidence or summary.has_stale:
        priority_score = min(priority_score, 0.55)
        urgency = "low"
        explanation = f"{explanation} Evidence quality is {summary.confidence_label}; verify before acting."

    return action.model_copy(
        update={
            "priority_score": priority_score,
            "urgency": urgency,
            "reason_codes": reason_codes,
            "constraints": constraints,
            "properties": properties,
            "explanation": explanation,
        }
    )
