from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.kb.kb_entity_linker import validate_article_links
from gw2radar.kb.kb_models import KnowledgeArticleInput, KnowledgeContentType, KnowledgeDomain


def test_kb_entity_linker_validates_graph_concepts_and_actions() -> None:
    graph = build_mock_graph()
    article = KnowledgeArticleInput(
        title="Link validation note",
        domain=KnowledgeDomain.LEGENDARY,
        content_type=KnowledgeContentType.SUMMARY,
        summary="Mystic Clover and system concepts can be linked with action schema validation.",
        linked_entities=["gw2:item:mystic_clover", "gw2:system:legendary", "gw2:item:missing"],
        linked_actions=["hold", "not_an_action"],
    )
    model = article.model_dump()
    model.update({"kb_id": "kb_article_test", "created_at": "2026-06-16T00:00:00Z", "updated_at": "2026-06-16T00:00:00Z"})

    result = validate_article_links(type("Article", (), model)(), graph)

    assert result.valid_entities == ["gw2:item:mystic_clover"]
    assert result.concept_entities == ["gw2:system:legendary"]
    assert result.missing_entities == ["gw2:item:missing"]
    assert result.valid_actions == ["hold"]
    assert result.invalid_actions == ["not_an_action"]
    assert result.is_valid is False
