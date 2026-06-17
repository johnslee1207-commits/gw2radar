from enum import StrEnum

from pydantic import BaseModel
from sqlalchemy.orm import Session

from gw2radar.acquisition.models import (
    AcquisitionMode,
    AcquisitionSource,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    GraphTarget,
    KbTarget,
    RefreshMode,
    SourcePolicy,
    SourcePolicyInput,
)
from gw2radar.acquisition.repository import list_sources, register_source, upsert_policy


class AcquisitionSeedPackId(StrEnum):
    MVP_BASELINE = "mvp_baseline"


class AcquisitionSeedEntry(BaseModel):
    seed_key: str
    source: AcquisitionSourceInput
    policy: SourcePolicyInput


class AcquisitionSeedPack(BaseModel):
    pack_id: AcquisitionSeedPackId
    title: str
    summary: str
    entries: list[AcquisitionSeedEntry]


class AcquisitionSeedImportResult(BaseModel):
    pack_id: AcquisitionSeedPackId
    created_count: int
    updated_policy_count: int
    skipped_existing_count: int
    sources: list[AcquisitionSource]
    policies: list[SourcePolicy]


def list_acquisition_seed_packs() -> list[AcquisitionSeedPack]:
    return [get_acquisition_seed_pack(AcquisitionSeedPackId.MVP_BASELINE)]


def get_acquisition_seed_pack(pack_id: AcquisitionSeedPackId | str) -> AcquisitionSeedPack:
    pack_id = AcquisitionSeedPackId(pack_id)
    return AcquisitionSeedPack(
        pack_id=pack_id,
        title="MVP Acquisition Source Baseline",
        summary="Safe default source and policy registry for official API, local PDF, wiki, build, community, and manual evidence.",
        entries=_baseline_entries(),
    )


def import_acquisition_seed_pack(
    session: Session,
    pack_id: AcquisitionSeedPackId | str,
    *,
    confirmed: bool,
) -> AcquisitionSeedImportResult:
    if not confirmed:
        raise ValueError("Importing acquisition seed packs requires confirmation.")
    pack = get_acquisition_seed_pack(pack_id)
    existing_by_key = {_seed_key_for_source(source): source for source in list_sources(session)}
    created_count = 0
    skipped_count = 0
    sources: list[AcquisitionSource] = []
    policies: list[SourcePolicy] = []
    for entry in pack.entries:
        source = existing_by_key.get(entry.seed_key)
        if source is None:
            source = register_source(session, entry.source)
            existing_by_key[entry.seed_key] = source
            created_count += 1
        else:
            skipped_count += 1
        policies.append(upsert_policy(session, source.source_id, entry.policy))
        sources.append(source)
    return AcquisitionSeedImportResult(
        pack_id=pack.pack_id,
        created_count=created_count,
        updated_policy_count=len(policies),
        skipped_existing_count=skipped_count,
        sources=sources,
        policies=policies,
    )


