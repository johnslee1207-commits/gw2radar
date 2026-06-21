import hashlib
import json
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from gw2radar.commercial.account_value import (
    AccountValueHistory,
    AccountValueSnapshot,
    build_account_value_evidence_bridge,
)
from gw2radar.commercial.legendary_planner import recompute_legendary_plan
from gw2radar.commercial.market_radar import build_market_radar_report
from gw2radar.db.models import PlayerReadinessSnapshotModel
from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.support.account_debug_bundle_review import SupportReviewReport, review_account_debug_bundle


PLAYER_SESSION_PACKET_ARTIFACT_ROOT = Path("src/gw2radar/reports/artifacts/player_session_packets")
PLAYER_SESSION_PACKET_ARTIFACT_FILES = {"packet.json", "packet.md", "packet.csv", "manifest.json"}
PLAYER_SUPPORT_HANDOFF_ARTIFACT_ROOT = Path("src/gw2radar/reports/artifacts/player_support_handoffs")
PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES = {"handoff.json", "handoff.md", "handoff.csv", "manifest.json"}
PLAYER_SUPPORT_HANDOFF_AUDIT_ROOT = PLAYER_SUPPORT_HANDOFF_ARTIFACT_ROOT / "audit"


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


class PlayerHistoryCorrelation(BaseModel):
    schema_version: str = "gw2radar.player_history_correlation.v1"
    status: str
    readiness_snapshot_count: int = 0
    account_value_snapshot_count: int = 0
    readiness_score_delta: float = 0.0
    total_value_buy_delta_copper: int = 0
    price_coverage_delta: float = 0.0
    value_coverage_delta: float = 0.0
    correlation_notes: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)


class PlayerSessionPacket(BaseModel):
    schema_version: str = "gw2radar.player_session_packet.v1"
    generated_at: datetime
    readiness_summary: dict
    account_value_summary: dict
    history_correlation: PlayerHistoryCorrelation
    debug_safe_evidence: list[str] = Field(default_factory=list)
    support_review_prompts: list[str] = Field(default_factory=list)
    export_manifest: dict = Field(default_factory=dict)
    safety_boundaries: list[str] = Field(default_factory=list)


class PlayerSessionPacketArtifactFile(BaseModel):
    file_name: str
    relative_path: str
    media_type: str
    size_bytes: int
    checksum_sha256: str


class PlayerSessionPacketArtifactBundle(BaseModel):
    schema_version: str = "gw2radar.player_session_packet_artifact_bundle.v1"
    artifact_id: str
    artifact_root: str
    generated_at: datetime
    file_count: int
    files: list[PlayerSessionPacketArtifactFile]
    manifest_path: str
    checksum_sha256: str
    boundary: str = "Player session packet artifacts are local support handoff files; they exclude raw keys and raw private source payloads."


