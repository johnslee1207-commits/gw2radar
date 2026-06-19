from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


RouteStepType = Literal["achievement", "collection"]
RouteTimeGate = Literal["daily", "weekly", "none"]
RouteSourceStatus = Literal["reviewed", "draft", "disabled"]
RouteAccountProgressStatus = Literal["unknown", "not_started", "in_progress", "complete"]


ACHIEVEMENT_ROUTE_SOURCE_ROOT = Path("docs/knowledge_base/achievement_routes")


class AchievementRouteRequest(BaseModel):
    user_id: str = "local-user"
    goal_id: str = "aurora_sample"
    available_minutes: int = Field(default=45, ge=10, le=240)
    completed_step_ids: list[str] = Field(default_factory=list)
    unlocked_prerequisite_ids: list[str] = Field(default_factory=list)
    include_group_content: bool = False


class AchievementRouteStep(BaseModel):
    step_id: str
    title: str
    step_type: RouteStepType
    map_name: str
    region: str
    objective: str
    advances_goal_id: str
    prerequisite_ids: list[str] = Field(default_factory=list)
    time_gate: RouteTimeGate = "none"
    estimated_minutes: int = Field(ge=1)
    group_required: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_id: str = "kb:seed:legendary-route:v1"
    source_status: RouteSourceStatus = "reviewed"
    official_achievement_id: int | None = None
    account_progress_status: RouteAccountProgressStatus = "unknown"
    account_progress_note: str | None = None


class AchievementRouteSegment(BaseModel):
    segment_id: str
    map_name: str
    region: str
    ready_step_ids: list[str]
    blocked_step_ids: list[str]
    time_gated_step_ids: list[str]
    total_ready_minutes: int
    notes: list[str] = Field(default_factory=list)


class AchievementRouteAction(BaseModel):
    action_id: str
    action_type: Literal["run_segment", "unlock_prerequisite", "do_time_gated_step", "postpone_blocked_step"]
    title: str
    step_ids: list[str]
    reason: str
    manual_only: bool = True


class AchievementRoutePlan(BaseModel):
    schema_version: str = "gw2radar.achievement_route_plan.v1"
    route_id: str
    user_id: str
    goal_id: str
    generated_at: datetime
    available_minutes: int
    steps: list[AchievementRouteStep]
    segments: list[AchievementRouteSegment]
    ready_step_ids: list[str]
    blocked_step_ids: list[str]
    time_gated_step_ids: list[str]
    next_actions: list[AchievementRouteAction]
    source_ids: list[str]
    source_warnings: list[str]
    assumptions: list[str]
    safety_boundaries: list[str]


