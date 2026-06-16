from gw2radar.kb_pdf.pdf_classifier import classify_pdf, extract_patch_date


def test_pdf_classifier_matches_plan_categories() -> None:
    assert classify_pdf("API_2 - Guild Wars 2 Wiki (GW2W).pdf").category == "official_api"
    assert classify_pdf("API_2_account - Guild Wars 2 Wiki (GW2W).pdf").category == "official_api_endpoint"
    assert classify_pdf("API_Best practices - Guild Wars 2 Wiki (GW2W).pdf").category == "api_governance"
    assert classify_pdf("API_2_tokeninfo - Guild Wars 2 Wiki (GW2W).pdf").category == "api_permission"
    assert classify_pdf("API_API key - Guild Wars 2 Wiki (GW2W).pdf").category == "api_key"
    assert classify_pdf("ArenaNet-security.pdf").category == "arenanet_policy"
    assert classify_pdf("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf").category == "patch_note"
    assert classify_pdf("Guild Wars 2 Wiki.pdf").category == "wiki_meta"
    assert classify_pdf("Gallant Longbow Skin - Guild Wars 2 Wiki (GW2W).pdf").category == "low_priority"


def test_patch_note_priority_and_date_extraction() -> None:
    recent = classify_pdf("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf")
    archive = classify_pdf("Game Update Notes_ June 5, 2018 - Game Update Notes - Guild Wars 2 Forums.pdf")

    assert recent.priority == "P2"
    assert recent.target_relative_dir == "patch_notes/2026"
    assert archive.priority == "P3"
    assert archive.target_relative_dir == "patch_notes/archive_2017_2023"
    assert extract_patch_date("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf") == "2026-06-02"
    assert extract_patch_date("2024-10-08 - October 8th Release Notes - Game Update Notes - Guild Wars 2 Forums.pdf") == "2024-10-08"
