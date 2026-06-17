import csv
from io import StringIO

from pydantic import BaseModel, Field

from gw2radar.graph.graph_query import GraphData
from gw2radar.kb.kb_domain_rule_packs import DomainRulePack, list_domain_rule_packs
from gw2radar.kb.kb_entity_linker import KnowledgeLinkValidationResult, validate_article_links
from gw2radar.kb.kb_models import (
    KnowledgeArticle,
    KnowledgeContentType,
    KnowledgeDomain,
    KnowledgeReviewStatus,
    KnowledgeRuleInput,
)
from gw2radar.kb.kb_rule_distiller import DEFAULT_RULE_PRIORITY_DELTA
from gw2radar.ontology.action_types import ActionType


class ArticlePromotionPreview(BaseModel):
    kb_id: str
    title: str
    domain: KnowledgeDomain
    review_status: KnowledgeReviewStatus
    content_type: KnowledgeContentType
    link_validation: KnowledgeLinkValidationResult
    distillable: bool
    rule_preview: KnowledgeRuleInput | None = None
    blockers: list[str] = Field(default_factory=list)


class RulePackPromotionPreview(BaseModel):
    pack_id: str
    title: str
    domain: KnowledgeDomain
    rule_count: int
    importable: bool
    blockers: list[str] = Field(default_factory=list)


class KbPromotionPlan(BaseModel):
    schema_version: str
    domain: KnowledgeDomain | None = None
    article_count: int
    distillable_article_count: int
    blocked_article_count: int
    rule_pack_count: int
    importable_rule_pack_count: int
    blocker_count: int
    articles: list[ArticlePromotionPreview]
    rule_packs: list[RulePackPromotionPreview]
    blockers: list[str]


def build_kb_promotion_plan(
    articles: list[KnowledgeArticle],
    graph: GraphData,
    *,
    domain: KnowledgeDomain | None = None,
    include_rule_packs: bool = True,
) -> KbPromotionPlan:
    scoped_articles = [article for article in articles if domain is None or article.domain == domain]
    article_previews = [_preview_article(article, graph) for article in scoped_articles]
    packs = _preview_rule_packs(domain) if include_rule_packs else []
    blockers = _collect_blockers(article_previews, packs)
    return KbPromotionPlan(
        schema_version="gw2radar.kb_promotion_plan.v1",
        domain=domain,
        article_count=len(article_previews),
        distillable_article_count=sum(1 for item in article_previews if item.distillable),
        blocked_article_count=sum(1 for item in article_previews if item.blockers),
        rule_pack_count=len(packs),
        importable_rule_pack_count=sum(1 for item in packs if item.importable),
        blocker_count=len(blockers),
        articles=article_previews,
        rule_packs=packs,
        blockers=blockers,
    )


def render_kb_promotion_plan_markdown(plan: KbPromotionPlan) -> str:
    lines = [
        "# KB Promotion Plan",
        "",
        f"- schema_version: `{plan.schema_version}`",
        f"- domain: `{plan.domain.value if plan.domain else 'all'}`",
        f"- article_count: `{plan.article_count}`",
        f"- distillable_article_count: `{plan.distillable_article_count}`",
        f"- blocked_article_count: `{plan.blocked_article_count}`",
        f"- rule_pack_count: `{plan.rule_pack_count}`",
        f"- importable_rule_pack_count: `{plan.importable_rule_pack_count}`",
        f"- blocker_count: `{plan.blocker_count}`",
        "",
        "## Article Promotion Preview",
        "",
        "| Article | Domain | Reviewed | Links Valid | Distillable | Blockers |",
        "|---|---|---:|---:|---:|---|",
    ]
    for article in plan.articles:
        lines.append(
            f"| {article.title} | {article.domain.value} | {_yes(article.review_status == KnowledgeReviewStatus.REVIEWED)} | "
            f"{_yes(article.link_validation.is_valid)} | {_yes(article.distillable)} | {_join(article.blockers)} |"
        )
    lines.extend(["", "## Rule Pack Preview", "", "| Pack | Domain | Rule Count | Importable | Blockers |", "|---|---|---:|---:|---|"])
    for pack in plan.rule_packs:
        lines.append(f"| {pack.title} | {pack.domain.value} | {pack.rule_count} | {_yes(pack.importable)} | {_join(pack.blockers)} |")
    if plan.blockers:
        lines.extend(["", "## Blockers", ""])
        lines.extend([f"- {blocker}" for blocker in plan.blockers])
    return "\n".join(lines).strip() + "\n"


