from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


MAX_KB_SUMMARY_CHARS = 900
MAX_KB_BODY_CHARS = 8000
MAX_KB_CHUNK_CHARS = 1400
LOW_CONFIDENCE_CAP = 0.5
HIGH_PRIORITY_THRESHOLD = 0.8

PRIVATE_DATA_MARKERS = [
    "api key",
    "access token",
    "private inventory",
    "bank contents",
    "account id:",
    "private player state",
]

FORBIDDEN_COPY_MARKERS = [
    "full article copied",
    "verbatim transcript",
    "entire guide text",
    "copied full guide",
]


class SourceType(StrEnum):
    OFFICIAL_API = "official_api"
    OFFICIAL_WIKI = "official_wiki"
    OFFICIAL_NEWS = "official_news"
    PUBLIC_GUIDE = "public_guide"
    BUILD_SITE = "build_site"
    COMMUNITY = "community"
    MANUAL = "manual"


class AllowedUse(StrEnum):
    API_JSON = "api_json"
    SUMMARY_AND_REFERENCE = "summary_and_reference"
    MANUAL_NOTE = "manual_note"


class CrawlPolicy(StrEnum):
    API_ONLY = "api_only"
    MANUAL_ONLY = "manual_only"
    CONSERVATIVE = "conservative"


class RateLimitPolicy(StrEnum):
    GATEWAY_MANAGED = "gateway_managed"
    LOW_FREQUENCY = "low_frequency"
    MANUAL = "manual"


class KnowledgeDomain(StrEnum):
    OFFICIAL = "official"
    GAME_SYSTEM = "game_system"
    LEGENDARY = "legendary"
    RETURNER = "returner"
    BUILD = "build"
    MARKET = "market"
    GUILD = "guild"
    CREATOR = "creator"


class KnowledgeContentType(StrEnum):
    GUIDE = "guide"
    RULE = "rule"
    FAQ = "faq"
    SUMMARY = "summary"
    TEMPLATE = "template"
    SOURCE_NOTE = "source_note"


class KnowledgeReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    DEPRECATED = "deprecated"
    NEEDS_UPDATE = "needs_update"
    CONFLICT = "conflict"


class SourceRegistryInput(BaseModel):
    name: str
    source_type: SourceType
    base_url: HttpUrl | None = None
    allowed_use: AllowedUse
    crawl_policy: CrawlPolicy
    rate_limit_policy: RateLimitPolicy
    license_note: str | None = None
    default_confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class SourceRegistry(SourceRegistryInput):
    source_id: str
    created_at: datetime
    updated_at: datetime


class KnowledgeArticleInput(BaseModel):
    title: str
    domain: KnowledgeDomain
    content_type: KnowledgeContentType
    summary: str = Field(max_length=MAX_KB_SUMMARY_CHARS)
    body_markdown: str = Field(default="", max_length=MAX_KB_BODY_CHARS)
    source_refs: list[str] = Field(default_factory=list)
    linked_entities: list[str] = Field(default_factory=list)
    linked_relations: list[str] = Field(default_factory=list)
    linked_actions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    review_status: KnowledgeReviewStatus = KnowledgeReviewStatus.DRAFT
    valid_from: datetime | None = None
    valid_to: datetime | None = None

    @model_validator(mode="after")
    def validate_article_contract(self) -> "KnowledgeArticleInput":
        validate_kb_text(self.summary, self.body_markdown)
        if self.source_refs and any(not ref.strip() for ref in self.source_refs):
            raise ValueError("Source references cannot be blank.")
        if self.domain == KnowledgeDomain.CREATOR and self.review_status != KnowledgeReviewStatus.REVIEWED:
            self.confidence = min(self.confidence, LOW_CONFIDENCE_CAP)
        return self


class KnowledgeArticle(KnowledgeArticleInput):
    kb_id: str
    last_reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkInput(BaseModel):
    kb_id: str
    text: str = Field(max_length=MAX_KB_CHUNK_CHARS)
    token_count: int = Field(ge=0)
    embedding_id: str | None = None
    linked_entities: list[str] = Field(default_factory=list)
    linked_actions: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_chunk_contract(self) -> "KnowledgeChunkInput":
        validate_kb_text(self.text)
        return self


class KnowledgeChunk(KnowledgeChunkInput):
    chunk_id: str
    created_at: datetime


class KnowledgeRuleInput(BaseModel):
    name: str
    domain: KnowledgeDomain
    condition: str
    recommendation: str
    action_type: str
    priority_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    explanation_template: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.6, ge=0.0, le=1.0)
    review_status: KnowledgeReviewStatus = KnowledgeReviewStatus.DRAFT
    enabled: bool = True

    @model_validator(mode="after")
    def validate_rule_contract(self) -> "KnowledgeRuleInput":
        validate_kb_text(self.recommendation, self.explanation_template)
        if self.review_status != KnowledgeReviewStatus.REVIEWED and self.enabled:
            raise ValueError("Unreviewed KB rules cannot be enabled.")
        if self.review_status != KnowledgeReviewStatus.REVIEWED and self.priority_delta >= HIGH_PRIORITY_THRESHOLD:
            raise ValueError("Unreviewed KB rules cannot drive high-priority actions.")
        return self


class KnowledgeRule(KnowledgeRuleInput):
    rule_id: str
    created_at: datetime
    updated_at: datetime


def validate_kb_text(*texts: str) -> None:
    text = "\n".join(texts).lower()
    for marker in FORBIDDEN_COPY_MARKERS:
        if marker in text:
            raise ValueError(f"No mass-copy policy violation: {marker}")
    for marker in PRIVATE_DATA_MARKERS:
        if marker in text:
            raise ValueError(f"Private player data is not allowed in KB content: {marker}")
