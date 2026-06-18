from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import BuildModel, utc_now
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer


DEFAULT_USER_ID = "local-user"


class GearSlot(StrEnum):
    HEAD = "head"
    SHOULDERS = "shoulders"
    CHEST = "chest"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    WEAPON_1 = "weapon_1"
    WEAPON_2 = "weapon_2"
    RUNE = "rune"
    SIGIL = "sigil"
    RELIC = "relic"


class BuildSource(BaseModel):
    name: str = "manual_import"
    url: str | None = None
    attribution: str = "User-provided structured build data."


class GearRequirement(BaseModel):
    slot: GearSlot
    item_name: str
    stat_combo: str
    required: bool = True
    estimated_cost_gold: float = 0.0


class BuildImport(BaseModel):
    name: str
    source: BuildSource = Field(default_factory=BuildSource)
    profession: str
    specialization: str
    role: str
    game_mode: str
    patch_version: str | None = None
    patch_freshness_days: int = 0
    difficulty: str = "medium"
    requirements: list[GearRequirement]
    estimated_transition_cost_gold: float = 0.0


class BuildRecord(BuildImport):
    build_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class AccountGearItem(BaseModel):
    slot: GearSlot
    item_name: str
    stat_combo: str


class AccountGearSnapshot(BaseModel):
    profession: str | None = None
    specializations: list[str] = Field(default_factory=list)
    preferred_game_modes: list[str] = Field(default_factory=list)
    difficulty_preference: str = "medium"
    wallet_gold: float = 0.0
    gear: list[AccountGearItem] = Field(default_factory=list)


class CharacterGearSnapshot(BaseModel):
    snapshot_id: str
    character_name: str
    profession: str
    specialization: str
    level: int = 80
    preferred_game_modes: list[str] = Field(default_factory=list)
    difficulty_preference: str = "medium"
    wallet_gold: float = 0.0
    gear: list[AccountGearItem] = Field(default_factory=list)
    source: str = "manual_sample"
    assumptions: list[str] = Field(default_factory=list)

    def to_account_gear_snapshot(self) -> AccountGearSnapshot:
        return AccountGearSnapshot(
            profession=self.profession,
            specializations=[self.specialization],
            preferred_game_modes=self.preferred_game_modes,
            difficulty_preference=self.difficulty_preference,
            wallet_gold=self.wallet_gold,
            gear=self.gear,
        )


class GearMatchItem(BaseModel):
    requirement: GearRequirement
    matched: bool
    reusable_item_name: str | None = None
    explanation: str


class BuildFitScore(BaseModel):
    build_id: str
    score: float
    playable_now: bool
    gear_match: float
    unlock_match: float
    cost_affordability: float
    difficulty_match: float
    preferred_mode_match: float
    patch_freshness: float
    source_attribution: str
    stale_warning: str | None = None


class GearTransitionPlan(BaseModel):
    build_id: str
    missing_requirements: list[GearMatchItem]
    reusable_requirements: list[GearMatchItem]
    estimated_cost_gold: float
    manual_steps: list[str]
    recommendation_boundary: str = "informational_manual_actions_only"


class BudgetAlternative(BaseModel):
    build_id: str
    suggestion: str
    estimated_savings_gold: float
    explanation: str


class BuildFitResult(BaseModel):
    build: BuildRecord
    matches: list[GearMatchItem]
    score: BuildFitScore
    transition_plan: GearTransitionPlan
    budget_alternative: BudgetAlternative


