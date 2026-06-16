import pytest

from gw2radar.kb.kb_models import KnowledgeArticleInput, KnowledgeContentType, KnowledgeDomain


def test_kb_article_rejects_private_player_data_markers() -> None:
    with pytest.raises(ValueError, match="Private player data"):
        KnowledgeArticleInput(
            title="Unsafe account note",
            domain=KnowledgeDomain.RETURNER,
            content_type=KnowledgeContentType.SUMMARY,
            summary="This note includes private inventory details from a user account.",
        )


def test_kb_article_rejects_api_key_markers() -> None:
    with pytest.raises(ValueError, match="Private player data"):
        KnowledgeArticleInput(
            title="Unsafe key note",
            domain=KnowledgeDomain.OFFICIAL,
            content_type=KnowledgeContentType.SOURCE_NOTE,
            summary="Never put an API key into knowledge base text.",
        )
