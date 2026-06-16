from fastapi import APIRouter, HTTPException

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.kb.kb_models import KnowledgeArticleInput, KnowledgeDomain
from gw2radar.kb.kb_repository import (
    create_article,
    deprecate_article,
    get_article,
    list_articles,
    review_article,
    search_articles,
)

router = APIRouter(prefix="/api/v1/kb", tags=["kb"])


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


@router.get("/search", response_model=ApiDataEnvelope)
def get_kb_search(q: str, domain: KnowledgeDomain | None = None) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        articles = [article.model_dump(mode="json") for article in search_articles(session, q, domain)]
    return ApiDataEnvelope(data={"articles": articles})