class AchievementRouteSourceManifest(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source.v1"
    source_id: str
    title: str
    source_status: RouteSourceStatus = "reviewed"
    source_url: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    reviewed_by: str
    reviewed_at: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[AchievementRouteStep]


class AchievementRouteSourceSummary(BaseModel):
    source_id: str
    title: str
    source_status: RouteSourceStatus
    source_url: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    step_count: int = 0
    warning: str | None = None


class OfficialAchievementDetail(BaseModel):
    id: int
    name: str
    description: str | None = None
    requirement: str | None = None
    locked_text: str | None = None
    type: str | None = None
    flags: list[str] = Field(default_factory=list)
    bits: list[dict] = Field(default_factory=list)


class OfficialAccountAchievementProgress(BaseModel):
    id: int
    current: int | None = None
    max: int | None = None
    done: bool | None = None


class OfficialAchievementRoutePreviewRequest(BaseModel):
    source_id: str = "official:achievement-route-preview"
    title: str = "Official achievement route preview"
    goal_id: str = "custom_achievement_route"
    reviewed_by: str = "operator_review_required"
    achievement_details: list[OfficialAchievementDetail]
    account_achievements: list[OfficialAccountAchievementProgress] = Field(default_factory=list)
    source_refs: list[str] = Field(
        default_factory=lambda: [
            "official:/v2/achievements",
            "official:/v2/account/achievements",
        ]
    )


class OfficialAchievementRoutePreview(BaseModel):
    schema_version: str = "gw2radar.official_achievement_route_preview.v1"
    manifest: AchievementRouteSourceManifest
    source_summary: AchievementRouteSourceSummary
    candidate_step_count: int
    completed_step_ids: list[str]
    warnings: list[str]


SAMPLE_ROUTE_STEPS: tuple[AchievementRouteStep, ...] = (
    AchievementRouteStep(
        step_id="aurora-bloodstone-fen-check",
        title="Bloodstone Fen collection sweep",
        step_type="collection",
        map_name="Bloodstone Fen",
        region="Maguuma Wastes",
        objective="Check unlocked local collection progress and finish one visible map-bound objective.",
        advances_goal_id="aurora_sample",
        prerequisite_ids=["living_world_s3_access"],
        estimated_minutes=15,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Sample route seed; verify the exact in-game achievement panel before execution."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="aurora-ember-bay-daily-token",
        title="Ember Bay daily token pass",
        step_type="collection",
        map_name="Ember Bay",
        region="Ring of Fire",
        objective="Do one short account-progress pass tied to the active legendary collection.",
        advances_goal_id="aurora_sample",
        prerequisite_ids=["living_world_s3_access"],
        time_gate="daily",
        estimated_minutes=12,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Daily availability is represented as a planning gate, not a guarantee of current rotation."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="vision-dragonfall-meta",
        title="Dragonfall group event checkpoint",
        step_type="achievement",
        map_name="Dragonfall",
        region="Crystal Desert",
        objective="Reserve time for a group/meta checkpoint if the account is also advancing Vision-like goals.",
        advances_goal_id="vision_sample",
        prerequisite_ids=["living_world_s4_access"],
        time_gate="weekly",
        estimated_minutes=25,
        group_required=True,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Group event timing must be confirmed in game or with the squad before committing the session."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="fractals-ad-infinitum-check",
        title="Fractal collection checkpoint",
        step_type="achievement",
        map_name="Fractals of the Mists",
        region="Mistlock Observatory",
        objective="Check one fractal collection blocker and defer if group or tier access is missing.",
        advances_goal_id="ad_infinitum_sample",
        prerequisite_ids=["fractal_access"],
        estimated_minutes=20,
        group_required=True,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Fractal tier, instability, and group readiness are player-provided facts until synced or entered."],
        source_id="kb:seed:legendary-route:v1",
    ),
)


def build_achievement_route_plan(
    request: AchievementRouteRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> AchievementRoutePlan:
    source_steps, source_summaries = load_reviewed_achievement_route_steps(source_root)
    route_steps = source_steps or list(SAMPLE_ROUTE_STEPS)
    source_warnings = [
        summary.warning for summary in source_summaries if summary.warning
    ]
    if not source_steps:
        source_warnings.append("No reviewed achievement route source manifests were loaded; using built-in MVP fallback seed.")

    completed = set(request.completed_step_ids)
    unlocked = set(request.unlocked_prerequisite_ids)
    candidate_steps = [
        step
        for step in route_steps
        if step.step_id not in completed and (request.goal_id == "all" or step.advances_goal_id == request.goal_id)
    ]
    if not candidate_steps:
        candidate_steps = [step for step in route_steps if step.step_id not in completed]

    ready: list[str] = []
    blocked: list[str] = []
    time_gated: list[str] = []
    for step in candidate_steps:
        missing_prereqs = [prereq for prereq in step.prerequisite_ids if prereq not in unlocked]
        if missing_prereqs or (step.group_required and not request.include_group_content):
            blocked.append(step.step_id)
            continue
        if step.time_gate != "none":
            time_gated.append(step.step_id)
        ready.append(step.step_id)

    segments = _build_segments(candidate_steps, ready, blocked, time_gated)
    limited_ready = _fit_ready_steps(candidate_steps, ready, request.available_minutes)
    actions = _build_actions(candidate_steps, segments, limited_ready, blocked, time_gated, request.available_minutes)
    return AchievementRoutePlan(
        route_id=f"route:{request.user_id}:{request.goal_id}",
        user_id=request.user_id,
        goal_id=request.goal_id,
        generated_at=datetime.now(UTC),
        available_minutes=request.available_minutes,
        steps=candidate_steps,
        segments=segments,
        ready_step_ids=limited_ready,
        blocked_step_ids=blocked,
        time_gated_step_ids=time_gated,
        next_actions=actions,
        source_ids=_unique([step.source_id for step in candidate_steps]),
        source_warnings=_unique(source_warnings),
        assumptions=_unique(
            [
                "This MVP planner uses reviewed KB route source manifests plus player-provided prerequisite state.",
                "Exact achievement step completion must be checked in the in-game achievement panel.",
                *[assumption for step in candidate_steps for assumption in step.assumptions],
            ]
        ),
        safety_boundaries=[
            "Manual planning only; GW2Radar does not automate gameplay, squad joining, trading, or collection completion.",
            "Routes are advisory and must be verified against current account state and current patch context.",
        ],
    )


def render_achievement_route_markdown(plan: AchievementRoutePlan) -> str:
    step_by_id = {step.step_id: step for step in plan.steps}
    lines = [
        "# Achievement & Collection Route Plan",
        "",
        f"- User: {plan.user_id}",
        f"- Goal: {plan.goal_id}",
        f"- Available minutes: {plan.available_minutes}",
        f"- Ready steps: {len(plan.ready_step_ids)}",
        f"- Blocked steps: {len(plan.blocked_step_ids)}",
        f"- Sources: {', '.join(plan.source_ids) if plan.source_ids else 'none'}",
        "",
        "## Route Segments",
    ]
    for segment in plan.segments:
        lines.extend(
            [
                f"### {segment.map_name}",
                f"- Region: {segment.region}",
                f"- Ready minutes: {segment.total_ready_minutes}",
                f"- Ready: {_step_titles(step_by_id, segment.ready_step_ids) or 'none'}",
                f"- Blocked: {_step_titles(step_by_id, segment.blocked_step_ids) or 'none'}",
                f"- Time gated: {_step_titles(step_by_id, segment.time_gated_step_ids) or 'none'}",
            ]
        )
        lines.extend([f"- Note: {note}" for note in segment.notes])
        lines.append("")
    lines.extend(["## Next Actions"])
    lines.extend([f"- {action.title}: {action.reason}" for action in plan.next_actions] or ["- No route actions available."])
    lines.extend(["", "## Source Warnings"])
    lines.extend([f"- {warning}" for warning in plan.source_warnings] or ["- None"])
    lines.extend(["", "## Assumptions"])
    lines.extend([f"- {assumption}" for assumption in plan.assumptions])
    lines.extend(["", "## Safety Boundaries"])
    lines.extend([f"- {boundary}" for boundary in plan.safety_boundaries])
    return "\n".join(lines) + "\n"


def render_achievement_route_csv(plan: AchievementRoutePlan) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "step_id",
            "title",
            "map_name",
            "region",
            "status",
            "time_gate",
            "estimated_minutes",
            "objective",
            "evidence_refs",
            "source_id",
        ]
    )
    for step in plan.steps:
        status = "ready"
        if step.step_id in plan.blocked_step_ids:
            status = "blocked"
        elif step.step_id in plan.time_gated_step_ids:
            status = "time_gated"
        writer.writerow(
            [
                step.step_id,
                step.title,
                step.map_name,
                step.region,
                status,
                step.time_gate,
                step.estimated_minutes,
                step.objective,
                ";".join(step.evidence_refs),
                step.source_id,
            ]
        )
    return buffer.getvalue()


