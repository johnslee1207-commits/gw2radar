from sqlalchemy.orm import Session

from gw2radar.kb.kb_models import (
    KnowledgeArticle,
    KnowledgeContentType,
    KnowledgeReviewStatus,
    KnowledgeRule,
    KnowledgeRuleInput,
)
from gw2radar.kb.kb_repository import create_rule
from gw2radar.ontology.action_types import ActionType


DEFAULT_RULE_PRIORITY_DELTA = 0.2


def distill_rule_from_article(session: Session, article: KnowledgeArticle) -> KnowledgeRule:
    if article.content_type != KnowledgeContentType.RULE:
        raise ValueError("Only KB rule articles can be distilled into KnowledgeRule records.")
    if article.review_status != KnowledgeReviewStatus.REVIEWED:
        raise ValueError("Only reviewed KB rule articles can be distilled into KnowledgeRule records.")
    if not article.linked_actions:
        raise ValueError("KB rule articles need at least one linked action for rule distillation.")
    if article.linked_actions[0] not in {action.value for action in ActionType}:
        raise ValueError("KB rule article linked action is not in the ActionType schema.")

    rule_input = KnowledgeRuleInput(
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
        enabled=True,
    )
    return create_rule(session, rule_input)


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
