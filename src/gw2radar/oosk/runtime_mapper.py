from gw2radar.domain_graph.domain_schema import DomainGraph
from gw2radar.graph.graph_query import GraphData
from gw2radar.oosk.runtime_store import RuntimeStore
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, FreshnessStatus, QAStatus, Relation


class RuntimeMapper:
    _ENTITY_MAP: dict[str, EntityType] = {
        "Account": EntityType.ACCOUNT,
        "Item": EntityType.ITEM,
        "Goal": EntityType.GOAL,
        "Character": EntityType.CHARACTER,
        "Recipe": EntityType.RECIPE,
        "Currency": EntityType.CURRENCY,
        "Achievement": EntityType.ACHIEVEMENT,
        "Collection": EntityType.COLLECTION,
        "Evidence": EntityType.EVIDENCE,
        "Material": EntityType.MATERIAL,
        "Task": EntityType.TASK,
        "Action": EntityType.ACTION,
    }

    _RELATION_MAP: dict[str, RelationType] = {
        "requires": RelationType.REQUIRES,
        "consumes": RelationType.CONSUMES,
        "produces": RelationType.PRODUCES,
        "used_in": RelationType.USED_IN,
        "unlocks": RelationType.UNLOCKS,
        "part_of": RelationType.PART_OF,
        "owned_by": RelationType.OWNED_BY,
        "has_price": RelationType.HAS_PRICE,
        "missing_for_goal": RelationType.MISSING_FOR_GOAL,
        "advances_goal": RelationType.ADVANCES_GOAL,
        "blocks_goal": RelationType.BLOCKS_GOAL,
        "reserves_for_goal": RelationType.RESERVES_FOR_GOAL,
        "reserved_for_goal": RelationType.RESERVED_FOR_GOAL,
        "acquired_by": RelationType.ACQUIRED_BY,
        "required_by": RelationType.REQUIRES,
        "depends_on": RelationType.REQUIRES,
        "holds": RelationType.OWNED_BY,
        "generates": RelationType.PRODUCES,
        "compiles_to": RelationType.PART_OF,
        "executed_by": RelationType.REQUIRES,
        "evidenced_by": RelationType.REQUIRES,
        "cites": RelationType.REQUIRES,
    }

    def map_domain_to_store(self, dg: DomainGraph, store: RuntimeStore) -> None:
        for ntype, nd in dg.nodes.items():
            entity_type = self._ENTITY_MAP.get(ntype)
            if entity_type is None:
                continue
            entity = Entity(
                id=f"dg:{ntype}",
                type=entity_type,
                canonical_name=ntype,
                graph_layer=GraphLayer.PUBLIC_GAME,
                properties={p.name: None for p in nd.properties},
                freshness_status=FreshnessStatus.UNKNOWN,
                qa_status=QAStatus.UNTESTED,
            )
            store.add_entity(entity)

        for etype, ed in dg.edges.items():
            predicate = self._RELATION_MAP.get(etype, RelationType.REQUIRES)
            for src in ed.source_types:
                src_id = f"dg:{src}"
                for tgt in ed.target_types:
                    tgt_id = f"dg:{tgt}"
                    relation = Relation(
                        id=f"dg_edge:{src}:{etype}:{tgt}",
                        subject_id=src_id,
                        predicate=predicate,
                        object_id=tgt_id,
                        graph_layer=GraphLayer.PUBLIC_GAME,
                        properties={"relation_type": etype, "cardinality": ed.cardinality},
                    )
                    store.add_relation(relation)

    def extract_runtime_state(self, graph: GraphData) -> dict:
        return {
            "entities": list(graph.entities.values()),
            "relations": list(graph.relations),
            "action_history": list(graph.actions),
            "evidence": list(graph.evidence.values()),
            "player_state": list(graph.player_state),
        }

    def _resolve_entity_type(self, domain_type: str) -> EntityType | None:
        return self._ENTITY_MAP.get(domain_type)
