from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.commercial.account_value import AccountValueSnapshot, build_account_value_evidence_bridge
from gw2radar.commercial.legendary_planner import recompute_legendary_plan
from gw2radar.commercial.market_radar import build_market_radar_report
from gw2radar.db.models import PlayerReadinessSnapshotModel
from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap


class FreshnessAnnotation(BaseModel):
    annotation_id: str
    subject: str
    status: str
    source_confidence: str
    player_message: str
    next_refresh_action: str


class PlayerActionRecommendation(BaseModel):
    action_id: str
    title: str
    reason: str
    timeframe: str
    source: str
    freshness_annotation_id: str
    safety_boundary: str = "informational_manual_actions_only"


class PlayerDashboardPlan(BaseModel):
    schema_version: str = "gw2radar.player_dashboard.v1"
    today_best_actions: list[PlayerActionRecommendation]
    this_week_actions: list[PlayerActionRecommendation]
    do_not_sell_alerts: list[str]
    data_freshness: list[FreshnessAnnotation]
    assumptions: list[str] = Field(default_factory=list)


class PlayerReadinessCheck(BaseModel):
    check_id: str
    label: str
    status: str
    evidence: str
    next_action: str


class PlayerReadinessSummary(BaseModel):
    schema_version: str = "gw2radar.player_readiness_summary.v1"
    readiness_label: str
    readiness_score: float
    checks: list[PlayerReadinessCheck]
    next_actions: list[str]
    safety_boundaries: list[str] = Field(default_factory=list)


class PlayerReadinessSnapshot(BaseModel):
    schema_version: str = "gw2radar.player_readiness_snapshot.v1"
    snapshot_id: str
    user_id: str
    source: str
    created_at: datetime
    readiness_label: str
    readiness_score: float
    checks: list[PlayerReadinessCheck]
    next_actions: list[str]
    safety_boundaries: list[str] = Field(default_factory=list)


class PlayerReadinessHistoryComparison(BaseModel):
    schema_version: str = "gw2radar.player_readiness_history_comparison.v1"
    status: str
    baseline_snapshot_id: str | None = None
    latest_snapshot_id: str | None = None
    score_delta: float = 0.0
    changed_checks: list[str] = Field(default_factory=list)
    improved_checks: list[str] = Field(default_factory=list)
    regressed_checks: list[str] = Field(default_factory=list)
    summary: str


class PlayerReadinessHistory(BaseModel):
    schema_version: str = "gw2radar.player_readiness_history.v1"
    snapshots: list[PlayerReadinessSnapshot]
    comparison: PlayerReadinessHistoryComparison
    safety_boundaries: list[str] = Field(default_factory=list)


def build_data_freshness_annotations(graph: GraphData) -> list[FreshnessAnnotation]:
    has_evidence = bool(graph.evidence)
    has_private_state = bool(graph.player_state)
    return [
        FreshnessAnnotation(
            annotation_id="freshness:account_snapshot",
            subject="Account Snapshot",
            status="fresh" if has_private_state else "needs_sync",
            source_confidence="private_api_summary" if has_private_state else "missing_private_state",
            player_message=(
                "Private account facts are available for account-aware recommendations."
                if has_private_state
                else "Run account sync before trusting account-specific recommendations."
            ),
            next_refresh_action="Run account sync before costly decisions.",
        ),
        FreshnessAnnotation(
            annotation_id="freshness:market_prices",
            subject="Market Prices",
            status="manual_snapshot",
            source_confidence="manual_or_public_snapshot",
            player_message="Market data is observation-only and must be refreshed manually before buying or selling.",
            next_refresh_action="Record or refresh price snapshots for active goal materials.",
        ),
        FreshnessAnnotation(
            annotation_id="freshness:build_sources",
            subject="Build Sources",
            status="needs_patch_review",
            source_confidence="manual_build_import",
            player_message="Build recommendations depend on imported source freshness and patch review.",
            next_refresh_action="Check build patch freshness before replacing gear.",
        ),
        FreshnessAnnotation(
            annotation_id="freshness:knowledge_rules",
            subject="Knowledge Rules",
            status="reviewed_only" if has_evidence else "no_evidence",
            source_confidence="reviewed_kb_and_patch_rules" if has_evidence else "no_loaded_evidence",
            player_message="High-priority advice should be backed by reviewed evidence and enabled rules.",
            next_refresh_action="Review KB evidence when recommendations look stale or surprising.",
        ),
    ]


