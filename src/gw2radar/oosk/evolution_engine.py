from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvolutionProposal:
    proposal_type: str
    description: str
    trigger: str
    confidence: float = 0.5
    details: dict[str, Any] = field(default_factory=dict)


class EvolutionEngine:
    def __init__(self) -> None:
        self._low_success_threshold = 0.3

    def evolve(self, runtime_snapshot: dict[str, Any]) -> list[EvolutionProposal]:
        proposals: list[EvolutionProposal] = []
        tool_stats = runtime_snapshot.get("tool_stats", {})
        for tool_name, stats in tool_stats.items():
            rate = stats.get("success_rate", 1.0)
            if isinstance(rate, (int, float)) and rate < self._low_success_threshold:
                proposals.append(EvolutionProposal(
                    proposal_type="tool_repair",
                    description=f"Tool '{tool_name}' has low success rate ({rate:.0%}). Recommend repair.",
                    trigger=f"success_rate={rate:.2f}",
                    confidence=1.0 - rate,
                ))

        action_history = runtime_snapshot.get("action_history", [])
        type_counts: dict[str, int] = {}
        for action in action_history:
            atype = action.get("action_type", action.get("type", "unknown"))
            type_counts[atype] = type_counts.get(atype, 0) + 1
        for atype, count in type_counts.items():
            if count >= 5:
                proposals.append(EvolutionProposal(
                    proposal_type="index_suggestion",
                    description=f"Action type '{atype}' used {count} times. Consider adding dedicated index.",
                    trigger=f"usage_count={count}",
                    confidence=min(count / 20, 0.95),
                ))

        return proposals
