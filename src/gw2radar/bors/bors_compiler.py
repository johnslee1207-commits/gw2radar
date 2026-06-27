from typing import Any

from gw2radar.bors.business_entity import BusinessEntity, BusinessEntityType, entity_factory
from gw2radar.domain_graph.domain_schema import DomainGraph


from gw2radar.ontology.entity_types import EntityType as OSKEntityType

_MAPPING: dict[str, BusinessEntityType] = {
    "ExecutionRun": BusinessEntityType.SIMULATION_COST,
    "Evidence": BusinessEntityType.EVIDENCE_VALUE,
    "CalibrationCase": BusinessEntityType.CALIBRATION_CREDIBILITY,
    "Report": BusinessEntityType.REPORT_VALUE,
    "Run": BusinessEntityType.PUBLISHABILITY,
    "QualityGate": BusinessEntityType.QUALITY_SCORE,
    "ComplianceReport": BusinessEntityType.COMPLIANCE_VALUE,
    # EntityType enum values (lowercase):
    OSKEntityType.EVIDENCE.value: BusinessEntityType.EVIDENCE_VALUE,
    OSKEntityType.GOAL.value: BusinessEntityType.PUBLISHABILITY,
}


class BORSCompiler:
    def __init__(self, mapping: dict[str, BusinessEntityType] | None = None) -> None:
        self._mapping = {**_MAPPING, **(mapping or {})}

    def compile_one(self, oosk_entity: Any) -> BusinessEntity | None:
        entity_type_str = ""
        if hasattr(oosk_entity, "type"):
            t = oosk_entity.type
            entity_type_str = t.value if hasattr(t, "value") else str(t)
        elif hasattr(oosk_entity, "entity_type"):
            entity_type_str = oosk_entity.entity_type.value if hasattr(oosk_entity.entity_type, "value") else str(oosk_entity.entity_type)
        bors_type = self._mapping.get(entity_type_str)
        if not bors_type:
            return None
        return entity_factory(
            entity_type=bors_type,
            source_id=getattr(oosk_entity, "id", str(id(oosk_entity))),
            value=1.0,
        )

    def compile_all(self, entities: list) -> list[BusinessEntity]:
        results: list[BusinessEntity] = []
        for e in entities:
            compiled = self.compile_one(e)
            if compiled:
                results.append(compiled)
        return results

    def compile_from_mapping(self, runtime_mapping: dict) -> list[BusinessEntity]:
        results: list[BusinessEntity] = []
        for domain_type, bors_type_str in runtime_mapping.items():
            try:
                bors_type = BusinessEntityType(bors_type_str)
            except ValueError:
                continue
            results.append(entity_factory(
                entity_type=bors_type,
                source_id=f"domain:{domain_type}",
                value=1.0,
            ))
        return results