DEFAULT_CHARACTER_SNAPSHOTS = [
    CharacterGearSnapshot(
        snapshot_id="manual_virtuoso_power",
        character_name="Manual Virtuoso Power Template",
        profession="Mesmer",
        specialization="Virtuoso",
        preferred_game_modes=["Strike", "Open World"],
        difficulty_preference="medium",
        wallet_gold=120,
        gear=[
            AccountGearItem(slot=GearSlot.HEAD, item_name="Manual Power Headgear", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.SHOULDERS, item_name="Manual Power Shoulders", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.CHEST, item_name="Manual Power Chest", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.HANDS, item_name="Manual Power Gloves", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.LEGS, item_name="Manual Power Leggings", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.FEET, item_name="Manual Power Boots", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.WEAPON_1, item_name="Manual Power Dagger", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.WEAPON_2, item_name="Manual Power Focus", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.RUNE, item_name="Manual Power Rune Set", stat_combo="Power"),
            AccountGearItem(slot=GearSlot.SIGIL, item_name="Manual Power Sigil Set", stat_combo="Power"),
            AccountGearItem(slot=GearSlot.RELIC, item_name="Manual Power Relic", stat_combo="Power"),
        ],
        assumptions=[
            "This is a manual sample snapshot, not synced ArenaNet character equipment.",
            "Player should verify actual equipment, runes, sigils, and relics in game.",
        ],
    ),
    CharacterGearSnapshot(
        snapshot_id="manual_reaper_open_world",
        character_name="Manual Reaper Open World Template",
        profession="Necromancer",
        specialization="Reaper",
        preferred_game_modes=["Open World"],
        difficulty_preference="low",
        wallet_gold=80,
        gear=[
            AccountGearItem(slot=GearSlot.CHEST, item_name="Manual Soldier Chest", stat_combo="Soldier"),
            AccountGearItem(slot=GearSlot.WEAPON_1, item_name="Manual Greatsword", stat_combo="Berserker"),
            AccountGearItem(slot=GearSlot.RUNE, item_name="Manual Defensive Rune Set", stat_combo="Defense"),
        ],
        assumptions=[
            "This sample is intentionally imperfect to show missing gear and budget alternatives.",
            "Character selection is advisory until official character equipment sync is wired into this UI.",
        ],
    ),
]


