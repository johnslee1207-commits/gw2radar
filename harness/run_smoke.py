#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.action_types import ActionType
from gw2radar.reports.markdown_report import generate_markdown_report


def main() -> int:
    graph = build_mock_graph()
    gap = calculate_goal_gap(graph, "gw2:goal:aurora")
    actions = generate_actions(graph, "gw2:goal:aurora")
    report = generate_markdown_report(graph, "gw2:goal:aurora")

    checks = [
        gap.goal_name == "Aurora",
        any(item.entity_id == "gw2:item:mystic_coin" for item in gap.completed_requirements),
        any(item.entity_id == "gw2:item:mystic_clover" for item in gap.missing_requirements),
        any(action.action_type == ActionType.DO_DAILY for action in actions),
        any(action.action_type == ActionType.COMPLETE_ACHIEVEMENT for action in actions),
        all(action.explanation for action in actions),
        "## Active Goal" in report,
        "## Missing Requirements" in report,
        "## Recommended Actions Today" in report,
    ]
    if not all(checks):
        print("FAIL: GW2Radar MVP 0.1 smoke harness checks failed")
        return 1
    print("PASS: GW2Radar MVP 0.1 mock legendary goal loop succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
