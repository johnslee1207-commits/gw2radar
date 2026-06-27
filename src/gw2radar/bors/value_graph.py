from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValueNode:
    node_id: str
    node_type: str
    value: float = 0.0
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValueEdge:
    source_id: str
    target_id: str
    weight: float = 1.0
    label: str = ""


class ValueGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, ValueNode] = {}
        self._edges: list[ValueEdge] = []

    def build(self, entities: list | None = None,
              kpis: list | None = None,
              risks: list | None = None) -> None:
        self._nodes.clear()
        self._edges.clear()

        if entities:
            for entity in entities:
                eid = getattr(entity, "source_id", getattr(entity, "id", str(id(entity))))
                n = ValueNode(node_id=f"entity:{eid}", node_type="entity",
                              value=getattr(entity, "value", 0.0))
                self._nodes[n.node_id] = n

        if kpis:
            for kpi in kpis:
                kid = f"kpi:{getattr(kpi, 'name', getattr(kpi, 'kpi_type', 'unknown'))}"
                n = ValueNode(node_id=kid, node_type="kpi",
                              value=getattr(kpi, "value", 0.0))
                self._nodes[kid] = n

        if risks:
            for risk in risks:
                rid = f"risk:{getattr(risk, 'name', getattr(risk, 'risk_type', 'unknown'))}"
                n = ValueNode(node_id=rid, node_type="risk",
                              value=1.0 - getattr(risk, "score", 0.0))
                self._nodes[rid] = n

    def add_node(self, node: ValueNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: ValueEdge) -> None:
        if edge.source_id in self._nodes and edge.target_id in self._nodes:
            self._edges.append(edge)

    def propagate(self, node_id: str, depth: int = 3) -> list[dict]:
        visited: set[str] = set()
        paths: list[dict] = []

        def _walk(current_id: str, remaining: int, chain: list[str]) -> None:
            if remaining <= 0 or current_id in visited:
                return
            visited.add(current_id)
            chain = chain + [current_id]
            for edge in self._edges:
                if edge.source_id == current_id:
                    paths.append({
                        "path": " -> ".join(chain + [edge.target_id]),
                        "source": current_id,
                        "target": edge.target_id,
                        "edge_label": edge.label,
                        "weight": edge.weight,
                    })
                    _walk(edge.target_id, remaining - 1, chain)

        _walk(node_id, depth, [])
        return paths

    def impact_analysis(self, entity_id: str) -> dict:
        affected: list[dict] = []
        for edge in self._edges:
            if edge.source_id == entity_id:
                target_node = self._nodes.get(edge.target_id)
                affected.append({
                    "target_id": edge.target_id,
                    "target_type": target_node.node_type if target_node else "unknown",
                    "edge_label": edge.label,
                    "weight": edge.weight,
                })
        return {"entity_id": entity_id, "direct_impacts": affected,
                "impact_count": len(affected)}

    def path_to_decision(self, entity_id: str, target_kpi: str = "") -> list[dict]:
        results: list[dict] = []
        for edge in self._edges:
            if edge.source_id == entity_id:
                if not target_kpi or target_kpi in edge.target_id:
                    results.append({
                        "path": f"{entity_id} -> {edge.target_id}",
                        "source": entity_id,
                        "target": edge.target_id,
                    })
        return results
