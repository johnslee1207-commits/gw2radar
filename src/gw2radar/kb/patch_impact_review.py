import os
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRule, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule, list_rules
from gw2radar.ontology.action_types import ActionType


DEFAULT_PATCH_SUMMARY_ROOT = Path("docs") / "knowledge_base" / "patch_notes"
DEFAULT_PATCH_REVIEW_STORE = Path("data") / "kb" / "patch_impact_reviews.jsonl"
PATCH_REVIEW_STORE_ENV = "GW2RADAR_PATCH_REVIEW_STORE"

ALLOWED_AFFECTED_SYSTEMS = {
    "achievements",
    "balance",
    "build",
    "economy",
    "game_update",
    "items",
    "legendary",
    "market",
    "patch_notes",
    "profession",
    "release_notes",
    "rewards",
    "skills",
    "traits",
    "wvw",
}


class PatchImpactDraft(BaseModel):
    patch_id: str
    date: str
    year: int
    title: str
    summary_path: str
    source_pdf: str
    evidence_id: str
    review_status: KnowledgeReviewStatus
    affected_systems: list[str] = Field(default_factory=list)
    possible_build_impact: list[str] = Field(default_factory=list)
    possible_market_impact: list[str] = Field(default_factory=list)


class PatchImpactReviewInput(BaseModel):
    patch_id: str
    affected_systems: list[str] = Field(default_factory=list)
    build_impact: list[str] = Field(default_factory=list)
    market_impact: list[str] = Field(default_factory=list)
    reviewer: str = "manual_reviewer"
    notes: str = ""
    review_status: KnowledgeReviewStatus = KnowledgeReviewStatus.REVIEWED

    @model_validator(mode="after")
    def validate_review_contract(self) -> "PatchImpactReviewInput":
        if self.review_status not in {KnowledgeReviewStatus.REVIEWED, KnowledgeReviewStatus.NEEDS_UPDATE}:
            raise ValueError("Patch impact reviews must be reviewed or needs_update.")
        for system in self.affected_systems:
            if system not in ALLOWED_AFFECTED_SYSTEMS:
                raise ValueError(f"Unsupported affected system: {system}")
        if not self.affected_systems:
            raise ValueError("At least one affected system is required for patch impact review.")
        if not self.build_impact and not self.market_impact:
            raise ValueError("At least one build or market impact is required for patch impact review.")
        return self


class PatchImpactReview(PatchImpactReviewInput):
    reviewed_at: datetime


class PatchKnowledgeRuleCandidate(BaseModel):
    patch_id: str
    rules: list[KnowledgeRuleInput]


class PersistedPatchRuleCandidate(BaseModel):
    patch_id: str
    created_count: int
    skipped_existing_count: int
    rules: list[KnowledgeRule]


def list_patch_impact_drafts(
    summary_root: Path | None = None,
    review_store: Path | None = None,
    year: int | None = None,
) -> list[PatchImpactDraft]:
    summary_root = _resolve_summary_root(summary_root)
    review_store = _resolve_review_store(review_store)
    reviewed = load_patch_reviews(review_store)
    drafts = [_parse_patch_summary(path) for path in sorted(summary_root.glob("*/*.md"))]
    if year is not None:
        drafts = [draft for draft in drafts if draft.year == year]
    merged: list[PatchImpactDraft] = []
    for draft in sorted(drafts, key=lambda item: item.date, reverse=True):
        review = reviewed.get(draft.patch_id)
        if review is None:
            merged.append(draft)
            continue
        merged.append(
            draft.model_copy(
                update={
                    "review_status": review.review_status,
                    "affected_systems": review.affected_systems,
                    "possible_build_impact": review.build_impact,
                    "possible_market_impact": review.market_impact,
                }
            )
        )
    return merged


def list_pending_patch_impact_drafts(
    summary_root: Path | None = None,
    review_store: Path | None = None,
    year: int | None = None,
) -> list[PatchImpactDraft]:
    return [
        draft
        for draft in list_patch_impact_drafts(summary_root, review_store, year)
        if draft.review_status != KnowledgeReviewStatus.REVIEWED
    ]


def save_patch_impact_review(
    review_input: PatchImpactReviewInput,
    summary_root: Path | None = None,
    review_store: Path | None = None,
) -> PatchImpactReview:
    summary_root = _resolve_summary_root(summary_root)
    review_store = _resolve_review_store(review_store)
    drafts_by_id = {draft.patch_id: draft for draft in list_patch_impact_drafts(summary_root, review_store)}
    if review_input.patch_id not in drafts_by_id:
        raise ValueError(f"Unknown patch summary: {review_input.patch_id}")
    review = PatchImpactReview(
        **review_input.model_dump(),
        reviewed_at=datetime.now(UTC),
    )
    reviews = load_patch_reviews(review_store)
    reviews[review.patch_id] = review
    _write_reviews(reviews, review_store)
    return review


def load_patch_reviews(review_store: Path | None = None) -> dict[str, PatchImpactReview]:
    review_store = _resolve_review_store(review_store)
    if not review_store.exists():
        return {}
    reviews: dict[str, PatchImpactReview] = {}
    for line in review_store.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        review = PatchImpactReview.model_validate_json(line)
        reviews[review.patch_id] = review
    return reviews


