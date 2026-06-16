from gw2radar.kb.kb_models import (
    AllowedUse,
    CrawlPolicy,
    KnowledgeArticleInput,
    KnowledgeContentType,
    KnowledgeDomain,
    KnowledgeReviewStatus,
    RateLimitPolicy,
    SourceRegistryInput,
    SourceType,
)
from gw2radar.kb.kb_repository import create_article, register_source


def official_source_input() -> SourceRegistryInput:
    return SourceRegistryInput(
        name="Official GW2 API",
        source_type=SourceType.OFFICIAL_API,
        base_url="https://api.guildwars2.com/",
        allowed_use=AllowedUse.API_JSON,
        crawl_policy=CrawlPolicy.API_ONLY,
        rate_limit_policy=RateLimitPolicy.GATEWAY_MANAGED,
        license_note="Use official API responses through the governed gateway.",
        default_confidence=0.95,
    )


def legendary_article_input(source_id: str) -> KnowledgeArticleInput:
    return KnowledgeArticleInput(
        title="Mystic Clover source summary",
        domain=KnowledgeDomain.LEGENDARY,
        content_type=KnowledgeContentType.SUMMARY,
        summary="Mystic Clover acquisition is a recurring legendary planning bottleneck.",
        body_markdown="Use source-linked summaries and keep acquisition advice reviewed before report use.",
        source_refs=[source_id],
        linked_entities=["gw2:item:mystic_clover"],
        linked_actions=["do_daily"],
        confidence=0.8,
        review_status=KnowledgeReviewStatus.DRAFT,
    )


def create_sample_kb_article(session):
    source = register_source(session, official_source_input())
    article = create_article(session, legendary_article_input(source.source_id))
    return source, article