def import_build(session: Session, build: BuildImport, user_id: str = DEFAULT_USER_ID) -> BuildRecord:
    build_id = f"build_{uuid4().hex}"
    now = utc_now()
    row = BuildModel(
        build_id=build_id,
        user_id=user_id,
        name=build.name,
        source_name=build.source.name,
        source_url=build.source.url,
        source_attribution=build.source.attribution,
        profession=build.profession,
        specialization=build.specialization,
        role=build.role,
        game_mode=build.game_mode,
        patch_version=build.patch_version,
        patch_freshness_days=build.patch_freshness_days,
        difficulty=build.difficulty,
        requirements_json=[requirement.model_dump(mode="json") for requirement in build.requirements],
        estimated_transition_cost_gold=build.estimated_transition_cost_gold,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    return _build_from_model(row)


def list_builds(session: Session, user_id: str = DEFAULT_USER_ID) -> list[BuildRecord]:
    rows = (
        session.query(BuildModel)
        .filter(BuildModel.user_id == user_id)
        .order_by(BuildModel.created_at)
        .all()
    )
    return [_build_from_model(row) for row in rows]


def get_build(session: Session, build_id: str) -> BuildRecord | None:
    row = session.get(BuildModel, build_id)
    return _build_from_model(row) if row else None


def list_character_snapshots(graph: GraphData | None = None) -> list[CharacterGearSnapshot]:
    synced = list_synced_character_snapshots(graph) if graph is not None else []
    return [*synced, *DEFAULT_CHARACTER_SNAPSHOTS]


def get_character_snapshot(snapshot_id: str, graph: GraphData | None = None) -> CharacterGearSnapshot | None:
    return next((snapshot for snapshot in list_character_snapshots(graph) if snapshot.snapshot_id == snapshot_id), None)


def list_synced_character_snapshots(graph: GraphData | None) -> list[CharacterGearSnapshot]:
    if graph is None:
        return []
    snapshots: list[CharacterGearSnapshot] = []
    wallet_gold = _wallet_gold(graph)
    for entity in sorted(graph.entities.values(), key=lambda item: item.canonical_name):
        if entity.type is not EntityType.CHARACTER or entity.graph_layer is not GraphLayer.PRIVATE_PLAYER_STATE:
            continue
        if entity.properties.get("sync_detail_status") != "detail_synced":
            continue
        gear = [_account_gear_item(item) for item in entity.properties.get("equipment", [])]
        gear = [item for item in gear if item is not None]
        snapshots.append(
            CharacterGearSnapshot(
                snapshot_id=f"synced_{_safe_snapshot_id(entity.canonical_name)}",
                character_name=entity.canonical_name,
                profession=entity.properties.get("profession") or "Unknown",
                specialization=entity.properties.get("specialization") or entity.properties.get("profession") or "Unknown",
                level=int(entity.properties.get("level") or 80),
                preferred_game_modes=["Open World", "Strike"],
                difficulty_preference="medium",
                wallet_gold=wallet_gold,
                gear=gear,
                source="synced_official_api",
                assumptions=[
                    "This snapshot is derived from synced official GW2 API character data.",
                    "Item names or stat names may require item metadata enrichment when the API only exposes ids.",
                    "GW2Radar never changes equipment; use this for manual planning only.",
                ],
            )
        )
    return snapshots


def evaluate_build_fit(build: BuildRecord, account: AccountGearSnapshot) -> BuildFitResult:
    matches = match_account_gear(build, account)
    score = calculate_build_fit_score(build, account, matches)
    plan = build_transition_plan(build, matches)
    alternative = recommend_budget_alternative(build, plan)
    return BuildFitResult(
        build=build,
        matches=matches,
        score=score,
        transition_plan=plan,
        budget_alternative=alternative,
    )


def match_account_gear(build: BuildRecord, account: AccountGearSnapshot) -> list[GearMatchItem]:
    by_slot = {item.slot: item for item in account.gear}
    matches: list[GearMatchItem] = []
    for requirement in build.requirements:
        owned = by_slot.get(requirement.slot)
        matched = owned is not None and owned.stat_combo.lower() == requirement.stat_combo.lower()
        matches.append(
            GearMatchItem(
                requirement=requirement,
                matched=matched,
                reusable_item_name=owned.item_name if matched and owned else None,
                explanation=(
                    f"{requirement.slot.value} can reuse {owned.item_name}."
                    if matched and owned
                    else f"{requirement.slot.value} needs {requirement.stat_combo} gear for this build."
                ),
            )
        )
    return matches


def calculate_build_fit_score(
    build: BuildRecord,
    account: AccountGearSnapshot,
    matches: list[GearMatchItem],
) -> BuildFitScore:
    required_matches = [match for match in matches if match.requirement.required]
    gear_match = (
        sum(1 for match in required_matches if match.matched) / len(required_matches)
        if required_matches
        else 1.0
    )
    unlock_match = _bool_score(
        (account.profession or "").lower() == build.profession.lower()
        and build.specialization.lower() in {item.lower() for item in account.specializations}
    )
    cost_affordability = min(account.wallet_gold / build.estimated_transition_cost_gold, 1.0) if build.estimated_transition_cost_gold > 0 else 1.0
    difficulty_match = _difficulty_score(build.difficulty, account.difficulty_preference)
    preferred_mode_match = _bool_score(
        not account.preferred_game_modes
        or build.game_mode.lower() in {mode.lower() for mode in account.preferred_game_modes}
    )
    patch_freshness = max(0.0, min(1.0, 1.0 - (build.patch_freshness_days / 180.0)))
    score = (
        0.30 * gear_match
        + 0.20 * unlock_match
        + 0.15 * cost_affordability
        + 0.15 * difficulty_match
        + 0.10 * preferred_mode_match
        + 0.10 * patch_freshness
    )
    return BuildFitScore(
        build_id=build.build_id,
        score=round(score, 3),
        playable_now=gear_match >= 0.8 and unlock_match >= 1.0,
        gear_match=round(gear_match, 3),
        unlock_match=round(unlock_match, 3),
        cost_affordability=round(cost_affordability, 3),
        difficulty_match=round(difficulty_match, 3),
        preferred_mode_match=round(preferred_mode_match, 3),
        patch_freshness=round(patch_freshness, 3),
        source_attribution=build.source.attribution,
        stale_warning="Build data may be stale; verify against current patch notes." if build.patch_freshness_days > 90 else None,
    )


def build_transition_plan(build: BuildRecord, matches: list[GearMatchItem]) -> GearTransitionPlan:
    missing = [match for match in matches if not match.matched]
    reusable = [match for match in matches if match.matched]
    estimated_cost = sum(match.requirement.estimated_cost_gold for match in missing)
    steps = [
        f"Manually review {match.requirement.slot.value} for {match.requirement.stat_combo} replacement."
        for match in missing
    ]
    if not steps:
        steps = ["Current account gear appears reusable for this structured build."]
    return GearTransitionPlan(
        build_id=build.build_id,
        missing_requirements=missing,
        reusable_requirements=reusable,
        estimated_cost_gold=round(estimated_cost, 2),
        manual_steps=steps,
    )


def recommend_budget_alternative(build: BuildRecord, plan: GearTransitionPlan) -> BudgetAlternative:
    if plan.estimated_cost_gold <= 0:
        return BudgetAlternative(
            build_id=build.build_id,
            suggestion="No budget alternative needed.",
            estimated_savings_gold=0.0,
            explanation="The imported build already matches the provided account gear snapshot.",
        )
    savings = round(plan.estimated_cost_gold * 0.35, 2)
    return BudgetAlternative(
        build_id=build.build_id,
        suggestion="Use temporary exotic or stat-selectable alternatives before full ascended conversion.",
        estimated_savings_gold=savings,
        explanation="This is a conservative planning suggestion, not a claim of optimal meta performance.",
    )


def render_build_fit_report(result: BuildFitResult) -> str:
    lines = [
        "# Build Fit Report",
        "",
        f"Build: {result.build.name}",
        f"Source: {result.build.source.name} ({result.build.source.url or 'no url'})",
        f"Attribution: {result.build.source.attribution}",
        "",
        "## Fit Score",
        f"- Score: {result.score.score:.3f}",
        f"- Playable now: {str(result.score.playable_now).lower()}",
        f"- Patch freshness: {result.score.patch_freshness:.3f}",
        "",
        "## Gear Reuse",
        *[f"- {match.explanation}" for match in result.matches],
        "",
        "## Transition Plan",
        *[f"- {step}" for step in result.transition_plan.manual_steps],
        f"- Estimated manual transition cost: {result.transition_plan.estimated_cost_gold:g} gold",
        "",
        "## Budget Alternative",
        f"- {result.budget_alternative.suggestion}",
        f"- Estimated savings: {result.budget_alternative.estimated_savings_gold:g} gold",
        "",
        "## Boundaries",
        "- Recommendations are informational only.",
        "- No gameplay automation or automatic gear changes are performed.",
        "- Build source attribution is preserved.",
    ]
    if result.score.stale_warning:
        lines.extend(["", "## Freshness Warning", f"- {result.score.stale_warning}"])
    return "\n".join(lines) + "\n"


def _build_from_model(row: BuildModel) -> BuildRecord:
    return BuildRecord(
        build_id=row.build_id,
        user_id=row.user_id,
        name=row.name,
        source=BuildSource(
            name=row.source_name,
            url=row.source_url,
            attribution=row.source_attribution,
        ),
        profession=row.profession,
        specialization=row.specialization,
        role=row.role,
        game_mode=row.game_mode,
        patch_version=row.patch_version,
        patch_freshness_days=row.patch_freshness_days,
        difficulty=row.difficulty,
        requirements=[GearRequirement(**requirement) for requirement in row.requirements_json],
        estimated_transition_cost_gold=row.estimated_transition_cost_gold,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _bool_score(value: bool) -> float:
    return 1.0 if value else 0.0


def _difficulty_score(build_difficulty: str, preference: str) -> float:
    levels = {"low": 1, "medium": 2, "high": 3}
    build_level = levels.get(build_difficulty.lower(), 2)
    preferred_level = levels.get(preference.lower(), 2)
    return 1.0 if build_level <= preferred_level else 0.5


def _account_gear_item(item: dict) -> AccountGearItem | None:
    slot = _map_official_slot(str(item.get("slot") or ""))
    if slot is None:
        return None
    return AccountGearItem(
        slot=slot,
        item_name=str(item.get("item_name") or f"Item {item.get('item_id', 'unknown')}"),
        stat_combo=str(item.get("stat_combo") or "Unknown"),
    )


def _map_official_slot(slot: str) -> GearSlot | None:
    normalized = slot.lower()
    mapping = {
        "helm": GearSlot.HEAD,
        "head": GearSlot.HEAD,
        "shoulders": GearSlot.SHOULDERS,
        "coat": GearSlot.CHEST,
        "chest": GearSlot.CHEST,
        "gloves": GearSlot.HANDS,
        "hands": GearSlot.HANDS,
        "leggings": GearSlot.LEGS,
        "legs": GearSlot.LEGS,
        "boots": GearSlot.FEET,
        "feet": GearSlot.FEET,
        "weapona1": GearSlot.WEAPON_1,
        "weaponb1": GearSlot.WEAPON_1,
        "weapon_1": GearSlot.WEAPON_1,
        "weapona2": GearSlot.WEAPON_2,
        "weaponb2": GearSlot.WEAPON_2,
        "weapon_2": GearSlot.WEAPON_2,
        "rune": GearSlot.RUNE,
        "sigil": GearSlot.SIGIL,
        "relic": GearSlot.RELIC,
    }
    return mapping.get(normalized)


def _wallet_gold(graph: GraphData) -> float:
    return round(
        sum(state.quantity for state in graph.player_state if state.entity_id in {"gw2:currency:1", "gw2:currency:gold"})
        / 10000,
        2,
    )


def _safe_snapshot_id(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "character"