def build_patch_rule_candidates(
    patch_id: str,
    summary_root: Path | None = None,
    review_store: Path | None = None,
) -> PatchKnowledgeRuleCandidate:
    summary_root = _resolve_summary_root(summary_root)
    review_store = _resolve_review_store(review_store)
    drafts_by_id = {draft.patch_id: draft for draft in list_patch_impact_drafts(summary_root, review_store)}
    draft = drafts_by_id.get(patch_id)
    if draft is None:
        raise ValueError(f"Unknown patch summary: {patch_id}")
    review = load_patch_reviews(review_store).get(patch_id)
    if review is None or review.review_status != KnowledgeReviewStatus.REVIEWED:
        raise ValueError("Patch impact rule candidates require a reviewed patch impact record.")

    rules: list[KnowledgeRuleInput] = []
    if review.build_impact:
        rules.append(_build_rule_for_impact(draft, review, "build", review.build_impact))
    if review.market_impact:
        rules.append(_build_rule_for_impact(draft, review, "market", review.market_impact))
    return PatchKnowledgeRuleCandidate(patch_id=patch_id, rules=rules)


def persist_patch_rule_candidates(
    session: Session,
    patch_id: str,
    confirmed: bool,
    summary_root: Path | None = None,
    review_store: Path | None = None,
) -> PersistedPatchRuleCandidate:
    if not confirmed:
        raise ValueError("Persisting patch rule candidates requires explicit manual confirmation.")
    candidates = build_patch_rule_candidates(patch_id, summary_root, review_store)
    existing_signatures = {
        (rule.condition, rule.action_type)
        for rule in list_rules(session)
    }
    persisted = []
    created_count = 0
    skipped_count = 0
    for candidate in candidates.rules:
        safe_candidate = candidate.model_copy(update={"enabled": False})
        signature = (safe_candidate.condition, safe_candidate.action_type)
        if signature in existing_signatures:
            skipped_count += 1
            continue
        persisted.append(create_rule(session, safe_candidate))
        existing_signatures.add(signature)
        created_count += 1
    return PersistedPatchRuleCandidate(
        patch_id=patch_id,
        created_count=created_count,
        skipped_existing_count=skipped_count,
        rules=persisted,
    )


def _build_rule_for_impact(
    draft: PatchImpactDraft,
    review: PatchImpactReview,
    impact_kind: str,
    impacts: list[str],
) -> KnowledgeRuleInput:
    action_type = ActionType.COMPLETE_ACHIEVEMENT.value if impact_kind == "build" else ActionType.WATCH_PRICE.value
    domain = KnowledgeDomain.BUILD if impact_kind == "build" else KnowledgeDomain.MARKET
    impact_text = "; ".join(impacts)
    systems = ", ".join(review.affected_systems)
    return KnowledgeRuleInput(
        name=f"{draft.patch_id} {impact_kind} impact",
        domain=domain,
        condition=f"patch_review:{draft.patch_id}:affected_systems:{','.join(review.affected_systems)}",
        recommendation=f"Review {impact_kind} planning after {draft.patch_id}: {impact_text}",
        action_type=action_type,
        priority_delta=0.3,
        explanation_template=(
            f"Official patch note {draft.date} was reviewed by {review.reviewer}; "
            f"affected systems: {systems}. Impact notes: {impact_text}."
        ),
        evidence_refs=[draft.evidence_id, draft.source_pdf],
        confidence=0.75,
        review_status=KnowledgeReviewStatus.REVIEWED,
        enabled=False,
    )


def _parse_patch_summary(path: Path) -> PatchImpactDraft:
    text = path.read_text(encoding="utf-8")
    date = _first_match(r"- date: `([^`]+)`", text) or path.stem
    patch_id = _first_match(r"- patch_id: `([^`]+)`", text) or f"patch:{date}"
    return PatchImpactDraft(
        patch_id=patch_id,
        date=date,
        year=int(path.parent.name),
        title=_first_match(r"^# (.+)$", text, re.MULTILINE) or f"GW2 Patch Note {date}",
        summary_path=str(path),
        source_pdf=_first_match(r"- source_pdf: `([^`]+)`", text) or "",
        evidence_id=_first_match(r"- evidence_id: `([^`]+)`", text) or "",
        review_status=KnowledgeReviewStatus(_first_match(r"- review_status: `([^`]+)`", text) or "draft"),
        affected_systems=_parse_inline_list("affected_systems", text),
        possible_build_impact=_parse_inline_list("possible_build_impact", text),
        possible_market_impact=_parse_inline_list("possible_market_impact", text),
    )


def _parse_inline_list(name: str, text: str) -> list[str]:
    value = _first_match(rf"- {re.escape(name)}: \[(.*?)\]", text)
    if value is None or not value.strip():
        return []
    return [part.strip().strip("`").strip() for part in value.split(",") if part.strip()]


def _first_match(pattern: str, text: str, flags: int = 0) -> str | None:
    match = re.search(pattern, text, flags)
    if match is None:
        return None
    return match.group(1).strip()


def _write_reviews(reviews: dict[str, PatchImpactReview], review_store: Path) -> None:
    review_store.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        reviews[patch_id].model_dump_json()
        for patch_id in sorted(reviews)
    ]
    review_store.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _resolve_summary_root(summary_root: Path | None) -> Path:
    return summary_root or DEFAULT_PATCH_SUMMARY_ROOT


def _resolve_review_store(review_store: Path | None) -> Path:
    if review_store is not None:
        return review_store
    env_path = os.environ.get(PATCH_REVIEW_STORE_ENV)
    return Path(env_path) if env_path else DEFAULT_PATCH_REVIEW_STORE
