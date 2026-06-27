from dataclasses import dataclass, field
from datetime import datetime, timezone

from gw2radar.bors.decision_engine import Decision, DecisionRecord


@dataclass
class DecisionNode:
    decision_id: str
    decision_type: str
    decision: Decision
    score: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_id: str | None = None
    context: dict = field(default_factory=dict)


@dataclass
class DecisionEdge:
    from_id: str
    to_id: str
    relation: str = "depends_on"


class DecisionGraph:
    def __init__(self) -> None:
        self._nodes: dict[str, DecisionNode] = {}
        self._edges: list[DecisionEdge] = []

    def add_decision(self, record: DecisionRecord, decision_id: str = "",
                     decision_type: str = "", parent_id: str | None = None) -> DecisionNode:
        did = decision_id or f"dec:{len(self._nodes)}"
        node = DecisionNode(
            decision_id=did,
            decision_type=decision_type or record.decision.value,
            decision=record.decision,
            score=record.score,
            parent_id=parent_id,
            context={"reason": record.reason, "factor_count": len(record.factors)},
        )
        self._nodes[did] = node
        if parent_id and parent_id in self._nodes:
            self._edges.append(DecisionEdge(from_id=parent_id, to_id=did))
        return node

    def trace(self, decision_id: str) -> list[dict]:
        chain: list[dict] = []
        current_id: str | None = decision_id
        depth = 0
        while current_id and depth < 50:
            node = self._nodes.get(current_id)
            if not node:
                break
            chain.append({
                "decision_id": node.decision_id,
                "decision_type": node.decision_type,
                "decision": node.decision.value,
                "score": node.score,
                "reason": node.context.get("reason", ""),
                "timestamp": node.timestamp.isoformat(),
            })
            current_id = node.parent_id
            depth += 1
        return chain

    def upstream_dependencies(self, decision_id: str) -> list[DecisionNode]:
        dependents: list[DecisionNode] = []
        for edge in self._edges:
            if edge.to_id == decision_id:
                node = self._nodes.get(edge.from_id)
                if node:
                    dependents.append(node)
        return dependents

    def downstream_dependents(self, decision_id: str) -> list[DecisionNode]:
        affected: list[DecisionNode] = []
        for edge in self._edges:
            if edge.from_id == decision_id:
                node = self._nodes.get(edge.to_id)
                if node:
                    affected.append(node)
        return affected

    def impact_of_reversal(self, decision_id: str) -> dict:
        downstream = self.downstream_dependents(decision_id)
        chain = self.trace(decision_id)
        return {
            "target": decision_id,
            "direct_downstream": len(downstream),
            "downstream_ids": [n.decision_id for n in downstream],
            "decision_chain": chain,
        }

    def all_decisions(self) -> list[DecisionNode]:
        return list(self._nodes.values())