class PlayerSupportHandoffBundle(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_bundle.v1"
    handoff_id: str
    generated_at: datetime
    support_status: str
    session_artifact_bundle: PlayerSessionPacketArtifactBundle
    debug_bundle_review: dict
    recommended_next_actions: list[str] = Field(default_factory=list)
    evidence_chain: list[str] = Field(default_factory=list)
    manifest: dict = Field(default_factory=dict)
    boundary: str = (
        "Support handoff bundles contain artifact metadata, checksums, and review summaries only; "
        "raw keys, raw debug bundles, private account payloads, and full artifact contents are excluded."
    )


class PlayerSupportHandoffArtifactBundle(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_artifact_bundle.v1"
    artifact_id: str
    artifact_root: str
    generated_at: datetime
    file_count: int
    files: list[PlayerSessionPacketArtifactFile]
    manifest_path: str
    checksum_sha256: str
    support_status: str
    source_handoff_id: str
    source_session_artifact_id: str
    boundary: str = (
        "Support handoff artifact files are local support archives; they exclude raw keys, raw debug bundles, "
        "private account payloads, and executable content."
    )


class PlayerSupportHandoffZipManifest(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_zip_manifest.v1"
    bundle_id: str
    source_artifact_id: str
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    file_count: int
    included_files: list[PlayerSessionPacketArtifactFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str = (
        "Support handoff zip bundles are read-only local transfer packages; they do not execute files, "
        "publish content, store raw keys, or include raw private payloads."
    )


class PlayerSupportHandoffZipVerification(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_zip_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support handoff zip verification reads zip bytes only; it does not execute files, write uploaded "
        "content to disk, publish content, or store secrets."
    )


class PlayerSupportHandoffZipVerificationAuditRequest(BaseModel):
    reviewer: str = "support"
    notes: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class PlayerSupportHandoffZipVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_zip_verification_audit.v1"
    audit_id: str
    recorded_at: datetime
    reviewer: str
    ready: bool
    checksum_sha256: str
    size_bytes: int
    file_count: int
    blocker_count: int
    warning_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    source: str = "player_support_handoff_zip_verification"
    boundary: str = (
        "Support handoff verification audit is metadata-only; it records validation results and does not "
        "store zip bytes, raw API keys, raw debug bundles, or private account payloads."
    )


class PlayerSupportHandoffZipVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_zip_verification_audit_list.v1"
    records: list[PlayerSupportHandoffZipVerificationAuditRecord]
    boundary: str = "Support handoff verification audit exports are metadata-only and exclude zip content and secrets."


class PlayerSupportHandoffReadinessChecklist(BaseModel):
    schema_version: str = "gw2radar.player_support_handoff_readiness_checklist.v1"
    generated_at: datetime
    ready: bool
    maturity_label: str
    latest_artifact_id: str | None = None
    artifact_file_count: int = 0
    zip_checksum_sha256: str | None = None
    zip_file_count: int = 0
    zip_verification_ready: bool = False
    verification_audit_count: int = 0
    latest_verification_audit_id: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = (
        "Support handoff readiness is metadata-only; it summarizes artifact, zip, verification, and audit gates "
        "without storing raw keys, raw debug bundles, private account payloads, or zip bytes."
    )


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


def build_player_history_correlation(
    readiness_history: PlayerReadinessHistory,
    account_value_history: AccountValueHistory,
) -> PlayerHistoryCorrelation:
    readiness_comparison = readiness_history.comparison
    value_comparison = account_value_history.comparison
    notes: list[str] = []
    actions: list[str] = []
    if len(readiness_history.snapshots) < 2 or len(account_value_history.snapshots) < 2:
        return PlayerHistoryCorrelation(
            status="insufficient_history",
            readiness_snapshot_count=len(readiness_history.snapshots),
            account_value_snapshot_count=len(account_value_history.snapshots),
            correlation_notes=["Save at least two readiness snapshots and two account value snapshots before correlation."],
            next_actions=["Run Check readiness, save readiness snapshot, refresh account value, then save value snapshot twice across meaningful changes."],
            safety_boundaries=_history_correlation_boundaries(),
        )
    readiness_delta = readiness_comparison.score_delta
    value_delta = value_comparison.total_value_buy_delta_copper
    price_delta = value_comparison.price_coverage_delta
    value_coverage_delta = value_comparison.value_coverage_delta
    if readiness_delta > 0 and price_delta >= 0:
        status = "improved"
        notes.append("Readiness improved while price coverage stayed flat or improved.")
    elif readiness_delta < 0 and price_delta < 0:
        status = "needs_review"
        notes.append("Readiness regressed alongside lower price coverage; stale or missing prices may be contributing.")
        actions.append("Refresh official prices and rerun readiness before making planning decisions.")
    elif readiness_delta == 0 and value_delta == 0 and price_delta == 0 and value_coverage_delta == 0:
        status = "unchanged"
        notes.append("Readiness and account value coverage are unchanged between the latest snapshots.")
    else:
        status = "changed"
        notes.append("Readiness and account value moved differently; inspect changed checks and value warnings together.")
    if value_comparison.warning_codes_added:
        notes.append(f"New value warnings appeared: {', '.join(value_comparison.warning_codes_added)}.")
        actions.append("Review value warnings before manual sell, craft, or gear decisions.")
    if readiness_comparison.changed_checks:
        notes.append(f"Readiness checks changed: {', '.join(readiness_comparison.changed_checks)}.")
    if price_delta > 0:
        actions.append("Price coverage improved; rerun Market Radar and Legendary cheap/fast path for fresher planning.")
    if not actions:
        actions.append("Keep using paired snapshots after sync or price refresh to make changes explainable.")
    return PlayerHistoryCorrelation(
        status=status,
        readiness_snapshot_count=len(readiness_history.snapshots),
        account_value_snapshot_count=len(account_value_history.snapshots),
        readiness_score_delta=readiness_delta,
        total_value_buy_delta_copper=value_delta,
        price_coverage_delta=price_delta,
        value_coverage_delta=value_coverage_delta,
        correlation_notes=notes,
        next_actions=actions,
        evidence_refs=[
            readiness_comparison.latest_snapshot_id or "missing_readiness_latest",
            readiness_comparison.baseline_snapshot_id or "missing_readiness_baseline",
            value_comparison.latest_snapshot_id or "missing_value_latest",
            value_comparison.baseline_snapshot_id or "missing_value_baseline",
        ],
        safety_boundaries=_history_correlation_boundaries(),
    )


def render_player_history_correlation_markdown(correlation: PlayerHistoryCorrelation) -> str:
    lines = [
        "# Player History Correlation",
        "",
        f"- Schema: {correlation.schema_version}",
        f"- Status: {correlation.status}",
        f"- Readiness snapshots: {correlation.readiness_snapshot_count}",
        f"- Account value snapshots: {correlation.account_value_snapshot_count}",
        f"- Readiness score delta: {correlation.readiness_score_delta}",
        f"- Total value delta: {correlation.total_value_buy_delta_copper} copper",
        f"- Price coverage delta: {correlation.price_coverage_delta}",
        f"- Value coverage delta: {correlation.value_coverage_delta}",
        "",
        "## Correlation Notes",
        "",
        *[f"- {note}" for note in correlation.correlation_notes],
        "",
        "## Next Actions",
        "",
        *[f"- {action}" for action in correlation.next_actions],
        "",
        "## Safety Boundaries",
        "",
        *[f"- {boundary}" for boundary in correlation.safety_boundaries],
    ]
    return "\n".join(lines) + "\n"


def render_player_history_correlation_csv(correlation: PlayerHistoryCorrelation) -> str:
    rows = [
        "metric,value",
        f"schema_version,{_csv(correlation.schema_version)}",
        f"status,{_csv(correlation.status)}",
        f"readiness_snapshot_count,{_csv(str(correlation.readiness_snapshot_count))}",
        f"account_value_snapshot_count,{_csv(str(correlation.account_value_snapshot_count))}",
        f"readiness_score_delta,{_csv(str(correlation.readiness_score_delta))}",
        f"total_value_buy_delta_copper,{_csv(str(correlation.total_value_buy_delta_copper))}",
        f"price_coverage_delta,{_csv(str(correlation.price_coverage_delta))}",
        f"value_coverage_delta,{_csv(str(correlation.value_coverage_delta))}",
        f"correlation_notes,{_csv('; '.join(correlation.correlation_notes))}",
        f"next_actions,{_csv('; '.join(correlation.next_actions))}",
        f"evidence_refs,{_csv('; '.join(correlation.evidence_refs))}",
    ]
    return "\n".join(rows) + "\n"


def build_player_session_packet(
    graph: GraphData,
    readiness: PlayerReadinessSummary,
    account_value: AccountValueSnapshot,
    readiness_history: PlayerReadinessHistory,
    account_value_history: AccountValueHistory,
    history_correlation: PlayerHistoryCorrelation,
) -> PlayerSessionPacket:
    warning_codes = sorted({warning.warning_code for warning in account_value.warnings})
    readiness_checks = {check.check_id: check.status for check in readiness.checks}
    value_summary = account_value.summary.model_dump(mode="json")
    diagnostics = account_value.diagnostics
    return PlayerSessionPacket(
        generated_at=datetime.now(timezone.utc),
        readiness_summary={
            "schema_version": readiness.schema_version,
            "label": readiness.readiness_label,
            "score": readiness.readiness_score,
            "checks": readiness_checks,
            "next_actions": list(readiness.next_actions),
        },
        account_value_summary={
            "schema_version": account_value.schema_version,
            "account_id_present": bool(account_value.account_id),
            "summary": value_summary,
            "value_coverage_percent": diagnostics.value_coverage_percent,
            "price_coverage_percent": diagnostics.price_coverage_percent,
            "freshness_label": diagnostics.freshness_label,
            "source_insight_count": len(diagnostics.source_insights),
            "remediation_action_count": len(diagnostics.remediation_actions),
            "top_holding_count": len(account_value.top_holdings),
            "warning_codes": warning_codes,
        },
        history_correlation=history_correlation,
        debug_safe_evidence=[
            f"private_player_state_count={len(graph.player_state)}",
            f"readiness_history_snapshots={len(readiness_history.snapshots)}",
            f"account_value_history_snapshots={len(account_value_history.snapshots)}",
            f"value_warning_codes={','.join(warning_codes) if warning_codes else 'none'}",
            f"correlation_status={history_correlation.status}",
        ],
        support_review_prompts=_session_packet_support_prompts(readiness, account_value, history_correlation),
        export_manifest={
            "formats": ["json", "markdown", "csv"],
            "contains_raw_key": False,
            "contains_private_source_payload": False,
            "contains_full_holding_list": False,
            "source_endpoints": [
                "/api/v1/player/readiness",
                "/api/v1/player/account-value",
                "/api/v1/player/history/correlation",
            ],
        },
        safety_boundaries=[
            "Session packet is support-review metadata only.",
            "It excludes raw API keys, raw GW2 API payloads, and full private holding lists.",
            "It does not automate trades, change gear, craft items, or guarantee outcomes.",
        ],
    )


def render_player_session_packet_markdown(packet: PlayerSessionPacket) -> str:
    lines = [
        "# Player Session Packet",
        "",
        f"- Schema: {packet.schema_version}",
        f"- Generated: {packet.generated_at.isoformat()}",
        f"- Readiness: {packet.readiness_summary.get('label')} {packet.readiness_summary.get('score')}/100",
        f"- Account value freshness: {packet.account_value_summary.get('freshness_label')}",
        f"- Price coverage: {packet.account_value_summary.get('price_coverage_percent')}%",
        f"- Correlation status: {packet.history_correlation.status}",
        "",
        "## Debug-Safe Evidence",
        "",
        *[f"- {item}" for item in packet.debug_safe_evidence],
        "",
        "## Support Review Prompts",
        "",
        *[f"- {prompt}" for prompt in packet.support_review_prompts],
        "",
        "## Export Manifest",
        "",
        f"- Contains raw key: {packet.export_manifest.get('contains_raw_key')}",
        f"- Contains private source payload: {packet.export_manifest.get('contains_private_source_payload')}",
        f"- Contains full holding list: {packet.export_manifest.get('contains_full_holding_list')}",
        "",
        "## Safety Boundaries",
        "",
        *[f"- {boundary}" for boundary in packet.safety_boundaries],
    ]
    return "\n".join(lines) + "\n"


def render_player_session_packet_csv(packet: PlayerSessionPacket) -> str:
    rows = [
        "metric,value",
        f"schema_version,{_csv(packet.schema_version)}",
        f"generated_at,{_csv(packet.generated_at.isoformat())}",
        f"readiness_label,{_csv(str(packet.readiness_summary.get('label', '')))}",
        f"readiness_score,{_csv(str(packet.readiness_summary.get('score', '')))}",
        f"account_value_freshness,{_csv(str(packet.account_value_summary.get('freshness_label', '')))}",
        f"value_coverage_percent,{_csv(str(packet.account_value_summary.get('value_coverage_percent', '')))}",
        f"price_coverage_percent,{_csv(str(packet.account_value_summary.get('price_coverage_percent', '')))}",
        f"history_correlation_status,{_csv(packet.history_correlation.status)}",
        f"debug_safe_evidence,{_csv('; '.join(packet.debug_safe_evidence))}",
        f"support_review_prompts,{_csv('; '.join(packet.support_review_prompts))}",
        f"contains_raw_key,{_csv(str(packet.export_manifest.get('contains_raw_key')))}",
        f"contains_private_source_payload,{_csv(str(packet.export_manifest.get('contains_private_source_payload')))}",
    ]
    return "\n".join(rows) + "\n"


def write_player_session_packet_artifacts(
    packet: PlayerSessionPacket,
    *,
    artifact_root: Path | None = None,
) -> PlayerSessionPacketArtifactBundle:
    root = artifact_root or PLAYER_SESSION_PACKET_ARTIFACT_ROOT
    generated_at = datetime.now(timezone.utc)
    artifact_id = f"player-session-packet-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    artifact_dir = root / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    contents = {
        "packet.json": packet.model_dump_json(indent=2),
        "packet.md": render_player_session_packet_markdown(packet),
        "packet.csv": render_player_session_packet_csv(packet),
    }
    files: list[PlayerSessionPacketArtifactFile] = []
    for file_name, text in contents.items():
        file_path = artifact_dir / file_name
        file_path.write_text(text, encoding="utf-8")
        files.append(_artifact_file_entry(root, file_path, file_name, _packet_media_type(file_name), text))
    manifest_payload = {
        "schema_version": "gw2radar.player_session_packet_artifact_manifest.v1",
        "artifact_id": artifact_id,
        "generated_at": generated_at.isoformat(),
        "packet_schema": packet.schema_version,
        "files": [file.model_dump(mode="json") for file in files],
        "contains_raw_key": False,
        "contains_private_source_payload": False,
        "contains_full_holding_list": False,
        "safety_boundaries": list(packet.safety_boundaries),
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_file = _artifact_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
    files.append(manifest_file)
    return PlayerSessionPacketArtifactBundle(
        artifact_id=artifact_id,
        artifact_root=root.as_posix(),
        generated_at=generated_at,
        file_count=len(files),
        files=files,
        manifest_path=manifest_file.relative_path,
        checksum_sha256=_artifact_bundle_checksum(files),
    )


def list_player_session_packet_artifacts(
    *,
    artifact_root: Path | None = None,
    limit: int = 20,
) -> list[PlayerSessionPacketArtifactBundle]:
    root = artifact_root or PLAYER_SESSION_PACKET_ARTIFACT_ROOT
    if not root.exists():
        return []
    bundles: list[PlayerSessionPacketArtifactBundle] = []
    for artifact_dir in sorted([path for path in root.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)[: max(1, min(limit, 100))]:
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        files = [
            PlayerSessionPacketArtifactFile(**file)
            for file in manifest.get("files", [])
            if file.get("file_name") in PLAYER_SESSION_PACKET_ARTIFACT_FILES
        ]
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_file = _artifact_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
        if not any(file.file_name == "manifest.json" for file in files):
            files.append(manifest_file)
        bundles.append(
            PlayerSessionPacketArtifactBundle(
                artifact_id=artifact_dir.name,
                artifact_root=root.as_posix(),
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
                file_count=len(files),
                files=files,
                manifest_path=manifest_file.relative_path,
                checksum_sha256=_artifact_bundle_checksum(files),
            )
        )
    return bundles


def resolve_player_session_packet_artifact_path(
    artifact_id: str,
    file_name: str,
    *,
    artifact_root: Path | None = None,
) -> Path | None:
    if "/" in artifact_id or "\\" in artifact_id or ".." in artifact_id:
        return None
    if file_name not in PLAYER_SESSION_PACKET_ARTIFACT_FILES:
        return None
    root = (artifact_root or PLAYER_SESSION_PACKET_ARTIFACT_ROOT).resolve()
    candidate = (root / artifact_id / file_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_player_support_handoff_bundle(
    *,
    session_artifact_bundle: PlayerSessionPacketArtifactBundle,
    debug_bundle: dict | None = None,
) -> PlayerSupportHandoffBundle:
    generated_at = datetime.now(timezone.utc)
    review = review_account_debug_bundle(debug_bundle) if debug_bundle is not None else _missing_debug_bundle_review()
    review_payload = review.model_dump(mode="json")
    recommended_next_actions = _support_handoff_next_actions(review, session_artifact_bundle)
    evidence_chain = [
        f"session_artifact:{session_artifact_bundle.artifact_id}",
        f"session_manifest:{session_artifact_bundle.manifest_path}",
        f"session_checksum:{session_artifact_bundle.checksum_sha256}",
        f"debug_bundle_review:{review.overall_status}",
    ]
    return PlayerSupportHandoffBundle(
        handoff_id=f"player-support-handoff-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        generated_at=generated_at,
        support_status="ready" if review.overall_status == "ready" else "needs_review",
        session_artifact_bundle=session_artifact_bundle,
        debug_bundle_review=review_payload,
        recommended_next_actions=recommended_next_actions,
        evidence_chain=evidence_chain,
        manifest={
            "schema_version": "gw2radar.player_support_handoff_manifest.v1",
            "contains_raw_key": False,
            "contains_raw_debug_bundle": False,
            "contains_private_source_payload": False,
            "contains_full_artifact_contents": False,
            "artifact_file_count": session_artifact_bundle.file_count,
            "artifact_checksum_sha256": session_artifact_bundle.checksum_sha256,
            "debug_bundle_schema_version": review.bundle_schema_version,
            "debug_bundle_overall_status": review.overall_status,
        },
    )


def render_player_support_handoff_markdown(bundle: PlayerSupportHandoffBundle) -> str:
    review = bundle.debug_bundle_review
    lines = [
        "# Player Support Handoff Bundle",
        "",
        f"- Handoff id: {bundle.handoff_id}",
        f"- Status: {bundle.support_status}",
        f"- Generated: {bundle.generated_at.isoformat()}",
        f"- Session artifact: {bundle.session_artifact_bundle.artifact_id}",
        f"- Session checksum: {bundle.session_artifact_bundle.checksum_sha256}",
        f"- Debug review status: {review.get('overall_status', 'unknown')}",
        "",
        "## Recommended Next Actions",
        "",
    ]
    lines.extend(f"- {action}" for action in bundle.recommended_next_actions)
    lines.extend(["", "## Evidence Chain", ""])
    lines.extend(f"- {item}" for item in bundle.evidence_chain)
    lines.extend(["", "## Artifact Files", ""])
    for file in bundle.session_artifact_bundle.files:
        lines.append(f"- {file.file_name}: {file.relative_path} ({file.checksum_sha256})")
    lines.extend(["", "## Debug Review Findings", ""])
    findings = review.get("findings", [])
    if not findings:
        lines.append("- No blocking debug review finding is present.")
    for finding in findings:
        lines.append(
            f"- [{finding.get('severity', 'info')}] {finding.get('finding_id', 'finding')}: "
            f"{finding.get('recommended_action', '')}"
        )
    lines.extend(["", "## Boundary", "", f"- {bundle.boundary}"])
    return "\n".join(lines) + "\n"


def render_player_support_handoff_csv(bundle: PlayerSupportHandoffBundle) -> str:
    rows = [
        "metric,value",
        f"schema_version,{_csv(bundle.schema_version)}",
        f"handoff_id,{_csv(bundle.handoff_id)}",
        f"support_status,{_csv(bundle.support_status)}",
        f"generated_at,{_csv(bundle.generated_at.isoformat())}",
        f"session_artifact_id,{_csv(bundle.session_artifact_bundle.artifact_id)}",
        f"session_checksum_sha256,{_csv(bundle.session_artifact_bundle.checksum_sha256)}",
        f"artifact_file_count,{_csv(str(bundle.session_artifact_bundle.file_count))}",
        f"debug_bundle_overall_status,{_csv(str(bundle.debug_bundle_review.get('overall_status', 'unknown')))}",
        f"contains_raw_key,{_csv(str(bundle.manifest.get('contains_raw_key')))}",
        f"contains_raw_debug_bundle,{_csv(str(bundle.manifest.get('contains_raw_debug_bundle')))}",
        f"contains_private_source_payload,{_csv(str(bundle.manifest.get('contains_private_source_payload')))}",
        f"recommended_next_actions,{_csv('; '.join(bundle.recommended_next_actions))}",
        f"evidence_chain,{_csv('; '.join(bundle.evidence_chain))}",
    ]
    return "\n".join(rows) + "\n"


def write_player_support_handoff_artifacts(
    handoff: PlayerSupportHandoffBundle,
    *,
    artifact_root: Path | None = None,
) -> PlayerSupportHandoffArtifactBundle:
    root = artifact_root or PLAYER_SUPPORT_HANDOFF_ARTIFACT_ROOT
    generated_at = datetime.now(timezone.utc)
    artifact_id = f"player-support-handoff-{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}"
    artifact_dir = root / artifact_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    contents = {
        "handoff.json": handoff.model_dump_json(indent=2),
        "handoff.md": render_player_support_handoff_markdown(handoff),
        "handoff.csv": render_player_support_handoff_csv(handoff),
    }
    files: list[PlayerSessionPacketArtifactFile] = []
    for file_name, text in contents.items():
        file_path = artifact_dir / file_name
        file_path.write_text(text, encoding="utf-8")
        files.append(_artifact_file_entry(root, file_path, file_name, _packet_media_type(file_name), text))
    manifest_payload = {
        "schema_version": "gw2radar.player_support_handoff_artifact_manifest.v1",
        "artifact_id": artifact_id,
        "generated_at": generated_at.isoformat(),
        "handoff_schema": handoff.schema_version,
        "source_handoff_id": handoff.handoff_id,
        "source_session_artifact_id": handoff.session_artifact_bundle.artifact_id,
        "support_status": handoff.support_status,
        "files": [file.model_dump(mode="json") for file in files],
        "contains_raw_key": False,
        "contains_raw_debug_bundle": False,
        "contains_private_source_payload": False,
        "contains_executable_content": False,
        "allowed_files": sorted(PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES),
        "evidence_chain": list(handoff.evidence_chain),
        "boundary": "Local handoff artifact archive stores review summaries and artifact metadata only.",
    }
    manifest_text = json.dumps(manifest_payload, indent=2, sort_keys=True)
    manifest_path = artifact_dir / "manifest.json"
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_file = _artifact_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
    files.append(manifest_file)
    checksum = _artifact_bundle_checksum(files)
    return PlayerSupportHandoffArtifactBundle(
        artifact_id=artifact_id,
        artifact_root=root.as_posix(),
        generated_at=generated_at,
        file_count=len(files),
        files=files,
        manifest_path=manifest_file.relative_path,
        checksum_sha256=checksum,
        support_status=handoff.support_status,
        source_handoff_id=handoff.handoff_id,
        source_session_artifact_id=handoff.session_artifact_bundle.artifact_id,
    )


def list_player_support_handoff_artifacts(
    *,
    artifact_root: Path | None = None,
    limit: int = 20,
) -> list[PlayerSupportHandoffArtifactBundle]:
    root = artifact_root or PLAYER_SUPPORT_HANDOFF_ARTIFACT_ROOT
    if not root.exists():
        return []
    bundles: list[PlayerSupportHandoffArtifactBundle] = []
    for artifact_dir in sorted([path for path in root.iterdir() if path.is_dir()], key=lambda item: item.name, reverse=True)[: max(1, min(limit, 100))]:
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.exists():
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        files = [
            PlayerSessionPacketArtifactFile(**file)
            for file in manifest.get("files", [])
            if file.get("file_name") in PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES
        ]
        manifest_text = manifest_path.read_text(encoding="utf-8")
        manifest_file = _artifact_file_entry(root, manifest_path, "manifest.json", "application/json", manifest_text)
        if not any(file.file_name == "manifest.json" for file in files):
            files.append(manifest_file)
        bundles.append(
            PlayerSupportHandoffArtifactBundle(
                artifact_id=artifact_dir.name,
                artifact_root=root.as_posix(),
                generated_at=datetime.fromisoformat(manifest["generated_at"]),
                file_count=len(files),
                files=files,
                manifest_path=manifest_file.relative_path,
                checksum_sha256=_artifact_bundle_checksum(files),
                support_status=str(manifest.get("support_status") or "unknown"),
                source_handoff_id=str(manifest.get("source_handoff_id") or "unknown"),
                source_session_artifact_id=str(manifest.get("source_session_artifact_id") or "unknown"),
            )
        )
    return bundles


def resolve_player_support_handoff_artifact_path(
    artifact_id: str,
    file_name: str,
    *,
    artifact_root: Path | None = None,
) -> Path | None:
    if "/" in artifact_id or "\\" in artifact_id or ".." in artifact_id:
        return None
    if file_name not in PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES:
        return None
    root = (artifact_root or PLAYER_SUPPORT_HANDOFF_ARTIFACT_ROOT).resolve()
    candidate = (root / artifact_id / file_name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_player_support_handoff_zip_bundle(
    *,
    artifact_root: Path | None = None,
) -> tuple[PlayerSupportHandoffZipManifest, bytes]:
    bundles = list_player_support_handoff_artifacts(artifact_root=artifact_root, limit=1)
    if not bundles:
        raise ValueError("No player support handoff artifacts are available to bundle.")
    artifact_bundle = bundles[0]
    source_files: list[tuple[str, Path, str]] = []
    for file in artifact_bundle.files:
        path = resolve_player_support_handoff_artifact_path(
            artifact_bundle.artifact_id,
            file.file_name,
            artifact_root=artifact_root,
        )
        if path is not None:
            source_files.append((file.file_name, path, file.media_type))
    included_files: list[PlayerSessionPacketArtifactFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for file_name, path, media_type in sorted(source_files, key=lambda item: item[0]):
            if file_name not in PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES:
                continue
            content = path.read_bytes()
            archive_path = f"player_support_handoff/{file_name}"
            info = ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
            included_files.append(
                PlayerSessionPacketArtifactFile(
                    file_name=file_name,
                    relative_path=archive_path,
                    media_type=media_type,
                    size_bytes=len(content),
                    checksum_sha256=hashlib.sha256(content).hexdigest(),
                )
            )
    bundle_bytes = buffer.getvalue()
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    return (
        PlayerSupportHandoffZipManifest(
            bundle_id=f"player-support-handoff-zip:{checksum[:16]}",
            source_artifact_id=artifact_bundle.artifact_id,
            generated_at=datetime.now(timezone.utc),
            filename=f"{artifact_bundle.artifact_id}_support_handoff.zip",
            file_count=len(included_files),
            included_files=included_files,
            checksum_sha256=checksum,
            size_bytes=len(bundle_bytes),
        ),
        bundle_bytes,
    )


def verify_player_support_handoff_zip_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> PlayerSupportHandoffZipVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    allowed_names = {f"player_support_handoff/{file_name}" for file_name in PLAYER_SUPPORT_HANDOFF_ARTIFACT_FILES}
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("bundle checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    blockers.append(f"bundle contains unsafe path: {name}")
            extra_names = sorted(set(names) - allowed_names)
            missing_names = sorted(allowed_names - set(names))
            if extra_names:
                blockers.append("bundle contains non-whitelisted files: " + ", ".join(extra_names))
            if missing_names:
                blockers.append("bundle is missing required files: " + ", ".join(missing_names))
            for name in names:
                lowered = archive.read(name).lower()
                if b"secret-key" in lowered:
                    blockers.append(f"bundle file contains prohibited secret marker: {name}")
            _verify_support_handoff_zip_payloads(archive, names, blockers)
    except Exception as exc:
        blockers.append(f"bundle zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("bundle is larger than the MVP verification target of 5 MB")
    return PlayerSupportHandoffZipVerification(
        ready=not blockers,
        verified_at=datetime.now(timezone.utc),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def record_player_support_handoff_zip_verification_audit(
    request: PlayerSupportHandoffZipVerificationAuditRequest,
    *,
    bundle_bytes: bytes | None = None,
    audit_root: Path | None = None,
) -> PlayerSupportHandoffZipVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        manifest, bundle_bytes = build_player_support_handoff_zip_bundle()
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_player_support_handoff_zip_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    recorded_at = datetime.now(timezone.utc)
    reviewer = _safe_support_text(request.reviewer or "support", max_length=80)
    record = PlayerSupportHandoffZipVerificationAuditRecord(
        audit_id=f"player-support-handoff-zip-audit-{recorded_at.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex[:8]}",
        recorded_at=recorded_at,
        reviewer=reviewer,
        ready=verification.ready,
        checksum_sha256=verification.checksum_sha256,
        size_bytes=verification.size_bytes,
        file_count=verification.file_count,
        blocker_count=len(verification.blockers),
        warning_count=len(verification.warnings),
        verified_files=verification.verified_files,
        blockers=verification.blockers,
        warnings=verification.warnings,
        notes=[_safe_support_text(note, max_length=240) for note in (request.notes or [])]
        or ["Support handoff zip verification audit recorded."],
    )
    root = audit_root or PLAYER_SUPPORT_HANDOFF_AUDIT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    path = root / "verification_audit.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_player_support_handoff_zip_verification_audits(
    *,
    audit_root: Path | None = None,
    reviewer: str | None = None,
    limit: int = 20,
) -> PlayerSupportHandoffZipVerificationAuditList:
    root = audit_root or PLAYER_SUPPORT_HANDOFF_AUDIT_ROOT
    path = root / "verification_audit.jsonl"
    if not path.exists():
        return PlayerSupportHandoffZipVerificationAuditList(records=[])
    safe_reviewer = _safe_support_text(reviewer, max_length=80) if reviewer else None
    records: list[PlayerSupportHandoffZipVerificationAuditRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = PlayerSupportHandoffZipVerificationAuditRecord.model_validate_json(line)
        except ValueError:
            continue
        if safe_reviewer and record.reviewer != safe_reviewer:
            continue
        records.append(record)
    records.sort(key=lambda item: item.recorded_at, reverse=True)
    return PlayerSupportHandoffZipVerificationAuditList(records=records[: max(1, min(limit, 100))])


def render_player_support_handoff_zip_verification_audit_markdown(
    audit: PlayerSupportHandoffZipVerificationAuditList,
) -> str:
    lines = [
        "# Player Support Handoff Zip Verification Audit",
        "",
        f"- Records: {len(audit.records)}",
        "",
        "## Records",
    ]
    if not audit.records:
        lines.append("- No verification audit records are available.")
    for record in audit.records:
        lines.extend(
            [
                f"- {record.audit_id}",
                f"  - Reviewer: {record.reviewer}",
                f"  - Ready: {record.ready}",
                f"  - Checksum: {record.checksum_sha256}",
                f"  - Files: {record.file_count}",
                f"  - Blockers: {record.blocker_count}",
                f"  - Warnings: {record.warning_count}",
            ]
        )
    lines.extend(["", "## Boundary", "", f"- {audit.boundary}"])
    return "\n".join(lines) + "\n"


def render_player_support_handoff_zip_verification_audit_csv(
    audit: PlayerSupportHandoffZipVerificationAuditList,
) -> str:
    rows = [
        "audit_id,recorded_at,reviewer,ready,checksum_sha256,size_bytes,file_count,blocker_count,warning_count"
    ]
    for record in audit.records:
        rows.append(
            ",".join(
                [
                    _csv(record.audit_id),
                    _csv(record.recorded_at.isoformat()),
                    _csv(record.reviewer),
                    _csv(str(record.ready)),
                    _csv(record.checksum_sha256),
                    _csv(str(record.size_bytes)),
                    _csv(str(record.file_count)),
                    _csv(str(record.blocker_count)),
                    _csv(str(record.warning_count)),
                ]
            )
        )
    return "\n".join(rows) + "\n"


def build_player_support_handoff_readiness_checklist(
    *,
    artifact_root: Path | None = None,
    audit_root: Path | None = None,
) -> PlayerSupportHandoffReadinessChecklist:
    artifacts = list_player_support_handoff_artifacts(artifact_root=artifact_root, limit=1)
    latest_artifact = artifacts[0] if artifacts else None
    missing_gates: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    zip_manifest: PlayerSupportHandoffZipManifest | None = None
    zip_verification: PlayerSupportHandoffZipVerification | None = None
    if latest_artifact is None:
        missing_gates.append("support handoff artifact files")
    else:
        if latest_artifact.file_count < 4:
            missing_gates.append("support handoff required artifact files")
        try:
            zip_manifest, zip_bytes = build_player_support_handoff_zip_bundle(artifact_root=artifact_root)
            zip_verification = verify_player_support_handoff_zip_bundle(
                zip_bytes,
                expected_checksum_sha256=zip_manifest.checksum_sha256,
            )
        except ValueError as exc:
            blockers.append(str(exc))
    if zip_manifest is None or zip_manifest.file_count < 4:
        missing_gates.append("support handoff zip bundle")
    if zip_verification is None or not zip_verification.ready:
        missing_gates.append("support handoff zip verification")
    audit = list_player_support_handoff_zip_verification_audits(audit_root=audit_root, limit=1)
    latest_audit = audit.records[0] if audit.records else None
    if latest_audit is None:
        missing_gates.append("support handoff zip verification audit")
    elif not latest_audit.ready:
        missing_gates.append("latest support handoff zip verification audit ready state")
    if zip_verification:
        blockers.extend(zip_verification.blockers)
        warnings.extend(zip_verification.warnings)
    if latest_audit:
        blockers.extend(latest_audit.blockers)
        warnings.extend(latest_audit.warnings)
    ready = not missing_gates and not blockers
    if blockers:
        maturity_label = "blocked"
    elif missing_gates or warnings:
        maturity_label = "review_needed"
    else:
        maturity_label = "ready"
    next_actions = (
        [
            "Resolve missing support handoff gates before asking the player to transfer the zip.",
            "Re-run zip verification and record a fresh audit after blockers are fixed.",
        ]
        if not ready
        else [
            "Attach the support handoff zip, verification audit export, and readiness checklist to the support case.",
            "Continue troubleshooting without requesting raw API keys or private account payloads.",
        ]
    )
    return PlayerSupportHandoffReadinessChecklist(
        generated_at=datetime.now(timezone.utc),
        ready=ready,
        maturity_label=maturity_label,
        latest_artifact_id=latest_artifact.artifact_id if latest_artifact else None,
        artifact_file_count=latest_artifact.file_count if latest_artifact else 0,
        zip_checksum_sha256=zip_manifest.checksum_sha256 if zip_manifest else None,
        zip_file_count=zip_manifest.file_count if zip_manifest else 0,
        zip_verification_ready=zip_verification.ready if zip_verification else False,
        verification_audit_count=len(audit.records),
        latest_verification_audit_id=latest_audit.audit_id if latest_audit else None,
        checklist_items=[
            "Support handoff artifact files written and indexed.",
            "Support handoff zip bundle generated from whitelist files.",
            "Support handoff zip verified without executing content.",
            "Support handoff zip verification audit recorded as metadata only.",
        ],
        missing_gates=_unique_text(missing_gates),
        blockers=_unique_text(blockers),
        warnings=_unique_text(warnings),
        next_actions=next_actions,
        evidence_refs=[
            "/api/v1/player/support-handoff/artifacts",
            "/api/v1/player/support-handoff/artifacts/bundle",
            "/api/v1/player/support-handoff/artifacts/bundle/verify",
            "/api/v1/player/support-handoff/artifacts/bundle/verification-audit",
        ],
    )


def render_player_support_handoff_readiness_checklist_markdown(
    checklist: PlayerSupportHandoffReadinessChecklist,
) -> str:
    lines = [
        "# Player Support Handoff Readiness Checklist",
        "",
        f"- Ready: {checklist.ready}",
        f"- Maturity: {checklist.maturity_label}",
        f"- Latest artifact: {checklist.latest_artifact_id or 'None'}",
        f"- Artifact files: {checklist.artifact_file_count}",
        f"- Zip files: {checklist.zip_file_count}",
        f"- Zip checksum: {checklist.zip_checksum_sha256 or 'None'}",
        f"- Zip verification ready: {checklist.zip_verification_ready}",
        f"- Verification audit records: {checklist.verification_audit_count}",
        f"- Boundary: {checklist.boundary}",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist.checklist_items)
    lines.extend(["", "## Missing Gates"])
    lines.extend(f"- {item}" for item in checklist.missing_gates) if checklist.missing_gates else lines.append("- None")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in checklist.blockers) if checklist.blockers else lines.append("- None")
    lines.extend(["", "## Warnings"])
    lines.extend(f"- {item}" for item in checklist.warnings) if checklist.warnings else lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in checklist.next_actions)
    return "\n".join(lines) + "\n"


def render_player_support_handoff_readiness_checklist_csv(
    checklist: PlayerSupportHandoffReadinessChecklist,
) -> str:
    rows = [
        "ready,maturity_label,latest_artifact_id,artifact_file_count,zip_file_count,zip_verification_ready,verification_audit_count,missing_gate_count,blocker_count,warning_count",
        ",".join(
            [
                _csv(str(checklist.ready)),
                _csv(checklist.maturity_label),
                _csv(checklist.latest_artifact_id or ""),
                _csv(str(checklist.artifact_file_count)),
                _csv(str(checklist.zip_file_count)),
                _csv(str(checklist.zip_verification_ready)),
                _csv(str(checklist.verification_audit_count)),
                _csv(str(len(checklist.missing_gates))),
                _csv(str(len(checklist.blockers))),
                _csv(str(len(checklist.warnings))),
            ]
        ),
        "section,value",
    ]
    rows.extend(f"missing_gate,{_csv(item)}" for item in checklist.missing_gates)
    rows.extend(f"blocker,{_csv(item)}" for item in checklist.blockers)
    rows.extend(f"warning,{_csv(item)}" for item in checklist.warnings)
    rows.extend(f"next_action,{_csv(item)}" for item in checklist.next_actions)
    return "\n".join(rows) + "\n"


def _missing_debug_bundle_review() -> SupportReviewReport:
    report = review_account_debug_bundle({})
    report.overall_status = "debug_bundle_not_provided"
    report.summary = "No account debug bundle was included in this support handoff."
    return report


def _support_handoff_next_actions(
    review: SupportReviewReport,
    session_artifact_bundle: PlayerSessionPacketArtifactBundle,
) -> list[str]:
    actions = [
        f"Open {session_artifact_bundle.manifest_path} and verify the checksum before reviewing packet files.",
        "Use packet.md for player-facing context and packet.csv for quick triage.",
    ]
    if review.overall_status == "debug_bundle_not_provided":
        actions.append("Ask the player to export a fresh debug bundle from Connect and attach it to a new handoff.")
    elif review.findings:
        actions.extend(finding.recommended_action for finding in review.findings[:5])
    else:
        actions.append("No account connection blocker is visible; continue normal Build Fit and value-analysis verification.")
    actions.append("Do not request raw keys or private account payloads during support follow-up.")
    return actions


def _verify_support_handoff_zip_payloads(archive: ZipFile, names: list[str], blockers: list[str]) -> None:
    manifest_name = "player_support_handoff/manifest.json"
    handoff_json_name = "player_support_handoff/handoff.json"
    handoff_md_name = "player_support_handoff/handoff.md"
    handoff_csv_name = "player_support_handoff/handoff.csv"
    if manifest_name in names:
        try:
            manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
            if manifest.get("schema_version") != "gw2radar.player_support_handoff_artifact_manifest.v1":
                blockers.append("support handoff artifact manifest schema mismatch")
            for flag in ["contains_raw_key", "contains_raw_debug_bundle", "contains_private_source_payload"]:
                if manifest.get(flag) is not False:
                    blockers.append(f"support handoff artifact manifest has unsafe flag: {flag}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            blockers.append(f"support handoff artifact manifest validation failed: {exc}")
    if handoff_json_name in names:
        try:
            PlayerSupportHandoffBundle.model_validate_json(archive.read(handoff_json_name).decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            blockers.append(f"support handoff JSON validation failed: {exc}")
    if handoff_md_name in names:
        try:
            markdown = archive.read(handoff_md_name).decode("utf-8")
            if "Player Support Handoff Bundle" not in markdown:
                blockers.append("support handoff Markdown title is missing")
        except UnicodeDecodeError as exc:
            blockers.append(f"support handoff Markdown is not UTF-8: {exc}")
    if handoff_csv_name in names:
        try:
            csv_text = archive.read(handoff_csv_name).decode("utf-8")
            if "metric,value" not in csv_text or "support_status" not in csv_text:
                blockers.append("support handoff CSV header mismatch")
        except UnicodeDecodeError as exc:
            blockers.append(f"support handoff CSV is not UTF-8: {exc}")


def _safe_support_text(value: str | None, *, max_length: int) -> str:
    text = " ".join(str(value or "").split())
    cleaned = "".join(character for character in text if character.isprintable())
    return (cleaned or "support")[:max_length]


def _unique_text(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for item in items:
        if item and item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


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


def _history_correlation_boundaries() -> list[str]:
    return [
        "Correlation is explanatory planning metadata only.",
        "GW2Radar does not infer causality, automate trades, change gear, craft items, or guarantee outcomes.",
        "Raw API keys and private account source payloads are excluded from history correlation output.",
    ]


def _session_packet_support_prompts(
    readiness: PlayerReadinessSummary,
    account_value: AccountValueSnapshot,
    correlation: PlayerHistoryCorrelation,
) -> list[str]:
    prompts: list[str] = []
    if readiness.readiness_label != "ready":
        prompts.append("Review non-ready readiness checks before asking the player for more data.")
    if account_value.diagnostics.price_coverage_percent < 100:
        prompts.append("Explain which price coverage gaps remain and suggest a safe refresh path.")
    if correlation.status in {"needs_review", "changed"}:
        prompts.append("Compare readiness and value history together before attributing the change to sync or prices.")
    if not prompts:
        prompts.append("Session looks consistent at MVP depth; recommend normal manual planning review.")
    prompts.append("Never request raw API keys or raw private account payloads from the player.")
    return prompts


def _artifact_file_entry(root: Path, file_path: Path, file_name: str, media_type: str, text: str) -> PlayerSessionPacketArtifactFile:
    return PlayerSessionPacketArtifactFile(
        file_name=file_name,
        relative_path=file_path.relative_to(root).as_posix(),
        media_type=media_type,
        size_bytes=len(text.encode("utf-8")),
        checksum_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


def _artifact_bundle_checksum(files: list[PlayerSessionPacketArtifactFile]) -> str:
    return hashlib.sha256(
        "\n".join(f"{file.file_name}:{file.checksum_sha256}" for file in sorted(files, key=lambda item: item.file_name)).encode("utf-8")
    ).hexdigest()


def _packet_media_type(file_name: str) -> str:
    if file_name.endswith(".json"):
        return "application/json"
    if file_name.endswith(".md"):
        return "text/markdown; charset=utf-8"
    if file_name.endswith(".csv"):
        return "text/csv; charset=utf-8"
    return "text/plain; charset=utf-8"
