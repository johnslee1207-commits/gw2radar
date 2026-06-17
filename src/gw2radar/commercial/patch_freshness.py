from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from gw2radar.commercial.build_fit import BuildRecord
from gw2radar.commercial.market_radar import ItemWatch, validate_market_language
from gw2radar.kb.kb_models import KnowledgeReviewStatus
from gw2radar.kb.kb_source_semantics import SourceSemanticExtractionReport
from gw2radar.kb.patch_impact_review import PatchReviewDashboardItem


class FreshnessNoticeKind(StrEnum):
    BUILD = "build"
    MARKET = "market"


class PatchFreshnessNotice(BaseModel):
    kind: FreshnessNoticeKind
    subject_id: str
    subject_name: str
    patch_id: str
    patch_date: str
    reason: str
    review_required: bool = True
    affected_systems: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = "manual_review_only_no_automatic_changes"


class PatchFreshnessReport(BaseModel):
    schema_version: str
    build_notice_count: int
    market_notice_count: int
    source_hint_count: int
    notices: list[PatchFreshnessNotice]


BUILD_AFFECTED_SYSTEMS = {"balance", "build", "profession", "skills", "traits", "game_update"}
MARKET_AFFECTED_SYSTEMS = {"economy", "items", "market", "rewards", "game_update"}


def build_patch_freshness_report(
    builds: list[BuildRecord],
    watchlist: list[ItemWatch],
    patch_items: list[PatchReviewDashboardItem],
    source_semantics: SourceSemanticExtractionReport | None = None,
) -> PatchFreshnessReport:
    source_hint_count = len(source_semantics.hints) if source_semantics else 0
    notices: list[PatchFreshnessNotice] = []
    for build in builds:
        notices.extend(build_freshness_notices(build, patch_items, source_semantics))
    notices.extend(market_freshness_notices(watchlist, patch_items, source_semantics))
    return PatchFreshnessReport(
        schema_version="gw2radar.patch_freshness.v1",
        build_notice_count=sum(1 for notice in notices if notice.kind == FreshnessNoticeKind.BUILD),
        market_notice_count=sum(1 for notice in notices if notice.kind == FreshnessNoticeKind.MARKET),
        source_hint_count=source_hint_count,
        notices=notices,
    )


def build_freshness_notices(
    build: BuildRecord,
    patch_items: list[PatchReviewDashboardItem],
    source_semantics: SourceSemanticExtractionReport | None = None,
) -> list[PatchFreshnessNotice]:
    notices: list[PatchFreshnessNotice] = []
    for item in _reviewed_patch_items(patch_items):
        if not _patch_affects_build(item):
            continue
        if not _patch_is_newer_than_build(item.date, build.patch_version) and build.patch_freshness_days <= 90:
            continue
        notices.append(
            PatchFreshnessNotice(
                kind=FreshnessNoticeKind.BUILD,
                subject_id=build.build_id,
                subject_name=build.name,
                patch_id=item.patch_id,
                patch_date=item.date,
                reason=(
                    f"Reviewed patch impact indicates build-related systems changed after this build source; "
                    f"manually verify {build.name} before relying on fit guidance."
                ),
                affected_systems=item.affected_systems,
                evidence_refs=[item.evidence_id, item.source_pdf],
            )
        )
    notices.extend(_source_build_notices(build, source_semantics))
    return _dedupe_notices(notices)


def market_freshness_notices(
    watchlist: list[ItemWatch],
    patch_items: list[PatchReviewDashboardItem],
    source_semantics: SourceSemanticExtractionReport | None = None,
) -> list[PatchFreshnessNotice]:
    notices: list[PatchFreshnessNotice] = []
    for watch in watchlist:
        for item in _reviewed_patch_items(patch_items):
            if not _patch_affects_market(item):
                continue
            reason = (
                f"Reviewed patch impact indicates market or item systems changed; manually review {watch.item_name} "
                "before changing any watchlist decision."
            )
            validate_market_language(reason)
            notices.append(
                PatchFreshnessNotice(
                    kind=FreshnessNoticeKind.MARKET,
                    subject_id=watch.item_id,
                    subject_name=watch.item_name,
                    patch_id=item.patch_id,
                    patch_date=item.date,
                    reason=reason,
                    affected_systems=item.affected_systems,
                    evidence_refs=[item.evidence_id, item.source_pdf],
                )
            )
        notices.extend(_source_market_notices(watch, source_semantics))
    return _dedupe_notices(notices)


