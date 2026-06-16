from fastapi import APIRouter, HTTPException

from gw2radar.api.state import get_graph, save_graph
from gw2radar.inference.action_generator import generate_actions

router = APIRouter()


@router.post("/goals/{goal_id}/actions/generate")
def post_generate_actions(goal_id: str) -> list[dict]:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    actions = generate_actions(graph, goal_id)
    save_graph(graph)
    return [action.model_dump(mode="json") for action in actions]
