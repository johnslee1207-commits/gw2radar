from pydantic import BaseModel, Field

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