def load_reviewed_achievement_route_steps(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> tuple[list[AchievementRouteStep], list[AchievementRouteSourceSummary]]:
    manifests = load_achievement_route_source_manifests(source_root)
    reviewed_steps: list[AchievementRouteStep] = []
    summaries: list[AchievementRouteSourceSummary] = []
    for manifest in manifests:
        if isinstance(manifest, AchievementRouteSourceSummary):
            summaries.append(manifest)
            continue
        if manifest.source_status != "reviewed":
            summaries.append(
                AchievementRouteSourceSummary(
                    source_id=manifest.source_id,
                    title=manifest.title,
                    source_status=manifest.source_status,
                    source_url=manifest.source_url,
                    source_refs=manifest.source_refs,
                    reviewed_by=manifest.reviewed_by,
                    reviewed_at=manifest.reviewed_at,
                    step_count=0,
                    warning=f"{manifest.source_id} skipped because status is {manifest.source_status}.",
                )
            )
            continue
        steps = [
            step.model_copy(
                update={
                    "source_id": manifest.source_id,
                    "source_status": manifest.source_status,
                    "evidence_refs": _unique([*step.evidence_refs, *manifest.source_refs, manifest.source_id]),
                    "assumptions": _unique([*manifest.assumptions, *step.assumptions]),
                }
            )
            for step in manifest.steps
        ]
        reviewed_steps.extend(steps)
        summaries.append(
            AchievementRouteSourceSummary(
                source_id=manifest.source_id,
                title=manifest.title,
                source_status=manifest.source_status,
                source_url=manifest.source_url,
                source_refs=manifest.source_refs,
                reviewed_by=manifest.reviewed_by,
                reviewed_at=manifest.reviewed_at,
                step_count=len(steps),
            )
        )
    return reviewed_steps, summaries


def load_achievement_route_source_manifests(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> list[AchievementRouteSourceManifest | AchievementRouteSourceSummary]:
    if not source_root.exists():
        return [
            AchievementRouteSourceSummary(
                source_id="missing:achievement-route-source-root",
                title="Achievement route source root",
                source_status="disabled",
                warning=f"Source root not found: {source_root.as_posix()}",
            )
        ]
    manifests: list[AchievementRouteSourceManifest | AchievementRouteSourceSummary] = []
    for path in sorted(source_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            manifest = AchievementRouteSourceManifest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            manifests.append(
                AchievementRouteSourceSummary(
                    source_id=f"invalid:{path.name}",
                    title=path.name,
                    source_status="disabled",
                    warning=f"{path.as_posix()} could not be loaded: {exc}",
                )
            )
            continue
        manifests.append(manifest)
    if not manifests:
        manifests.append(
            AchievementRouteSourceSummary(
                source_id="empty:achievement-route-source-root",
                title="Achievement route source root",
                source_status="disabled",
                warning=f"No route manifest JSON files found in {source_root.as_posix()}",
            )
        )
    return manifests


def build_official_achievement_route_preview(
    request: OfficialAchievementRoutePreviewRequest,
) -> OfficialAchievementRoutePreview:
    progress_by_id = {item.id: item for item in request.account_achievements}
    steps: list[AchievementRouteStep] = []
    warnings = [
        "Generated preview is draft-only. Save it as a reviewed source manifest only after human verification.",
        "Official achievement details do not always contain map or route order; inferred map fields must be reviewed.",
    ]
    for detail in sorted(request.achievement_details, key=lambda item: (item.name.lower(), item.id)):
        progress = progress_by_id.get(detail.id)
        progress_status, progress_note = _official_progress_status(progress)
        map_name, region, map_assumption = _infer_official_route_location(detail)
        time_gate = _infer_official_time_gate(detail)
        group_required = _infer_official_group_required(detail)
        step_id = f"official-achievement-{detail.id}"
        objective = _official_objective(detail)
        assumptions = _unique(
            [
                "Official achievement detail imported as a draft route candidate, not reviewed guidance.",
                map_assumption,
                "Route order, waypoint choice, and collection substeps require human review.",
            ]
        )
        steps.append(
            AchievementRouteStep(
                step_id=step_id,
                title=detail.name,
                step_type="achievement",
                map_name=map_name,
                region=region,
                objective=objective,
                advances_goal_id=request.goal_id,
                prerequisite_ids=["achievement_api_access"],
                time_gate=time_gate,
                estimated_minutes=_estimate_official_minutes(detail, group_required),
                group_required=group_required,
                evidence_refs=_unique([*request.source_refs, f"official:/v2/achievements/{detail.id}"]),
                assumptions=assumptions,
                source_id=request.source_id,
                source_status="draft",
                official_achievement_id=detail.id,
                account_progress_status=progress_status,
                account_progress_note=progress_note,
            )
        )
    manifest = AchievementRouteSourceManifest(
        source_id=request.source_id,
        title=request.title,
        source_status="draft",
        source_url="official:/v2/achievements",
        source_refs=request.source_refs,
        reviewed_by=request.reviewed_by,
        reviewed_at=datetime.now(UTC).date().isoformat(),
        assumptions=[
            "This draft source was generated from official achievement/account-achievement payloads.",
            "Human review is required before changing source_status to reviewed.",
            "No raw API key or private account payload is stored in this manifest.",
        ],
        steps=steps,
    )
    summary = AchievementRouteSourceSummary(
        source_id=manifest.source_id,
        title=manifest.title,
        source_status=manifest.source_status,
        source_url=manifest.source_url,
        source_refs=manifest.source_refs,
        reviewed_by=manifest.reviewed_by,
        reviewed_at=manifest.reviewed_at,
        step_count=len(steps),
        warning="Draft official preview requires human review before route planner ingestion.",
    )
    return OfficialAchievementRoutePreview(
        manifest=manifest,
        source_summary=summary,
        candidate_step_count=len(steps),
        completed_step_ids=[step.step_id for step in steps if step.account_progress_status == "complete"],
        warnings=warnings,
    )


def render_official_achievement_route_preview_markdown(preview: OfficialAchievementRoutePreview) -> str:
    lines = [
        "# Official Achievement Route Preview",
        "",
        f"- Source: {preview.manifest.source_id}",
        f"- Status: {preview.manifest.source_status}",
        f"- Candidate steps: {preview.candidate_step_count}",
        f"- Completed from account progress: {len(preview.completed_step_ids)}",
        "",
        "## Candidate Steps",
    ]
    for step in preview.manifest.steps:
        lines.extend(
            [
                f"- {step.title}",
                f"  - Achievement id: {step.official_achievement_id}",
                f"  - Map: {step.map_name}",
                f"  - Progress: {step.account_progress_status} ({step.account_progress_note or 'no account progress supplied'})",
                f"  - Evidence: {', '.join(step.evidence_refs)}",
            ]
        )
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {warning}" for warning in preview.warnings])
    lines.extend(["", "## Assumptions"])
    lines.extend([f"- {assumption}" for assumption in preview.manifest.assumptions])
    return "\n".join(lines) + "\n"


def _build_segments(
    steps: list[AchievementRouteStep],
    ready: list[str],
    blocked: list[str],
    time_gated: list[str],
) -> list[AchievementRouteSegment]:
    segment_index: dict[str, list[AchievementRouteStep]] = {}
    for step in steps:
        segment_index.setdefault(step.map_name, []).append(step)
    segments: list[AchievementRouteSegment] = []
    for map_name, map_steps in segment_index.items():
        ready_ids = [step.step_id for step in map_steps if step.step_id in ready]
        blocked_ids = [step.step_id for step in map_steps if step.step_id in blocked]
        gated_ids = [step.step_id for step in map_steps if step.step_id in time_gated]
        total = sum(step.estimated_minutes for step in map_steps if step.step_id in ready_ids)
        notes = []
        if blocked_ids:
            notes.append("Resolve prerequisites or enable group-content planning before adding blocked steps.")
        if gated_ids:
            notes.append("Treat daily/weekly labels as scheduling gates and verify current reset state.")
        segments.append(
            AchievementRouteSegment(
                segment_id=f"segment:{_slug(map_name)}",
                map_name=map_name,
                region=map_steps[0].region,
                ready_step_ids=ready_ids,
                blocked_step_ids=blocked_ids,
                time_gated_step_ids=gated_ids,
                total_ready_minutes=total,
                notes=notes,
            )
        )
    return sorted(segments, key=lambda segment: (not segment.ready_step_ids, segment.map_name))


def _fit_ready_steps(steps: list[AchievementRouteStep], ready_ids: list[str], minutes: int) -> list[str]:
    fitted: list[str] = []
    spent = 0
    for step in sorted((step for step in steps if step.step_id in ready_ids), key=lambda item: item.estimated_minutes):
        if spent + step.estimated_minutes > minutes and fitted:
            continue
        fitted.append(step.step_id)
        spent += step.estimated_minutes
        if spent >= minutes:
            break
    return fitted


def _build_actions(
    steps: list[AchievementRouteStep],
    segments: list[AchievementRouteSegment],
    ready_ids: list[str],
    blocked_ids: list[str],
    time_gated_ids: list[str],
    minutes: int,
) -> list[AchievementRouteAction]:
    step_by_id = {step.step_id: step for step in steps}
    actions: list[AchievementRouteAction] = []
    for segment in segments:
        segment_ready = [step_id for step_id in segment.ready_step_ids if step_id in ready_ids]
        if segment_ready:
            actions.append(
                AchievementRouteAction(
                    action_id=f"action:run:{segment.segment_id}",
                    action_type="run_segment",
                    title=f"Run {segment.map_name} segment",
                    step_ids=segment_ready,
                    reason=f"Fits inside the {minutes}-minute planning window with map-local objectives grouped together.",
                )
            )
    for step_id in time_gated_ids:
        if step_id in ready_ids:
            step = step_by_id[step_id]
            actions.append(
                AchievementRouteAction(
                    action_id=f"action:gate:{step_id}",
                    action_type="do_time_gated_step",
                    title=f"Schedule {step.title}",
                    step_ids=[step_id],
                    reason=f"Marked as {step.time_gate}; verify reset state before relying on it.",
                )
            )
    for step_id in blocked_ids:
        step = step_by_id[step_id]
        missing = ", ".join(step.prerequisite_ids) or "group-content opt-in"
        actions.append(
            AchievementRouteAction(
                action_id=f"action:blocker:{step_id}",
                action_type="unlock_prerequisite" if step.prerequisite_ids else "postpone_blocked_step",
                title=f"Resolve blocker for {step.title}",
                step_ids=[step_id],
                reason=f"Missing prerequisite or planning permission: {missing}.",
            )
        )
    return actions


def _step_titles(step_by_id: dict[str, AchievementRouteStep], step_ids: list[str]) -> str:
    return ", ".join(step_by_id[step_id].title for step_id in step_ids if step_id in step_by_id)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace(":", "")


def _official_progress_status(
    progress: OfficialAccountAchievementProgress | None,
) -> tuple[RouteAccountProgressStatus, str | None]:
    if progress is None:
        return "unknown", "No account achievement progress payload supplied."
    if progress.done is True:
        return "complete", "Official account achievement payload marks this achievement complete."
    if progress.max and progress.current is not None:
        if progress.current >= progress.max:
            return "complete", f"Official account progress is {progress.current}/{progress.max}."
        if progress.current > 0:
            return "in_progress", f"Official account progress is {progress.current}/{progress.max}."
        return "not_started", f"Official account progress is {progress.current}/{progress.max}."
    if progress.current:
        return "in_progress", f"Official account progress current value is {progress.current}."
    return "not_started", "Official account progress has no completed value."


def _infer_official_route_location(detail: OfficialAchievementDetail) -> tuple[str, str, str]:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''} {detail.locked_text or ''}".lower()
    known_locations = [
        ("bloodstone fen", "Bloodstone Fen", "Maguuma Wastes"),
        ("ember bay", "Ember Bay", "Ring of Fire"),
        ("bitterfrost", "Bitterfrost Frontier", "Shiverpeak Mountains"),
        ("dragonfall", "Dragonfall", "Crystal Desert"),
        ("fractals", "Fractals of the Mists", "Mistlock Observatory"),
        ("fractal", "Fractals of the Mists", "Mistlock Observatory"),
    ]
    for marker, map_name, region in known_locations:
        if marker in text:
            return (
                map_name,
                region,
                f"Map inferred from official achievement text keyword: {map_name}.",
            )
    return (
        "Unmapped Achievement Review",
        "Unknown",
        "Official achievement payload did not include an unambiguous map; review required.",
    )


def _infer_official_time_gate(detail: OfficialAchievementDetail) -> RouteTimeGate:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''}".lower()
    flags = {flag.lower() for flag in detail.flags}
    if "weekly" in text or "weekly" in flags:
        return "weekly"
    if "daily" in text or "daily" in flags:
        return "daily"
    return "none"


def _infer_official_group_required(detail: OfficialAchievementDetail) -> bool:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''}".lower()
    return any(marker in text for marker in ("fractal", "raid", "strike", "meta-event", "meta event", "squad"))


def _estimate_official_minutes(detail: OfficialAchievementDetail, group_required: bool) -> int:
    if group_required:
        return 25
    if detail.bits:
        return min(max(len(detail.bits) * 5, 10), 45)
    return 15


def _official_objective(detail: OfficialAchievementDetail) -> str:
    for value in (detail.requirement, detail.description, detail.locked_text):
        if value and value.strip():
            return " ".join(value.strip().split())
    return "Review the official achievement detail and convert it into a player-verified route step."
