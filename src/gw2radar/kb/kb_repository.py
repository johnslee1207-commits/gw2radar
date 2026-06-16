from uuid import uuid4

from sqlalchemy.orm import Session

from gw2radar.db.models import (
    KnowledgeArticleModel,
    KnowledgeChunkModel,
    KnowledgeRuleModel,
    KnowledgeSourceModel,
    utc_now,
)
from gw2radar.kb.kb_models import (
    KnowledgeArticle,
    KnowledgeArticleInput,
    KnowledgeChunk,
    KnowledgeChunkInput,
    KnowledgeDomain,
    KnowledgeReviewStatus,
    KnowledgeRule,
    KnowledgeRuleInput,
    SourceRegistry,
    SourceRegistryInput,
)


def register_source(session: Session, source: SourceRegistryInput) -> SourceRegistry:
    row = KnowledgeSourceModel(
        source_id=f"kb_source_{uuid4().hex}",
        name=source.name.strip(),
        source_type=source.source_type.value,
        base_url=str(source.base_url) if source.base_url else None,
        allowed_use=source.allowed_use.value,
        crawl_policy=source.crawl_policy.value,
        rate_limit_policy=source.rate_limit_policy.value,
        license_note=source.license_note,
        default_confidence=source.default_confidence,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _source_from_model(row)


def get_source(session: Session, source_id: str) -> SourceRegistry | None:
    row = session.get(KnowledgeSourceModel, source_id)
    return _source_from_model(row) if row else None


def list_sources(session: Session, source_type: str | None = None) -> list[SourceRegistry]:
    query = session.query(KnowledgeSourceModel)
    if source_type:
        query = query.filter(KnowledgeSourceModel.source_type == source_type)
    rows = query.order_by(KnowledgeSourceModel.name).all()
    return [_source_from_model(row) for row in rows]


def create_article(session: Session, article: KnowledgeArticleInput) -> KnowledgeArticle:
    _ensure_sources_exist(session, article.source_refs)
    row = KnowledgeArticleModel(
        kb_id=f"kb_article_{uuid4().hex}",
        title=article.title.strip(),
        domain=article.domain.value,
        content_type=article.content_type.value,
        summary=article.summary.strip(),
        body_markdown=article.body_markdown.strip(),
        source_refs_json=article.source_refs,
        linked_entities_json=article.linked_entities,
        linked_relations_json=article.linked_relations,
        linked_actions_json=article.linked_actions,
        confidence=article.confidence,
        review_status=article.review_status.value,
        last_reviewed_at=utc_now() if article.review_status == KnowledgeReviewStatus.REVIEWED else None,
        valid_from=article.valid_from,
        valid_to=article.valid_to,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _article_from_model(row)


def get_article(session: Session, kb_id: str) -> KnowledgeArticle | None:
    row = session.get(KnowledgeArticleModel, kb_id)
    return _article_from_model(row) if row else None


def list_articles(session: Session, domain: KnowledgeDomain | None = None) -> list[KnowledgeArticle]:
    query = session.query(KnowledgeArticleModel)
    if domain is not None:
        query = query.filter(KnowledgeArticleModel.domain == domain.value)
    rows = query.order_by(KnowledgeArticleModel.domain, KnowledgeArticleModel.title).all()
    return [_article_from_model(row) for row in rows]


def search_articles(
    session: Session,
    query_text: str,
    domain: KnowledgeDomain | None = None,
    include_deprecated: bool = False,
) -> list[KnowledgeArticle]:
    needle = query_text.strip().lower()
    if not needle:
        return []
    articles = list_articles(session, domain)
    results: list[KnowledgeArticle] = []
    for article in articles:
        if not include_deprecated and article.review_status == KnowledgeReviewStatus.DEPRECATED:
            continue
        haystack = "\n".join(
            [
                article.title,
                article.summary,
                article.body_markdown,
                " ".join(article.linked_entities),
                " ".join(article.linked_actions),
            ]
        ).lower()
        if needle in haystack:
            results.append(article)
    return results


def review_article(session: Session, kb_id: str) -> KnowledgeArticle:
    row = session.get(KnowledgeArticleModel, kb_id)
    if row is None:
        raise ValueError("Knowledge article not found.")
    row.review_status = KnowledgeReviewStatus.REVIEWED.value
    row.last_reviewed_at = utc_now()
    row.updated_at = utc_now()
    session.commit()
    return _article_from_model(row)


def deprecate_article(session: Session, kb_id: str) -> KnowledgeArticle:
    row = session.get(KnowledgeArticleModel, kb_id)
    if row is None:
        raise ValueError("Knowledge article not found.")
    row.review_status = KnowledgeReviewStatus.DEPRECATED.value
    row.updated_at = utc_now()
    session.commit()
    return _article_from_model(row)


def create_chunk(session: Session, chunk: KnowledgeChunkInput) -> KnowledgeChunk:
    if session.get(KnowledgeArticleModel, chunk.kb_id) is None:
        raise ValueError("Knowledge article not found.")
    row = KnowledgeChunkModel(
        chunk_id=f"kb_chunk_{uuid4().hex}",
        kb_id=chunk.kb_id,
        text=chunk.text.strip(),
        token_count=chunk.token_count,
        embedding_id=chunk.embedding_id,
        linked_entities_json=chunk.linked_entities,
        linked_actions_json=chunk.linked_actions,
        source_refs_json=chunk.source_refs,
        confidence=chunk.confidence,
        created_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _chunk_from_model(row)


def create_rule(session: Session, rule: KnowledgeRuleInput) -> KnowledgeRule:
    row = KnowledgeRuleModel(
        rule_id=f"kb_rule_{uuid4().hex}",
        name=rule.name.strip(),
        domain=rule.domain.value,
        condition=rule.condition.strip(),
        recommendation=rule.recommendation.strip(),
        action_type=rule.action_type,
        priority_delta=rule.priority_delta,
        explanation_template=rule.explanation_template.strip(),
        evidence_refs_json=rule.evidence_refs,
        confidence=rule.confidence,
        review_status=rule.review_status.value,
        enabled=rule.enabled,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(row)
    session.commit()
    return _rule_from_model(row)


def get_rule(session: Session, rule_id: str) -> KnowledgeRule | None:
    row = session.get(KnowledgeRuleModel, rule_id)
    return _rule_from_model(row) if row else None


def list_rules(session: Session, domain: KnowledgeDomain | None = None) -> list[KnowledgeRule]:
    query = session.query(KnowledgeRuleModel)
    if domain is not None:
        query = query.filter(KnowledgeRuleModel.domain == domain.value)
    rows = query.order_by(KnowledgeRuleModel.domain, KnowledgeRuleModel.name).all()
    return [_rule_from_model(row) for row in rows]


def enable_rule(session: Session, rule_id: str) -> KnowledgeRule:
    row = session.get(KnowledgeRuleModel, rule_id)
    if row is None:
        raise ValueError("Knowledge rule not found.")
    if row.review_status != KnowledgeReviewStatus.REVIEWED.value:
        raise ValueError("Only reviewed KnowledgeRule records can be enabled.")
    row.enabled = True
    row.updated_at = utc_now()
    session.commit()
    return _rule_from_model(row)


def _ensure_sources_exist(session: Session, source_refs: list[str]) -> None:
    for source_id in source_refs:
        if session.get(KnowledgeSourceModel, source_id) is None:
            raise ValueError(f"Knowledge source not found: {source_id}")


def _source_from_model(row: KnowledgeSourceModel) -> SourceRegistry:
    return SourceRegistry(
        source_id=row.source_id,
        name=row.name,
        source_type=row.source_type,
        base_url=row.base_url,
        allowed_use=row.allowed_use,
        crawl_policy=row.crawl_policy,
        rate_limit_policy=row.rate_limit_policy,
        license_note=row.license_note,
        default_confidence=row.default_confidence,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _article_from_model(row: KnowledgeArticleModel) -> KnowledgeArticle:
    return KnowledgeArticle(
        kb_id=row.kb_id,
        title=row.title,
        domain=row.domain,
        content_type=row.content_type,
        summary=row.summary,
        body_markdown=row.body_markdown,
        source_refs=row.source_refs_json,
        linked_entities=row.linked_entities_json,
        linked_relations=row.linked_relations_json,
        linked_actions=row.linked_actions_json,
        confidence=row.confidence,
        review_status=row.review_status,
        last_reviewed_at=row.last_reviewed_at,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _chunk_from_model(row: KnowledgeChunkModel) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=row.chunk_id,
        kb_id=row.kb_id,
        text=row.text,
        token_count=row.token_count,
        embedding_id=row.embedding_id,
        linked_entities=row.linked_entities_json,
        linked_actions=row.linked_actions_json,
        source_refs=row.source_refs_json,
        confidence=row.confidence,
        created_at=row.created_at,
    )


def _rule_from_model(row: KnowledgeRuleModel) -> KnowledgeRule:
    return KnowledgeRule(
        rule_id=row.rule_id,
        name=row.name,
        domain=row.domain,
        condition=row.condition,
        recommendation=row.recommendation,
        action_type=row.action_type,
        priority_delta=row.priority_delta,
        explanation_template=row.explanation_template,
        evidence_refs=row.evidence_refs_json,
        confidence=row.confidence,
        review_status=row.review_status,
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
