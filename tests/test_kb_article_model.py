import pytest

from gw2radar.kb.kb_models import (
    KnowledgeArticleInput,
    KnowledgeContentType,
    KnowledgeDomain,
    KnowledgeReviewStatus,
)


def test_kb_article_model_caps_unreviewed_creator_confidence() -> None:
    article = KnowledgeArticleInput(
        title="Creator topic summary",
        domain=KnowledgeDomain.CREATOR,
        content_type=KnowledgeContentType.SUMMARY,
        summary="Community questions indicate a possible guide gap.",
        confidence=0.9,
        review_status=KnowledgeReviewStatus.DRAFT,
    )

    assert article.confidence == 0.5


def test_kb_article_model_rejects_mass_copied_text() -> None:
    with pytest.raises(ValueError, match="No mass-copy policy"):
        KnowledgeArticleInput(
            title="Copied guide",
            domain=KnowledgeDomain.BUILD,
            content_type=KnowledgeContentType.GUIDE,
            summary="This is a full article copied from a third-party site.",
        )
