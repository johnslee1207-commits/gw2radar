from fastapi import APIRouter, HTTPException

from gw2radar.api.state import get_graph
from gw2radar.commercial.legendary_planner import ensure_legendary_goal_catalog
from gw2radar.inference.goal_gap import calculate_goal_gap

router = APIRouter()


@router.get("/goals")
def get_goals() -> list[dict]:
    graph = get_graph()
    ensure_legendary_goal_catalog(graph)
    return [
        {
            "id": goal.id,
            "name": goal.canonical_name,
            "goal_type": goal.properties.get("goal_type"),
        }
        for goal in graph.goals()
    ]


@router.get("/goals/{goal_id}/gap")
def get_goal_gap(goal_id: str) -> dict:
    graph = get_graph()
    ensure_legendary_goal_catalog(graph)
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    return calculate_goal_gap(graph, goal_id).model_dump(mode="json")