def build_player_dashboard_plan(graph: GraphData, goal_id: str = "gw2:goal:aurora") -> PlayerDashboardPlan:
    freshness = build_data_freshness_annotations(graph)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    gap = calculate_goal_gap(graph, goal_id) if goal_id in graph.entities else None

    today: list[PlayerActionRecommendation] = []
    for index, action in enumerate(sorted(actions, key=lambda item: item.priority_score, reverse=True)[:3], start=1):
        today.append(
            PlayerActionRecommendation(
                action_id=f"today:{index}",
                title=action.title,
                reason=action.explanation,
                timeframe="today",
                source="goal_action_graph",
                freshness_annotation_id="freshness:account_snapshot",
            )
        )

    if gap and gap.missing_requirements:
        first_missing = gap.missing_requirements[0]
        today.append(
            PlayerActionRecommendation(
                action_id="today:do_not_sell",
                title=f"Reserve {first_missing.name} before selling materials",
                reason=f"{first_missing.name} is still needed by {gap.goal_name}.",
                timeframe="today",
                source="goal_gap",
                freshness_annotation_id="freshness:market_prices",
            )
        )

    week_titles = [
        "Recheck account sync and freshness before expensive spending.",
        "Complete low-risk collection or daily steps for the active goal.",
        "Run Build Fit before entering group content or replacing gear.",
        "Review do-not-sell alerts before market cleanup.",
        "Generate a full report after previewing the evidence boundaries.",
    ]
    week = [
        PlayerActionRecommendation(
            action_id=f"week:{index}",
            title=title,
            reason="This keeps the plan manual, evidence-aware, and reversible.",
            timeframe="this_week",
            source="player_dashboard_policy",
            freshness_annotation_id="freshness:knowledge_rules",
        )
        for index, title in enumerate(week_titles, start=1)
    ]
    return PlayerDashboardPlan(
        today_best_actions=today[:3],
        this_week_actions=week,
        do_not_sell_alerts=_do_not_sell_alerts(graph, goal_id),
        data_freshness=freshness,
        assumptions=[] if graph.player_state else ["No synced private account snapshot is available yet."],
    )


def build_player_readiness_summary(
    graph: GraphData,
    session: Session,
    value_snapshot: AccountValueSnapshot,
    *,
    goal_id: str = "gw2:goal:aurora",
) -> PlayerReadinessSummary:
    bridge = build_account_value_evidence_bridge(value_snapshot)
    checks = [
        PlayerReadinessCheck(
            check_id="account_sync",
            label="Account sync",
            status="ready" if graph.player_state else "needs_sync",
            evidence=f"{len(graph.player_state)} private player-state summaries available.",
            next_action="Run Sync now from Connect before trusting account-aware plans.",
        ),
        PlayerReadinessCheck(
            check_id="account_value",
            label="Account value diagnostics",
            status="ready" if value_snapshot.diagnostics.source_insights else "needs_data",
            evidence=f"Value coverage {bridge.value_coverage_percent}% and price coverage {bridge.price_coverage_percent}%.",
            next_action="Refresh official prices or add manual snapshots for unpriced holdings.",
        ),
        _legendary_readiness_check(graph, session, goal_id),
        _market_readiness_check(graph, session, goal_id),
        PlayerReadinessCheck(
            check_id="build_fit_bridge",
            label="Build Fit evidence bridge",
            status="ready" if bridge.schema_version == "gw2radar.account_value_evidence_bridge.v1" else "blocked",
            evidence=f"{len(bridge.source_summary)} value sources and {len(bridge.remediation_summary)} remediation hints are bridgeable into Build Fit.",
            next_action="Import a build and run Fit score or Transition plan to attach this bridge.",
        ),
    ]
    ready_count = sum(1 for check in checks if check.status == "ready")
    score = round(ready_count / len(checks) * 100, 2) if checks else 0.0
    blockers = [check for check in checks if check.status == "blocked"]
    needs_review = [check for check in checks if check.status not in {"ready", "blocked"}]
    label = "ready" if not blockers and not needs_review else "blocked" if blockers else "needs_review"
    return PlayerReadinessSummary(
        readiness_label=label,
        readiness_score=score,
        checks=checks,
        next_actions=[check.next_action for check in checks if check.status != "ready"][:5]
        or ["All readiness checks are ready at MVP depth; proceed with manual planning review."],
        safety_boundaries=[
            "This readiness card is planning guidance only.",
            "GW2Radar never places trades, changes gear, crafts items, or guarantees outcomes.",
            "Raw API keys and private source payloads are excluded from readiness output.",
        ],
    )


