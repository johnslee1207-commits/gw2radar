from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class BusinessEntityType(str, Enum):
    QUALITY_SCORE = "QualityScore"
    COMPLIANCE_VALUE = "ComplianceValue"
    EVIDENCE_VALUE = "EvidenceValue"
    PUBLISHABILITY = "Publishability"
    CALIBRATION_CREDIBILITY = "CalibrationCredibility"
    SIMULATION_COST = "SimulationCost"
    REPORT_VALUE = "ReportValue"


@dataclass
class BusinessEntity:
    entity_type: BusinessEntityType
    source_id: str
    value: float = 0.0
    confidence: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)


def entity_factory(
    entity_type: BusinessEntityType,
    source_id: str,
    value: float = 0.0,
    **kwargs: Any,
) -> BusinessEntity:
    return BusinessEntity(
        entity_type=entity_type,
        source_id=source_id,
        value=value,
        confidence=kwargs.pop("confidence", 1.0),
        properties=kwargs,
    )
