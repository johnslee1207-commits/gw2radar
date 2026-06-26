from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph, save_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.action_registry import (
    ActionPreconditionError,
    generate_do_not_sell,
    generate_legendary_plan,
    list_registry,
    reserve_material_for_goal,
)
from gw2radar.ontology.impact_analyzer import (
    analyze_build_source_stale,
    analyze_goal_change,
    analyze_report_publish,
    analyze_sell_item,
)
from gw2radar.ontology.mappers import (
    enrich_account_entities,
    enrich_evidence_entities,
    enrich_goal_entities,
    enrich_report_entities,
)
from gw2radar.ontology.ontology_qa import run_qa_suite

router = APIRouter(prefix="/api/v1/ontology", tags=["ontology"])


class ReserveRequest(BaseModel):
    item_id: str
    goal_id: str
    quantity: float


class GoalRequest(BaseModel):
    goal_id: str = "gw2:goal:aurora"


@router.post("/enrich", response_model=ApiDataEnvelope)
def post_ontology_enrich() -> ApiDataEnvelope:
    graph = get_graph()
    enrich_account_entities(graph)
    enrich_goal_entities(graph)
    enrich_evidence_entities(graph)
    save_graph(graph)
    return ApiDataEnvelope(data={"status": "enriched", "entity_count": len(graph.entities)})


@router.post("/impact/sell-item", response_model=ApiDataEnvelope)
def post_impact_sell_item(item_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    report = analyze_sell_item(graph, item_id)
    return ApiDataEnvelope(data={
        "impact": {
            "target": report.target,
            "operation": report.operation,
            "risk": report.risk,
            "affected_goals": report.affected_goals,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }
    })


@router.post("/impact/goal-change", response_model=ApiDataEnvelope)
def post_impact_goal_change(goal_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    report = analyze_goal_change(graph, goal_id)
    return ApiDataEnvelope(data={
        "impact": {
            "target": report.target,
            "operation": report.operation,
            "risk": report.risk,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }
    })


@router.post("/impact/build-stale", response_model=ApiDataEnvelope)
def post_impact_build_stale(build_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    report = analyze_build_source_stale(graph, build_id)
    return ApiDataEnvelope(data={
        "impact": {
            "target": report.target,
            "operation": report.operation,
            "risk": report.risk,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }
    })


@router.post("/impact/report-publish", response_model=ApiDataEnvelope)
def post_impact_report_publish(report_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    report = analyze_report_publish(graph, report_id)
    return ApiDataEnvelope(data={
        "impact": {
            "target": report.target,
            "operation": report.operation,
            "risk": report.risk,
            "warnings": report.warnings,
            "recommendations": report.recommendations,
        }
    })


@router.post("/action/reserve", response_model=ApiDataEnvelope)
def post_action_reserve(request: ReserveRequest) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        try:
            effect = reserve_material_for_goal(
                graph, session,
                item_id=request.item_id,
                goal_id=request.goal_id,
                quantity=request.quantity,
            )
            save_graph(graph)
            return ApiDataEnvelope(data={
                "action": "reserve_material_for_goal",
                "effect": effect.description,
                "affected_entities": effect.affected_entity_ids,
            })
        except (ActionPreconditionError, Exception) as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("/action/do-not-sell", response_model=ApiDataEnvelope)
def post_action_do_not_sell(request: GoalRequest) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        try:
            effect = generate_do_not_sell(graph, session, request.goal_id)
            save_graph(graph)
            return ApiDataEnvelope(data={
                "action": "generate_do_not_sell",
                "effect": effect.description,
            })
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.post("/action/legendary-plan", response_model=ApiDataEnvelope)
def post_action_legendary_plan(request: GoalRequest) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        try:
            effect = generate_legendary_plan(graph, session, request.goal_id)
            save_graph(graph)
            return ApiDataEnvelope(data={
                "action": "generate_legendary_plan",
                "effect": effect.description,
            })
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc))


@router.get("/registry", response_model=ApiDataEnvelope)
def get_ontology_registry() -> ApiDataEnvelope:
    registry = list_registry()
    data = {}
    for key, entry in registry.items():
        data[key] = {
            "title": entry.title,
            "description": entry.description,
            "preconditions": entry.preconditions,
            "effects": entry.effects,
            "qa_hooks": entry.qa_hooks,
            "privacy_policy": entry.privacy_policy,
        }
    return ApiDataEnvelope(data={"registry": data})


@router.post("/qa", response_model=ApiDataEnvelope)
def post_ontology_qa(checks: str | None = None) -> ApiDataEnvelope:
    graph = get_graph()
    check_list = checks.split(",") if checks else None
    suite = run_qa_suite(graph, checks=check_list)
    return ApiDataEnvelope(data={
        "qa": {
            "passed": suite.passed,
            "summary": suite.summary(),
            "checks": [
                {"name": r.check_name, "passed": r.passed, "message": r.message, "severity": r.severity}
                for r in suite.results
            ],
        }
    })


@router.post("/query/relations", response_model=ApiDataEnvelope)
def post_query_relations(subject_id: str | None = None, predicate: str | None = None, object_id: str | None = None) -> ApiDataEnvelope:
    from gw2radar.ontology.relation_types import RelationType
    graph = get_graph()
    pred = RelationType(predicate) if predicate else None
    relations = graph.find_relations(subject_id=subject_id, predicate=pred, object_id=object_id)
    return ApiDataEnvelope(data={
        "relations": [
            {"id": r.id, "subject_id": r.subject_id, "predicate": r.predicate.value, "object_id": r.object_id}
            for r in relations
        ],
        "count": len(relations),
    })
