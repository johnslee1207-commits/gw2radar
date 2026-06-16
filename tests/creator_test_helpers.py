from gw2radar.commercial.creator_intelligence import (
    AudienceSegment,
    CommunitySignalInput,
    CommunitySignalKind,
    CommunitySourceType,
    import_community_signal,
)


def returning_player_questions() -> list[CommunitySignalInput]:
    return [
        CommunitySignalInput(
            source_type=CommunitySourceType.PUBLIC_FORUM,
            source_url="https://example.com/forums/returner-gear",
            title="How do I gear a returning player build?",
            summary="Several returning players ask what gear path is cheapest before committing to a meta build.",
            topic="returner gearing",
            audience_segment=AudienceSegment.RETURNING_PLAYER,
            signal_kind=CommunitySignalKind.QUESTION,
            confidence=0.8,
        ),
        CommunitySignalInput(
            source_type=CommunitySourceType.REDDIT,
            source_url="https://example.com/r/guildwars2/returner-build",
            title="What should I craft first after coming back?",
            summary="The thread asks for a simple build and upgrade order for a newly returned account.",
            topic="returner gearing",
            audience_segment=AudienceSegment.RETURNING_PLAYER,
            signal_kind=CommunitySignalKind.QUESTION,
            confidence=0.7,
        ),
        CommunitySignalInput(
            source_type=CommunitySourceType.WIKI,
            source_url="https://wiki.guildwars2.com/wiki/Equipment_acquisition",
            title="Equipment acquisition reference",
            summary="Primary reference for acquisition paths; useful for verifying guide recommendations.",
            topic="returner gearing",
            audience_segment=AudienceSegment.RETURNING_PLAYER,
            signal_kind=CommunitySignalKind.DISCUSSION,
            confidence=0.95,
            verified=True,
        ),
    ]


def import_returning_player_questions(session):
    return [import_community_signal(session, signal) for signal in returning_player_questions()]
