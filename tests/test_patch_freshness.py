from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.build_fit import BuildImport, BuildSource, GearRequirement, GearSlot, import_build
from gw2radar.commercial.market_radar import add_watchlist_item
from gw2radar.commercial.patch_freshness import (
    build_freshness_notices,
    market_freshness_notices,
    render_patch_freshness_section,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeReviewStatus
from gw2radar.kb.patch_impact_review import PatchReviewDashboardItem


def test_patch_freshness_build_and_market_notices_are_manual_review_only() -> None:
    temp_dir = Path(".test_tmp") / f"patch-freshness-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'freshness.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, _build_import())
            watch = add_watchlist_item(session, "gw2:item:mystic_coin", "Mystic Coin", "Goal material watch")

        patch = _reviewed_patch_item()
        build_notices = build_freshness_notices(build, [patch])
        market_notices = market_freshness_notices([watch], [patch])
        section = render_patch_freshness_section(
            type(
                "Report",
                (),
                {"notices": [*build_notices, *market_notices]},
            )()
        )

        assert len(build_notices) == 1
        assert build_notices[0].boundary == "manual_review_only_no_automatic_changes"
        assert "manually verify" in build_notices[0].reason
        assert len(market_notices) == 1
        assert "manually review" in market_notices[0].reason
        assert "automatic" in "\n".join(section)
        assert "automated order" not in "\n".join(section).lower()
    finally:
        close_database()


def test_patch_freshness_api_for_build_and_market() -> None:
    temp_dir = Path(".test_tmp") / f"patch-freshness-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'freshness.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        with db_session.SessionLocal() as session:
            build = import_build(session, _build_import())
            add_watchlist_item(session, "gw2:item:mystic_coin", "Mystic Coin", "Goal material watch")

        build_response = client.get(f"/api/v1/builds/{build.build_id}/patch-freshness")
        market_response = client.get("/api/v1/market/patch-freshness")

        assert build_response.status_code == 200
        assert build_response.json()["data"]["notice_count"] >= 1
        assert build_response.json()["data"]["notices"][0]["boundary"] == "manual_review_only_no_automatic_changes"
        assert market_response.status_code == 200
        assert market_response.json()["data"]["notice_count"] >= 1
    finally:
        close_database()
        state.reset_cached_graph()


def _build_import() -> BuildImport:
    return BuildImport(
        name="Old Patch Open World Build",
        source=BuildSource(name="manual", attribution="User-provided structured build data."),
        profession="Necromancer",
        specialization="Reaper",
        role="dps",
        game_mode="open_world",
        patch_version="2025-01",
        patch_freshness_days=240,
        difficulty="low",
        requirements=[
            GearRequirement(
                slot=GearSlot.WEAPON_1,
                item_name="Greatsword",
                stat_combo="Berserker",
                estimated_cost_gold=5,
            )
        ],
        estimated_transition_cost_gold=5,
    )


def _reviewed_patch_item() -> PatchReviewDashboardItem:
    return PatchReviewDashboardItem(
        patch_id="patch:2026-06-02",
        date="2026-06-02",
        year=2026,
        title="GW2 Patch Note 2026-06-02",
        source_pdf="docs/knowledge_base/_sources/pdf/patch_notes/2026/source.pdf",
        evidence_id="evidence:pdf:patch:2026-06-02",
        review_status=KnowledgeReviewStatus.REVIEWED,
        lifecycle_status="reviewed",
        affected_systems=["build", "market", "items"],
        possible_build_impact=["manual build freshness review"],
        possible_market_impact=["manual market watchlist review"],
        latest_audit_at=datetime.now(timezone.utc),
    )
