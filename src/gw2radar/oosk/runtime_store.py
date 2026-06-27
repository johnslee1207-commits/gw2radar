from datetime import datetime, timezone

from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.schemas import Entity, Evidence, PlayerState, Relation


class RuntimeStore:
    def __init__(self, graph: GraphData | None = None) -> None:
        self._graph = graph or GraphData()

    @property
    def graph(self) -> GraphData:
        return self._graph

    def add_entity(self, entity: Entity) -> Entity:
        return self._graph.add_entity(entity)

    def get_entity(self, eid: str) -> Entity | None:
        return self._graph.entities.get(eid)

    def search(self, query: str) -> list[Entity]:
        q = query.lower()
        return [
            e for e in self._graph.entities.values()
            if q in e.canonical_name.lower() or q in e.id.lower()
        ]

    def trace(self, eid: str, depth: int = 3) -> dict:
        visited: set[str] = set()

        def _walk(current_id: str, remaining: int, rels_in: list[dict]) -> list[dict]:
            if remaining <= 0 or current_id in visited:
                return rels_in
            visited.add(current_id)
            for r in self._graph.find_relations(subject_id=current_id):
                rels_in.append({
                    "direction": "outgoing",
                    "predicate": r.predicate.value,
                    "target_id": r.object_id,
                    "target_name": self._graph.entity_name(r.object_id),
                })
                _walk(r.object_id, remaining - 1, rels_in)
            for r in self._graph.find_relations(object_id=current_id):
                rels_in.append({
                    "direction": "incoming",
                    "predicate": r.predicate.value,
                    "source_id": r.subject_id,
                    "source_name": self._graph.entity_name(r.subject_id),
                })
                _walk(r.subject_id, remaining - 1, rels_in)
            return rels_in

        return {"entity_id": eid, "entity_name": self._graph.entity_name(eid), "relations": _walk(eid, depth, [])}

    def add_relation(self, relation: Relation) -> Relation:
        return self._graph.add_relation(relation)

    def get_neighbors(self, eid: str) -> list[Relation]:
        subjects = self._graph.find_relations(subject_id=eid)
        objects = self._graph.find_relations(object_id=eid)
        seen: dict[str, Relation] = {}
        for r in subjects + objects:
            seen[r.id] = r
        return list(seen.values())

    def add_evidence(self, evidence: Evidence) -> Evidence:
        return self._graph.add_evidence(evidence)

    def add_player_state(self, state: PlayerState) -> PlayerState:
        return self._graph.add_player_state(state)

    def register_from_domain_graph(self, registry: dict) -> None:
        for dtype in registry.get("domain_types", []):
            entity = Entity(
                id=f"type:{dtype}",
                type=None,
                canonical_name=dtype,
                properties={"domain_type": True},
            )
            self._graph.add_entity(entity)
