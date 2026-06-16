from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb.kb_entity_linker import validate_article_links
from gw2radar.kb.kb_explanation import explain_actions_with_kb
from gw2radar.kb.kb_markdown_loader import load_markdown_directory
from gw2radar.kb.kb_models import KnowledgeArticleInput, KnowledgeDomain, SourceRegistryInput, SourceType
from gw2radar.kb.kb_report_quality import score_kb_report_quality
from gw2radar.kb.kb_repository import (
    create_article,
    deprecate_article,
    enable_rule,
    get_article,
    get_source,
    list_articles,
    list_sources,
    list_rules,
    register_source,
    review_article,
    search_articles,
)
from gw2radar.kb.kb_rule_distiller import distill_rule_from_article
from gw2radar.kb.patch_impact_review import (
    PatchImpactReviewInput,
    build_patch_rule_candidates,
    list_patch_impact_drafts,
    list_pending_patch_impact_drafts,
    persist_patch_rule_candidates,
    save_patch_impact_review,
)
from gw2radar.inference.action_generator import generate_actions

router = APIRouter(prefix="/api/v1/kb", tags=["kb"])


class LoadDirectoryRequest(BaseModel):
    directory: str = "docs/knowledge_base"


class ConfirmPatchRulePersistenceRequest(BaseModel):
    confirmed: bool = False


class EnableKnowledgeRuleRequest(BaseModel):
    confirmed_reviewed: bool = False


@router.post("/sources", response_model=ApiDataEnvelope)
def post_kb_source(request: SourceRegistryInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = register_source(session, request)
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.get("/sources", response_model=ApiDataEnvelope)
def get_kb_sources(source_type: SourceType | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        sources = [
            source.model_dump(mode="json")
            for source in list_sources(session, source_type.value if source_type else None)
        ]
    return ApiDataEnvelope(data={"sources": sources})


@router.get("/sources/{source_id}", response_model=ApiDataEnvelope)
def get_kb_source(source_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        source = get_source(session, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Knowledge source not found.")
    return ApiDataEnvelope(data={"source": source.model_dump(mode="json")})


@router.post("/load-directory", response_model=ApiDataEnvelope)
def post_kb_load_directory(request: LoadDirectoryRequest) -> ApiDataEnvelope:
    init_db()
    directory = Path(request.directory)
    with db_session.SessionLocal() as session:
        try:
            articles = [article.model_dump(mode="json") for article in load_markdown_directory(session, directory)]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"loaded_count": len(articles), "articles": articles})


@router.post("/articles", response_model=ApiDataEnvelope)
def post_kb_article(request: KnowledgeArticleInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = create_article(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.get("/articles", response_model=ApiDataEnvelope)
def get_kb_articles(domain: KnowledgeDomain | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        articles = [article.model_dump(mode="json") for article in list_articles(session, domain)]
    return ApiDataEnvelope(data={"articles": articles})


@router.get("/articles/{kb_id}", response_model=ApiDataEnvelope)
def get_kb_article(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/review", response_model=ApiDataEnvelope)
def post_kb_article_review(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = review_article(session, kb_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/deprecate", response_model=ApiDataEnvelope)
def post_kb_article_deprecate(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            article = deprecate_article(session, kb_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"article": article.model_dump(mode="json")})


@router.post("/articles/{kb_id}/validate-links", response_model=ApiDataEnvelope)
def post_kb_article_validate_links(kb_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
    if article is None:
        raise HTTPException(status_code=404, detail="Knowledge article not found.")
    result = validate_article_links(article, graph)
    return ApiDataEnvelope(data={"validation": result.model_dump(mode="json")})


@router.post("/articles/{kb_id}/distill-rule", response_model=ApiDataEnvelope)
def post_kb_article_distill_rule(kb_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        article = get_article(session, kb_id)
        if article is None:
            raise HTTPException(status_code=404, detail="Knowledge article not found.")
        try:
            rule = distill_rule_from_article(session, article)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"rule": rule.model_dump(mode="json")})


@router.get("/search", response_model=ApiDataEnvelope)
def get_kb_search(q: str, domain: KnowledgeDomain | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        articles = [article.model_dump(mode="json") for article in search_articles(session, q, domain)]
    return ApiDataEnvelope(data={"articles": articles})


@router.get("/patch-impact/drafts", response_model=ApiDataEnvelope)
def get_patch_impact_drafts(year: int | None = None, pending_only: bool = False) -> ApiDataEnvelope:
    drafts = (
        list_pending_patch_impact_drafts(year=year)
        if pending_only
        else list_patch_impact_drafts(year=year)
    )
    return ApiDataEnvelope(
        data={
            "count": len(drafts),
            "drafts": [draft.model_dump(mode="json") for draft in drafts],
        }
    )


@router.post("/patch-impact/reviews", response_model=ApiDataEnvelope)
def post_patch_impact_review(request: PatchImpactReviewInput) -> ApiDataEnvelope:
    try:
        review = save_patch_impact_review(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"review": review.model_dump(mode="json")})


@router.get("/patch-impact/{patch_id}/rule-candidates", response_model=ApiDataEnvelope)
def get_patch_impact_rule_candidates(patch_id: str) -> ApiDataEnvelope:
    try:
        candidate = build_patch_rule_candidates(patch_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={
            "patch_id": candidate.patch_id,
            "rules": [rule.model_dump(mode="json") for rule in candidate.rules],
        }
    )


@router.post("/patch-impact/{patch_id}/rule-candidates/persist", response_model=ApiDataEnvelope)
def post_patch_impact_rule_candidates_persist(
    patch_id: str,
    request: ConfirmPatchRulePersistenceRequest,
) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            result = persist_patch_rule_candidates(session, patch_id, confirmed=request.confirmed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(
        data={
            "patch_id": result.patch_id,
            "created_count": result.created_count,
            "skipped_existing_count": result.skipped_existing_count,
            "rules": [rule.model_dump(mode="json") for rule in result.rules],
        }
    )


@router.post("/rules/{rule_id}/enable", response_model=ApiDataEnvelope)
def post_kb_rule_enable(rule_id: str, request: EnableKnowledgeRuleRequest) -> ApiDataEnvelope:
    if not request.confirmed_reviewed:
        raise HTTPException(status_code=400, detail="Enabling a KnowledgeRule requires reviewed confirmation.")
    init_db()
    with db_session.SessionLocal() as session:
        try:
            rule = enable_rule(session, rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"rule": rule.model_dump(mode="json")})


@router.get("/goals/{goal_id}/action-explanations", response_model=ApiDataEnvelope)
def get_kb_action_explanations(goal_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    explanations = explain_actions_with_kb(actions, rules)
    return ApiDataEnvelope(
        data={
            "goal_id": goal_id,
            "explanations": {
                action_id: [item.model_dump(mode="json") for item in items]
                for action_id, items in explanations.items()
            },
        }
    )


@router.get("/goals/{goal_id}/report-quality", response_model=ApiDataEnvelope)
def get_kb_report_quality(goal_id: str) -> ApiDataEnvelope:
    graph = get_graph()
    if goal_id not in graph.entities:
        raise HTTPException(status_code=404, detail="Goal not found")
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    init_db()
    with db_session.SessionLocal() as session:
        rules = list_rules(session)
    explanations = explain_actions_with_kb(actions, rules)
    quality = score_kb_report_quality(actions, rules, explanations)
    return ApiDataEnvelope(data={"goal_id": goal_id, "quality": quality.model_dump(mode="json")})
