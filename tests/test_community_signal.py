from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.commercial.creator_intelligence import (
    CommunitySignalInput,
    CommunitySignalKind,
    CommunitySourceType,
    import_community_signal,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_community_signal_import_preserves_source_and_caps_unverified_confidence() -> None:
    temp_dir = Path(".test_tmp") / f"creator-signal-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            signal = import_community_signal(
                session,
                CommunitySignalInput(
                    source_type=CommunitySourceType.PUBLIC_FORUM,
                    source_url="https://example.com/forum/topic",
                    title="How do I plan legendary armor?",
                    summary="A community question asks for a concise legendary armor planning guide.",
                    topic="Legendary Armor",
                    signal_kind=CommunitySignalKind.QUESTION,
                    confidence=0.9,
                ),
            )

        assert signal.source_url == "https://example.com/forum/topic"
        assert signal.topic == "legendary armor"
        assert signal.confidence == 0.5
        assert signal.summary.startswith("A community question")
    finally:
        close_database()


def test_private_discord_signal_requires_authorization() -> None:
    temp_dir = Path(".test_tmp") / f"creator-private-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            with pytest.raises(ValueError, match="explicit authorization"):
                import_community_signal(
                    session,
                    CommunitySignalInput(
                        source_type=CommunitySourceType.DISCORD_PRIVATE,
                        source_url="https://discord.com/channels/example/message",
                        title="Private static build discussion",
                        summary="A private server discussion was summarized with permission missing.",
                        topic="static builds",
                    ),
                )
    finally:
        close_database()