def render_freshness_markdown(graph: GraphData) -> str:
    lines = ["## Data Freshness & Source Confidence"]
    for annotation in build_data_freshness_annotations(graph):
        lines.extend(
            [
                f"- {annotation.subject}: {annotation.status}",
                f"  - Confidence: {annotation.source_confidence}",
                f"  - Player note: {annotation.player_message}",
                f"  - Refresh: {annotation.next_refresh_action}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_player_readiness_markdown(readiness: PlayerReadinessSummary) -> str:
    lines = [
        "# Player Readiness Summary",
        "",
        f"- Schema: {readiness.schema_version}",
        f"- Readiness label: {readiness.readiness_label}",
        f"- Readiness score: {readiness.readiness_score}/100",
        f"- Checks: {len(readiness.checks)}",
        "",
        "## Checks",
        "",
    ]
    for check in readiness.checks:
        lines.extend(
            [
                f"### {check.label}",
                "",
                f"- Check id: `{check.check_id}`",
                f"- Status: {check.status}",
                f"- Evidence: {check.evidence}",
                f"- Next action: {check.next_action}",
                "",
            ]
        )
    lines.extend(["## Next Actions", ""])
    lines.extend(f"- {action}" for action in readiness.next_actions)
    lines.extend(["", "## Safety Boundaries", ""])
    lines.extend(f"- {boundary}" for boundary in readiness.safety_boundaries)
    return "\n".join(lines) + "\n"


def render_player_readiness_csv(readiness: PlayerReadinessSummary) -> str:
    rows = ["check_id,label,status,evidence,next_action"]
    for check in readiness.checks:
        rows.append(
            ",".join(
                [
                    _csv(check.check_id),
                    _csv(check.label),
                    _csv(check.status),
                    _csv(check.evidence),
                    _csv(check.next_action),
                ]
            )
        )
    rows.extend(
        [
            "",
            "summary_key,summary_value",
            f"schema_version,{_csv(readiness.schema_version)}",
            f"readiness_label,{_csv(readiness.readiness_label)}",
            f"readiness_score,{_csv(str(readiness.readiness_score))}",
            f"next_actions,{_csv('; '.join(readiness.next_actions))}",
            f"safety_boundaries,{_csv('; '.join(readiness.safety_boundaries))}",
        ]
    )
    return "\n".join(rows) + "\n"


def record_player_readiness_snapshot(
    session: Session,
    readiness: PlayerReadinessSummary,
    *,
    user_id: str = "local-user",
    source: str = "player_dashboard",
) -> PlayerReadinessSnapshot:
    snapshot_id = f"readiness_{uuid4().hex}"
    row = PlayerReadinessSnapshotModel(
        snapshot_id=snapshot_id,
        user_id=user_id,
        source=source,
        readiness_label=readiness.readiness_label,
        readiness_score=readiness.readiness_score,
        checks_json=[check.model_dump(mode="json") for check in readiness.checks],
        next_actions_json=list(readiness.next_actions),
        safety_boundaries_json=list(readiness.safety_boundaries),
        properties_json={"summary_schema_version": readiness.schema_version},
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return _snapshot_from_row(row)


def list_player_readiness_history(
    session: Session,
    *,
    user_id: str = "local-user",
    limit: int = 10,
) -> PlayerReadinessHistory:
    safe_limit = max(1, min(limit, 50))
    rows = session.scalars(
        select(PlayerReadinessSnapshotModel)
        .where(PlayerReadinessSnapshotModel.user_id == user_id)
        .order_by(PlayerReadinessSnapshotModel.created_at.desc())
        .limit(safe_limit)
    ).all()
    snapshots = [_snapshot_from_row(row) for row in rows]
    return PlayerReadinessHistory(
        snapshots=snapshots,
        comparison=_compare_readiness_snapshots(snapshots),
        safety_boundaries=[
            "History snapshots contain summary readiness metadata only.",
            "Raw API keys and private account source payloads are never stored in readiness history.",
            "Score changes are planning signals, not guarantees of build, market, or crafting outcomes.",
        ],
    )


def render_player_readiness_history_markdown(history: PlayerReadinessHistory) -> str:
    lines = [
        "# Player Readiness History",
        "",
        f"- Schema: {history.schema_version}",
        f"- Snapshots: {len(history.snapshots)}",
        f"- Comparison: {history.comparison.summary}",
        f"- Score delta: {history.comparison.score_delta}",
        "",
        "## Snapshots",
        "",
    ]
    for snapshot in history.snapshots:
        lines.extend(
            [
                f"### {snapshot.created_at.isoformat()}",
                "",
                f"- Snapshot id: `{snapshot.snapshot_id}`",
                f"- Source: {snapshot.source}",
                f"- Readiness: {snapshot.readiness_label} {snapshot.readiness_score}/100",
                f"- Checks: {len(snapshot.checks)}",
                "",
            ]
        )
    lines.extend(["## Changed Checks", ""])
    lines.extend(f"- {item}" for item in history.comparison.changed_checks or ["No check status changes available."])
    lines.extend(["", "## Safety Boundaries", ""])
    lines.extend(f"- {boundary}" for boundary in history.safety_boundaries)
    return "\n".join(lines) + "\n"


def render_player_readiness_history_csv(history: PlayerReadinessHistory) -> str:
    rows = ["snapshot_id,created_at,source,readiness_label,readiness_score,check_id,check_status"]
    for snapshot in history.snapshots:
        for check in snapshot.checks:
            rows.append(
                ",".join(
                    [
                        _csv(snapshot.snapshot_id),
                        _csv(snapshot.created_at.isoformat()),
                        _csv(snapshot.source),
                        _csv(snapshot.readiness_label),
                        _csv(str(snapshot.readiness_score)),
                        _csv(check.check_id),
                        _csv(check.status),
                    ]
                )
            )
    rows.extend(
        [
            "",
            "comparison_key,comparison_value",
            f"status,{_csv(history.comparison.status)}",
            f"baseline_snapshot_id,{_csv(history.comparison.baseline_snapshot_id or '')}",
            f"latest_snapshot_id,{_csv(history.comparison.latest_snapshot_id or '')}",
            f"score_delta,{_csv(str(history.comparison.score_delta))}",
            f"changed_checks,{_csv('; '.join(history.comparison.changed_checks))}",
            f"summary,{_csv(history.comparison.summary)}",
        ]
    )
    return "\n".join(rows) + "\n"


def _do_not_sell_alerts(graph: GraphData, goal_id: str) -> list[str]:
    if goal_id not in graph.entities:
        return ["Load an active goal before generating do-not-sell alerts."]
    gap = calculate_goal_gap(graph, goal_id)
    alerts = [
        f"Do not sell {item.name} while {gap.goal_name} is active."
        for item in gap.completed_requirements + gap.missing_requirements
        if graph.quantity_owned(item.entity_id) > 0
    ]
    return alerts[:5] or ["No owned active-goal materials detected; verify manually before selling."]


def _legendary_readiness_check(graph: GraphData, session: Session, goal_id: str) -> PlayerReadinessCheck:
    if goal_id not in graph.entities:
        return PlayerReadinessCheck(
            check_id="legendary_planner",
            label="Legendary Planner",
            status="blocked",
            evidence=f"Goal {goal_id} is not loaded.",
            next_action="Load the demo graph or select an available legendary goal.",
        )
    planner = recompute_legendary_plan(session, graph)
    bridge_ready = planner.account_value_evidence is not None
    return PlayerReadinessCheck(
        check_id="legendary_planner",
        label="Legendary Planner",
        status="ready" if planner.portfolio.goals and bridge_ready else "needs_goal",
        evidence=f"{len(planner.portfolio.goals)} goals, {len(planner.do_not_sell)} do-not-sell notes, bridge {str(bridge_ready).lower()}.",
        next_action="Add or prioritize a legendary goal, then run Cheap/fast path.",
    )


def _market_readiness_check(graph: GraphData, session: Session, goal_id: str) -> PlayerReadinessCheck:
    if goal_id not in graph.entities:
        return PlayerReadinessCheck(
            check_id="market_radar",
            label="Market Radar",
            status="blocked",
            evidence=f"Goal {goal_id} is not loaded.",
            next_action="Load a goal before market signal review.",
        )
    report = build_market_radar_report(session, graph, goal_id)
    return PlayerReadinessCheck(
        check_id="market_radar",
        label="Market Radar",
        status="ready" if report.account_value_evidence is not None else "needs_price",
        evidence=f"{len(report.signals)} market signals and {len(report.trends)} watched price trends available.",
        next_action="Record or refresh price snapshots, then run Market signals.",
    )


def _csv(value: str) -> str:
    text = str(value)
    if any(char in text for char in [",", '"', "\n"]):
        return f'"{text.replace(chr(34), chr(34) + chr(34))}"'
    return text


def _snapshot_from_row(row: PlayerReadinessSnapshotModel) -> PlayerReadinessSnapshot:
    return PlayerReadinessSnapshot(
        snapshot_id=row.snapshot_id,
        user_id=row.user_id,
        source=row.source,
        created_at=row.created_at,
        readiness_label=row.readiness_label,
        readiness_score=row.readiness_score,
        checks=[PlayerReadinessCheck(**item) for item in row.checks_json],
        next_actions=list(row.next_actions_json),
        safety_boundaries=list(row.safety_boundaries_json),
    )


def _compare_readiness_snapshots(snapshots: list[PlayerReadinessSnapshot]) -> PlayerReadinessHistoryComparison:
    if len(snapshots) < 2:
        return PlayerReadinessHistoryComparison(
            status="insufficient_history",
            latest_snapshot_id=snapshots[0].snapshot_id if snapshots else None,
            summary="Save at least two readiness snapshots before comparing changes.",
        )
    latest = snapshots[0]
    baseline = snapshots[1]
    latest_checks = {check.check_id: check.status for check in latest.checks}
    baseline_checks = {check.check_id: check.status for check in baseline.checks}
    changed = [
        check_id
        for check_id in sorted(set(latest_checks) | set(baseline_checks))
        if latest_checks.get(check_id) != baseline_checks.get(check_id)
    ]
    improved = [check_id for check_id in changed if latest_checks.get(check_id) == "ready"]
    regressed = [check_id for check_id in changed if baseline_checks.get(check_id) == "ready"]
    score_delta = round(latest.readiness_score - baseline.readiness_score, 2)
    direction = "unchanged" if score_delta == 0 and not changed else "improved" if score_delta > 0 else "regressed" if score_delta < 0 else "changed"
    return PlayerReadinessHistoryComparison(
        status=direction,
        baseline_snapshot_id=baseline.snapshot_id,
        latest_snapshot_id=latest.snapshot_id,
        score_delta=score_delta,
        changed_checks=changed,
        improved_checks=improved,
        regressed_checks=regressed,
        summary=f"Latest readiness {direction}: score delta {score_delta}, changed checks {len(changed)}.",
    )