def _baseline_entries() -> list[AcquisitionSeedEntry]:
    return [
        AcquisitionSeedEntry(
            seed_key="official_api_public:items",
            source=AcquisitionSourceInput(
                name="Official GW2 API Public",
                source_type=AcquisitionSourceType.OFFICIAL_API_PUBLIC,
                acquisition_mode=AcquisitionMode.API,
                base_url="https://api.guildwars2.com",
                allowed_use=AllowedUse.API_JSON,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.OFFICIAL,
                trust_level=0.95,
                review_required=False,
                notes="Official public GW2 API source for public game data.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.API_JSON,
                refresh_mode=RefreshMode.SCHEDULED,
                refresh_interval_seconds=3600,
                can_drive_paid_report=True,
                can_drive_strong_recommendation=True,
                forbidden_use=["automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="official_api_private:account",
            source=AcquisitionSourceInput(
                name="Official GW2 API Private Account",
                source_type=AcquisitionSourceType.OFFICIAL_API_PRIVATE,
                acquisition_mode=AcquisitionMode.API,
                base_url="https://api.guildwars2.com",
                allowed_use=AllowedUse.API_JSON,
                graph_target=GraphTarget.PRIVATE_PLAYER_STATE,
                kb_target=KbTarget.NONE,
                trust_level=0.95,
                review_required=False,
                notes="Official private account API. Runtime API keys are read from SecretStore and are never stored in acquisition jobs.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.API_JSON,
                refresh_mode=RefreshMode.USER_TRIGGERED,
                can_drive_paid_report=False,
                can_drive_strong_recommendation=False,
                forbidden_use=["automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="downloaded_pdf:official_sources",
            source=AcquisitionSourceInput(
                name="Downloaded Official PDF Sources",
                source_type=AcquisitionSourceType.DOWNLOADED_PDF,
                acquisition_mode=AcquisitionMode.LOCAL_FILE,
                local_path="docs/knowledge_base/_sources/pdf",
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.OFFICIAL,
                trust_level=0.9,
                notes="Local downloaded PDFs are used by summary and reference, not copied as full text.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=True,
                can_drive_strong_recommendation=False,
                retain_raw_evidence=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="official_patch_note:local_pdf",
            source=AcquisitionSourceInput(
                name="Official Patch Note PDF Sources",
                source_type=AcquisitionSourceType.OFFICIAL_PATCH_NOTE,
                acquisition_mode=AcquisitionMode.LOCAL_FILE,
                local_path="docs/knowledge_base/_sources/pdf/patch_notes",
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.OFFICIAL,
                trust_level=0.9,
                notes="Patch note PDFs require review before rules are persisted or enabled.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=True,
                can_drive_strong_recommendation=False,
                retain_raw_evidence=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="gw2_wiki:summary",
            source=AcquisitionSourceInput(
                name="GW2 Wiki Summary References",
                source_type=AcquisitionSourceType.GW2_WIKI,
                acquisition_mode=AcquisitionMode.WEB_SUMMARY,
                base_url="https://wiki.guildwars2.com",
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.OFFICIAL,
                trust_level=0.75,
                notes="Manual summaries and references only; no full article copying.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=True,
                can_drive_strong_recommendation=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="public_build_site:summary",
            source=AcquisitionSourceInput(
                name="Public Build Site Summary References",
                source_type=AcquisitionSourceType.PUBLIC_BUILD_SITE,
                acquisition_mode=AcquisitionMode.WEB_SUMMARY,
                base_url="https://example.com/builds",
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.BUILD,
                trust_level=0.65,
                notes="Attribution-bound public build summaries, not copied build pages.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=True,
                can_drive_strong_recommendation=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="community_signal:summary",
            source=AcquisitionSourceInput(
                name="Community Signal Summary References",
                source_type=AcquisitionSourceType.COMMUNITY_SIGNAL,
                acquisition_mode=AcquisitionMode.WEB_SUMMARY,
                base_url="https://example.com/community",
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                graph_target=GraphTarget.PUBLIC_GAME,
                kb_target=KbTarget.CREATOR,
                trust_level=0.4,
                notes="Community signals are discovery inputs only until reviewed.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=False,
                can_drive_strong_recommendation=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        ),
        AcquisitionSeedEntry(
            seed_key="manual_note:operator",
            source=AcquisitionSourceInput(
                name="Operator Manual Notes",
                source_type=AcquisitionSourceType.MANUAL_NOTE,
                acquisition_mode=AcquisitionMode.MANUAL,
                allowed_use=AllowedUse.MANUAL_NOTE,
                graph_target=GraphTarget.PERSONAL_INTELLIGENCE,
                kb_target=KbTarget.NONE,
                trust_level=0.6,
                notes="Manual operational notes must stay summary-only and reviewed before use.",
            ),
            policy=SourcePolicyInput(
                allowed_use=AllowedUse.MANUAL_NOTE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=False,
                can_drive_strong_recommendation=False,
                forbidden_use=["automated_trade", "public_private_data_mix"],
            ),
        ),
    ]


def _seed_key_for_source(source: AcquisitionSource) -> str:
    if source.source_type in {AcquisitionSourceType.OFFICIAL_API_PUBLIC, AcquisitionSourceType.OFFICIAL_API_PRIVATE}:
        suffix = "account" if source.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE else "items"
        return f"{source.source_type.value}:{suffix}"
    if source.local_path == "docs/knowledge_base/_sources/pdf":
        return "downloaded_pdf:official_sources"
    if source.local_path == "docs/knowledge_base/_sources/pdf/patch_notes":
        return "official_patch_note:local_pdf"
    if source.source_type == AcquisitionSourceType.GW2_WIKI:
        return "gw2_wiki:summary"
    if source.source_type == AcquisitionSourceType.PUBLIC_BUILD_SITE:
        return "public_build_site:summary"
    if source.source_type == AcquisitionSourceType.COMMUNITY_SIGNAL:
        return "community_signal:summary"
    if source.source_type == AcquisitionSourceType.MANUAL_NOTE:
        return "manual_note:operator"
    return f"{source.source_type.value}:{source.name.strip().lower()}"
