from gw2radar.commercial.build_fit import (
    AccountGearItem,
    AccountGearSnapshot,
    BuildImport,
    BuildSource,
    GearRequirement,
    GearSlot,
)


def sample_build_import() -> BuildImport:
    return BuildImport(
        name="Power Quickness Herald",
        source=BuildSource(
            name="manual_test_fixture",
            url="https://example.invalid/build/herald",
            attribution="Manual test fixture with source link.",
        ),
        profession="Revenant",
        specialization="Herald",
        role="quickness_dps",
        game_mode="strike",
        patch_version="2026-06",
        patch_freshness_days=20,
        difficulty="medium",
        estimated_transition_cost_gold=80,
        requirements=[
            GearRequirement(slot=GearSlot.CHEST, item_name="Ascended Chest", stat_combo="Berserker", estimated_cost_gold=25),
            GearRequirement(slot=GearSlot.WEAPON_1, item_name="Sword", stat_combo="Berserker", estimated_cost_gold=20),
            GearRequirement(slot=GearSlot.RELIC, item_name="Relic of Speed", stat_combo="Power", estimated_cost_gold=10),
        ],
    )


def matching_account_gear() -> AccountGearSnapshot:
    return AccountGearSnapshot(
        profession="Revenant",
        specializations=["Herald"],
        preferred_game_modes=["strike"],
        difficulty_preference="medium",
        wallet_gold=120,
        gear=[
            AccountGearItem(slot=GearSlot.CHEST, item_name="Owned Ascended Chest", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.WEAPON_1, item_name="Owned Sword", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.RELIC, item_name="Owned Relic", stat_combo="Power"),
        ],
    )


def partial_account_gear() -> AccountGearSnapshot:
    return AccountGearSnapshot(
        profession="Revenant",
        specializations=["Herald"],
        preferred_game_modes=["strike"],
        difficulty_preference="medium",
        wallet_gold=15,
        gear=[
            AccountGearItem(slot=GearSlot.CHEST, item_name="Owned Ascended Chest", stat_combo="Berserker"),
        ],
    )