def render_patch_freshness_section(report: PatchFreshnessReport) -> list[str]:
    lines = ["## Patch Freshness Review"]
    if not report.notices:
        return [*lines, "- No reviewed patch freshness notices matched this report."]
    for notice in report.notices:
        lines.append(f"- {notice.subject_name}: {notice.reason}")
        lines.append(f"  - Patch: {notice.patch_id} ({notice.patch_date})")
        lines.append(f"  - Affected systems: {_join(notice.affected_systems)}")
        lines.append(f"  - Evidence refs: {_join(notice.evidence_refs)}")
        lines.append("  - Boundary: manual review only; no automatic gear, build, or market action is performed.")
    return lines


def _reviewed_patch_items(items: list[PatchReviewDashboardItem]) -> list[PatchReviewDashboardItem]:
    return [
        item
        for item in items
        if item.review_status == KnowledgeReviewStatus.REVIEWED
        and item.lifecycle_status in {"reviewed", "persisted", "enabled"}
    ]


def _patch_affects_build(item: PatchReviewDashboardItem) -> bool:
    return bool(set(item.affected_systems) & BUILD_AFFECTED_SYSTEMS or item.possible_build_impact)


def _patch_affects_market(item: PatchReviewDashboardItem) -> bool:
    return bool(set(item.affected_systems) & MARKET_AFFECTED_SYSTEMS or item.possible_market_impact)


def _patch_is_newer_than_build(patch_date: str, build_patch_version: str | None) -> bool:
    if not build_patch_version:
        return True
    try:
        patch_day = date.fromisoformat(patch_date)
        build_parts = build_patch_version.split("-")
        build_day = date(int(build_parts[0]), int(build_parts[1]), int(build_parts[2]) if len(build_parts) > 2 else 1)
    except (ValueError, IndexError):
        return True
    return patch_day > build_day


def _source_build_notices(
    build: BuildRecord,
    source_semantics: SourceSemanticExtractionReport | None,
) -> list[PatchFreshnessNotice]:
    if source_semantics is None:
        return []
    notices: list[PatchFreshnessNotice] = []
    for hint in source_semantics.hints:
        if "review_build_freshness" not in hint.action_hints:
            continue
        notices.append(
            PatchFreshnessNotice(
                kind=FreshnessNoticeKind.BUILD,
                subject_id=build.build_id,
                subject_name=build.name,
                patch_id=hint.source_path,
                patch_date="source_semantic_hint",
                reason="Official source semantic hints indicate build freshness should be manually reviewed.",
                affected_systems=[link.removeprefix("gw2:system:") for link in hint.ontology_links if link.startswith("gw2:system:")],
                evidence_refs=hint.evidence_refs,
            )
        )
    return notices


def _source_market_notices(
    watch: ItemWatch,
    source_semantics: SourceSemanticExtractionReport | None,
) -> list[PatchFreshnessNotice]:
    if source_semantics is None:
        return []
    notices: list[PatchFreshnessNotice] = []
    for hint in source_semantics.hints:
        if "review_market_watchlist" not in hint.action_hints:
            continue
        reason = "Official source semantic hints indicate this watchlist item should be manually reviewed."
        validate_market_language(reason)
        notices.append(
            PatchFreshnessNotice(
                kind=FreshnessNoticeKind.MARKET,
                subject_id=watch.item_id,
                subject_name=watch.item_name,
                patch_id=hint.source_path,
                patch_date="source_semantic_hint",
                reason=reason,
                affected_systems=[link.removeprefix("gw2:system:") for link in hint.ontology_links if link.startswith("gw2:system:")],
                evidence_refs=hint.evidence_refs,
            )
        )
    return notices


def _dedupe_notices(notices: list[PatchFreshnessNotice]) -> list[PatchFreshnessNotice]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[PatchFreshnessNotice] = []
    for notice in notices:
        key = (notice.kind.value, notice.subject_id, notice.patch_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(notice)
    return deduped


def _join(values: list[str]) -> str:
    return ", ".join(value for value in values if value) or "none"