def render_kb_promotion_plan_csv(plan: KbPromotionPlan) -> str:
    output = StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["kind", "id", "title", "domain", "ready", "blockers"])
    for article in plan.articles:
        writer.writerow(
            [
                "article",
                article.kb_id,
                article.title,
                article.domain.value,
                str(article.distillable).lower(),
                "; ".join(article.blockers),
            ]
        )
    for pack in plan.rule_packs:
        writer.writerow(
            [
                "rule_pack",
                pack.pack_id,
                pack.title,
                pack.domain.value,
                str(pack.importable).lower(),
                "; ".join(pack.blockers),
            ]
        )
    return output.getvalue()


def _preview_article(article: KnowledgeArticle, graph: GraphData) -> ArticlePromotionPreview:
    validation = validate_article_links(article, graph)
    blockers = _article_blockers(article, validation)
    rule_preview = _rule_preview_from_article(article) if not blockers else None
    return ArticlePromotionPreview(
        kb_id=article.kb_id,
        title=article.title,
        domain=article.domain,
        review_status=article.review_status,
        content_type=article.content_type,
        link_validation=validation,
        distillable=rule_preview is not None,
        rule_preview=rule_preview,
        blockers=blockers,
    )


def _article_blockers(article: KnowledgeArticle, validation: KnowledgeLinkValidationResult) -> list[str]:
    blockers: list[str] = []
    if article.content_type != KnowledgeContentType.RULE:
        blockers.append("Article is not a KB rule article.")
    if article.review_status != KnowledgeReviewStatus.REVIEWED:
        blockers.append("Article must be reviewed before rule distillation.")
    if not article.linked_actions:
        blockers.append("Article needs at least one linked action.")
    if not validation.is_valid:
        if validation.missing_entities:
            blockers.append(f"Missing linked entities: {', '.join(validation.missing_entities)}.")
        if validation.invalid_actions:
            blockers.append(f"Invalid linked actions: {', '.join(validation.invalid_actions)}.")
    return blockers


def _rule_preview_from_article(article: KnowledgeArticle) -> KnowledgeRuleInput:
    return KnowledgeRuleInput(
        name=article.title,
        domain=article.domain,
        condition=_condition_from_article(article),
        recommendation=article.summary,
        action_type=article.linked_actions[0],
        priority_delta=DEFAULT_RULE_PRIORITY_DELTA,
        explanation_template=_explanation_template_from_article(article),
        evidence_refs=article.source_refs,
        confidence=article.confidence,
        review_status=KnowledgeReviewStatus.REVIEWED,
        enabled=False,
    )


def _preview_rule_packs(domain: KnowledgeDomain | None) -> list[RulePackPromotionPreview]:
    packs = [pack for pack in list_domain_rule_packs() if domain is None or pack.domain == domain]
    return [_preview_rule_pack(pack) for pack in packs]


def _preview_rule_pack(pack: DomainRulePack) -> RulePackPromotionPreview:
    blockers: list[str] = []
    if not pack.rules:
        blockers.append("Rule pack has no rules.")
    for rule in pack.rules:
        if rule.review_status != KnowledgeReviewStatus.REVIEWED:
            blockers.append(f"{rule.name} is not reviewed.")
        if rule.enabled:
            blockers.append(f"{rule.name} must be disabled before import.")
        if rule.action_type not in {action.value for action in ActionType}:
            blockers.append(f"{rule.name} action_type is not in the ActionType schema.")
        if not rule.evidence_refs:
            blockers.append(f"{rule.name} has no evidence refs.")
    return RulePackPromotionPreview(
        pack_id=pack.pack_id.value,
        title=pack.title,
        domain=pack.domain,
        rule_count=len(pack.rules),
        importable=not blockers,
        blockers=blockers,
    )


def _collect_blockers(
    articles: list[ArticlePromotionPreview],
    packs: list[RulePackPromotionPreview],
) -> list[str]:
    blockers: list[str] = []
    for article in articles:
        blockers.extend([f"{article.kb_id}: {blocker}" for blocker in article.blockers])
    for pack in packs:
        blockers.extend([f"{pack.pack_id}: {blocker}" for blocker in pack.blockers])
    return blockers


def _condition_from_article(article: KnowledgeArticle) -> str:
    if article.linked_entities:
        return f"article_links_any_entity:{','.join(article.linked_entities)}"
    return f"article_domain:{article.domain.value}"


def _explanation_template_from_article(article: KnowledgeArticle) -> str:
    body = article.body_markdown.strip()
    if not body:
        return article.summary
    first_line = next((line.strip() for line in body.splitlines() if line.strip()), article.summary)
    return f"{article.summary} {first_line}"


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else "none"


def _yes(value: bool) -> str:
    return "yes" if value else "no"
