from pydantic import BaseModel, Field

from gw2radar.graph.graph_query import GraphData
from gw2radar.kb.kb_models import KnowledgeArticle
from gw2radar.ontology.action_types import ActionType


CONCEPT_ENTITY_PREFIXES = ("gw2:system:", "gw2:segment:")


class KnowledgeLinkValidationResult(BaseModel):
    kb_id: str
    valid_entities: list[str] = Field(default_factory=list)
    concept_entities: list[str] = Field(default_factory=list)
    missing_entities: list[str] = Field(default_factory=list)
    valid_actions: list[str] = Field(default_factory=list)
    invalid_actions: list[str] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.missing_entities and not self.invalid_actions


def validate_article_links(article: KnowledgeArticle, graph: GraphData) -> KnowledgeLinkValidationResult:
    valid_entities: list[str] = []
    concept_entities: list[str] = []
    missing_entities: list[str] = []
    for entity_id in article.linked_entities:
        if entity_id in graph.entities:
            valid_entities.append(entity_id)
        elif entity_id.startswith(CONCEPT_ENTITY_PREFIXES):
            concept_entities.append(entity_id)
        else:
            missing_entities.append(entity_id)

    allowed_actions = {action.value for action in ActionType}
    valid_actions = [action for action in article.linked_actions if action in allowed_actions]
    invalid_actions = [action for action in article.linked_actions if action not in allowed_actions]

    return KnowledgeLinkValidationResult(
        kb_id=article.kb_id,
        valid_entities=valid_entities,
        concept_entities=concept_entities,
        missing_entities=missing_entities,
        valid_actions=valid_actions,
        invalid_actions=invalid_actions,
    )


def validate_articles_links(articles: list[KnowledgeArticle], graph: GraphData) -> list[KnowledgeLinkValidationResult]:
    return [validate_article_links(article, graph) for article in articles]
