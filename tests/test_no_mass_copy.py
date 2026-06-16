import pytest

from gw2radar.commercial.creator_intelligence import (
    CommunitySignalInput,
    CommunitySourceType,
    validate_no_mass_copy,
)


def test_no_mass_copy_rejects_long_raw_context() -> None:
    with pytest.raises(ValueError, match="Raw context is too long"):
        validate_no_mass_copy("Concise summary only.", raw_context="copied text " * 130)


def test_no_mass_copy_rejects_explicit_full_text_markers() -> None:
    with pytest.raises(ValueError, match="No mass-copy policy"):
        validate_no_mass_copy("This is a full article copied from a third-party page.")


def test_signal_input_excludes_raw_context_from_dump() -> None:
    signal = CommunitySignalInput(
        source_type=CommunitySourceType.PUBLIC_FORUM,
        source_url="https://example.com/forum/topic",
        title="Short discussion",
        summary="A short summary of a public discussion.",
        topic="source policy",
        raw_context="temporary local review context",
    )

    assert "raw_context" not in signal.model_dump()
