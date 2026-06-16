from gw2radar.commercial.build_fit import GearSlot
from build_fit_helpers import sample_build_import


def test_build_requirement_schema_preserves_source_attribution() -> None:
    build = sample_build_import()

    assert build.source.name == "manual_test_fixture"
    assert build.source.url == "https://example.invalid/build/herald"
    assert build.requirements[0].slot is GearSlot.CHEST
    assert build.requirements[0].stat_combo == "Berserker"
