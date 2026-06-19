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
