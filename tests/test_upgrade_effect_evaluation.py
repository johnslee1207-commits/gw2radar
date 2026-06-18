from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import (
    AccountGearItem,
    AccountGearSnapshot,
    GearSlot,
    evaluate_build_fit,
    import_build,
    render_build_fit_report,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import sample_build_import


def test_upgrade_effect_evaluation_flags_aligned_and_risky_upgrades() -> None:
    temp_dir = Path(".test_tmp") / f"upgrade-effects-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        account = AccountGearSnapshot(
            profession="Revenant",
            specializations=["Herald"],
            preferred_game_modes=["strike"],
            wallet_gold=120,
            gear=[
                AccountGearItem(slot=GearSlot.CHEST, item_name="Owned Ascended Chest", stat_combo="Berserker", equipment_category="armor"),
                AccountGearItem(slot=GearSlot.RUNE, item_name="Superior Rune of the Scholar", stat_combo="Rune", equipment_category="rune"),
                AccountGearItem(slot=GearSlot.SIGIL, item_name="Superior Sigil of Force", stat_combo="Sigil", equipment_category="sigil"),
                AccountGearItem(slot=GearSlot.RELIC, item_name="Relic of Durability", stat_combo="Relic", equipment_category="relic"),
            ],
        )

        result = evaluate_build_fit(build, account)
        by_name = {effect.item_name: effect for effect in result.upgrade_effects}

        assert by_name["Superior Rune of the Scholar"].effect_family == "power_damage"
        assert by_name["Superior Rune of the Scholar"].fit_status == "aligned"
        assert by_name["Superior Sigil of Force"].risk_level == "low"
        assert by_name["Relic of Durability"].effect_family == "defensive_survival"
        assert by_name["Relic of Durability"].fit_status == "possibly_misaligned"
        assert "do not auto-replace" in by_name["Relic of Durability"].manual_alternative

        report = render_build_fit_report(result)
        assert "Upgrade Effects" in report
        assert "Relic of Durability" in report
    finally:
        close_database()
