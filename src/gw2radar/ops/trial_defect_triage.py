from __future__ import annotations

from pydantic import BaseModel, Field

from gw2radar.ops.final_closeout import build_final_closeout_dashboard


class TrialChecklistItem(BaseModel):
    item_id: str
    label: str
    endpoint: str
    expected_result: str
    operator_note: str


class TrialReadinessChecklist(BaseModel):
    schema_version: str = "gw2radar.trial_readiness_checklist.v1"
    status: str
    checklist: list[TrialChecklistItem]
    defect_intake_channels: list[str]
    safety_boundaries: list[str]
    next_priority: str


class TrialDefectReport(BaseModel):
    symptom: str
    api_key_saved: bool = False
    permissions_ready: bool = False
    sync_queued: bool = False
    sync_succeeded: bool = False
    private_snapshot_count: int = 0
    character_snapshot_count: int = 0
    result_count: int = 0
    ui_result_visible: bool = False
    raw_key_included: bool = False
    notes: list[str] = Field(default_factory=list)


class TrialDefectTriage(BaseModel):
    schema_version: str = "gw2radar.trial_defect_triage.v1"
    classification: str
    severity: str
    user_message: str
    operator_actions: list[str]
    evidence_needed: list[str]
    product_fix_hint: str
    safe_to_store: bool
    boundary: str


class TrialDefectDashboard(BaseModel):
    schema_version: str = "gw2radar.trial_defect_dashboard.v1"
    status: str
    supported_classifications: list[str]
    primary_trial_entrypoints: list[str]
    defect_intake_channels: list[str]
    stop_line_policy: str
    safety_boundaries: list[str]
    next_priority: str


def build_trial_readiness_checklist() -> TrialReadinessChecklist:
    closeout = build_final_closeout_dashboard()
    return TrialReadinessChecklist(
        status=closeout.status,
        checklist=[
            TrialChecklistItem(
                item_id="connect_key",
                label="Connect GW2 API key",
                endpoint="/account/api-key/status",
                expected_result="masked configured key status or clear missing-key action",
                operator_note="Never ask the player to send the raw key.",
            ),
            TrialChecklistItem(
                item_id="inspect_permissions",
                label="Inspect permissions",
                endpoint="/account/api-key/permissions",
                expected_result="required permission readiness or missing permission list",
                operator_note="Missing permissions should produce limited mode, not silent empty results.",
            ),
            TrialChecklistItem(
                item_id="run_diagnostic",
                label="Run connection diagnostic",
                endpoint="/account/diagnostic",
                expected_result="step-level status for key, permission, sync, private layer, and Build Fit bridge",
                operator_note="Use diagnostic next_actions before asking for a support bundle.",
            ),
            TrialChecklistItem(
                item_id="generate_debug_bundle",
                label="Generate privacy-safe debug bundle",
                endpoint="/account/debug-bundle",
                expected_result="metadata-only bundle with no raw key or private payload",
                operator_note="Bundle can be reviewed and audited through the support workflow.",
            ),
            TrialChecklistItem(
                item_id="triage_empty_result",
                label="Triage empty or invisible result",
                endpoint="/api/v1/ops/trial/defect-triage",
                expected_result="classification, severity, operator actions, and evidence needed",
                operator_note="Use when users report no visible output after connecting a valid key.",
            ),
        ],
        defect_intake_channels=closeout.defect_intake_channels,
        safety_boundaries=closeout.safety_boundaries,
        next_priority="Run real user trial on account connection and capture only privacy-safe defect metadata.",
    )


def triage_trial_defect(report: TrialDefectReport) -> TrialDefectTriage:
    if report.raw_key_included:
        return _triage(
            "raw_key_shared",
            "p0",
            "Please remove the raw key from the report and rotate it in ArenaNet account settings before continuing.",
            ["Discard the unsafe report copy.", "Ask for a privacy-safe debug bundle instead.", "Confirm no raw key was stored."],
            ["redaction_policy", "support_audit.boundary"],
            "Block support intake when pasted text appears to include a raw key.",
            safe_to_store=False,
        )
    if not report.api_key_saved:
        return _triage(
            "api_key_not_saved",
            "p1",
            "GW2Radar does not see a saved API key yet. Save the key, then run the connection diagnostic again.",
            ["Check /account/api-key/status.", "Keep key input and save action visible.", "Do not request the raw key."],
            ["key_status.is_configured", "diagnostic_summary.checks.api_key_stored"],
            "Surface a clear saved-key status beside the Connect action.",
        )
    if not report.permissions_ready:
        return _triage(
            "missing_permissions",
            "p1",
            "The key is saved, but required permissions are missing or could not be confirmed.",
            ["Check /account/api-key/permissions.", "Show missing permissions.", "Ask the player to update permissions and resync."],
            ["permission_summary.missing_required_permissions", "diagnostic_summary.checks.permissions_ready"],
            "Turn missing permissions into visible limited-mode guidance instead of empty outputs.",
        )
    if not report.sync_queued:
        return _triage(
            "sync_not_started",
            "p1",
            "The key and permissions look usable, but no account sync job is visible yet.",
            ["Ask the player to click Sync now.", "Check account sync queue status.", "Re-run diagnostic after queueing."],
            ["sync_summary.status", "diagnostic_summary.checks.sync_job_visible"],
            "Make Sync now the primary next action after a valid key is saved.",
        )
    if not report.sync_succeeded:
        return _triage(
            "sync_pending_or_failed",
            "p1",
            "A sync job is visible, but it has not completed successfully yet.",
            ["Check worker health and latest endpoint status.", "Surface retryable endpoint errors.", "Drain one job in dev if needed."],
            ["sync_summary.latest", "worker_health.status", "endpoint_progress"],
            "Expose pending/failed sync states near account-aware result panels.",
        )
    if report.private_snapshot_count <= 0:
        return _triage(
            "private_layer_empty",
            "p1",
            "Sync completed, but no private account snapshot is available for account-aware results.",
            ["Check private graph layer writes.", "Inspect sync endpoint success counts.", "Re-run sync if private layer is empty."],
            ["snapshot_summary.private_player_state_count", "diagnostic_summary.checks.private_snapshot_written"],
            "Show private-layer empty as a backend state, not a blank report area.",
        )
    if report.character_snapshot_count <= 0:
        return _triage(
            "character_snapshot_empty",
            "p2",
            "Account data exists, but character snapshots are missing for build-aware results.",
            ["Confirm character permission.", "Ask player to resync.", "Show manual snapshot fallback where available."],
            ["snapshot_summary.synced_character_snapshot_count", "permission_summary.missing_required_permissions"],
            "Distinguish account value readiness from Build Fit character readiness.",
        )
    if report.result_count <= 0:
        return _triage(
            "result_generation_empty",
            "p1",
            "Required account data exists, but the selected workflow did not generate a result.",
            ["Capture selected view and build/goal id.", "Check report entitlement or selected goal.", "Review API response body for warnings."],
            ["client_state.active_view", "client_state.active_build_id_present", "api_response.warning_count"],
            "Render empty-state warnings with missing selected goal/build context.",
        )
    if not report.ui_result_visible:
        return _triage(
            "ui_flow_incomplete",
            "p2",
            "The backend appears ready, but the result is not visible in the current UI flow.",
            ["Capture active view and selected tab.", "Check browser console only for metadata-safe errors.", "Add a guided next-step card."],
            ["client_state.active_view", "client_state.active_build_id_present", "ui_state.visible_result_count"],
            "Make ready-but-hidden results visible through a guided next-step card.",
        )
    return _triage(
        "no_defect_detected",
        "info",
        "The submitted metadata indicates the key, sync, backend result, and UI visibility are ready.",
        ["Ask for a fresh privacy-safe debug bundle if the user still sees no output.", "Confirm the exact workflow and timestamp."],
        ["diagnostic_summary.summary_status", "ui_state.visible_result_count"],
        "Keep the defect intake focused on exact workflow and timestamp when automated checks look ready.",
    )


def build_trial_defect_dashboard() -> TrialDefectDashboard:
    checklist = build_trial_readiness_checklist()
    return TrialDefectDashboard(
        status=checklist.status,
        supported_classifications=[
            "raw_key_shared",
            "api_key_not_saved",
            "missing_permissions",
            "sync_not_started",
            "sync_pending_or_failed",
            "private_layer_empty",
            "character_snapshot_empty",
            "result_generation_empty",
            "ui_flow_incomplete",
            "no_defect_detected",
        ],
        primary_trial_entrypoints=[item.endpoint for item in checklist.checklist],
        defect_intake_channels=checklist.defect_intake_channels,
        stop_line_policy="Do not add broad new phases during trial; fix reproducible defects and diagnostics gaps.",
        safety_boundaries=checklist.safety_boundaries,
        next_priority="Use real trial reports to prioritize API key diagnostics, empty-state UX, and support bundle clarity.",
    )


def render_trial_readiness_checklist_markdown(checklist: TrialReadinessChecklist) -> str:
    lines = [
        "# Real User Trial Readiness",
        "",
        f"- Schema: {checklist.schema_version}",
        f"- Status: {checklist.status}",
        "",
        "## Checklist",
        "",
        "| Item | Endpoint | Expected Result | Operator Note |",
        "| --- | --- | --- | --- |",
    ]
    for item in checklist.checklist:
        lines.append(f"| {item.label} | `{item.endpoint}` | {item.expected_result} | {item.operator_note} |")
    lines.extend(["", "## Defect Intake Channels", ""])
    for channel in checklist.defect_intake_channels:
        lines.append(f"- {channel}")
    lines.extend(["", "## Safety Boundaries", ""])
    for boundary in checklist.safety_boundaries:
        lines.append(f"- {boundary}")
    lines.extend(["", "## Next Priority", "", checklist.next_priority, ""])
    return "\n".join(lines)


def render_trial_defect_dashboard_markdown(dashboard: TrialDefectDashboard) -> str:
    lines = [
        "# Trial Defect Triage Dashboard",
        "",
        f"- Schema: {dashboard.schema_version}",
        f"- Status: {dashboard.status}",
        f"- Stop-line policy: {dashboard.stop_line_policy}",
        "",
        "## Supported Classifications",
        "",
    ]
    for classification in dashboard.supported_classifications:
        lines.append(f"- {classification}")
    lines.extend(["", "## Primary Trial Entrypoints", ""])
    for endpoint in dashboard.primary_trial_entrypoints:
        lines.append(f"- `{endpoint}`")
    lines.extend(["", "## Next Priority", "", dashboard.next_priority, ""])
    return "\n".join(lines)


def render_trial_defect_dashboard_csv(dashboard: TrialDefectDashboard) -> str:
    rows = ["classification,status"]
    for classification in dashboard.supported_classifications:
        rows.append(f"{classification},supported")
    return "\n".join(rows) + "\n"


def _triage(
    classification: str,
    severity: str,
    user_message: str,
    operator_actions: list[str],
    evidence_needed: list[str],
    product_fix_hint: str,
    *,
    safe_to_store: bool = True,
) -> TrialDefectTriage:
    return TrialDefectTriage(
        classification=classification,
        severity=severity,
        user_message=user_message,
        operator_actions=operator_actions,
        evidence_needed=evidence_needed,
        product_fix_hint=product_fix_hint,
        safe_to_store=safe_to_store,
        boundary=(
            "Trial defect triage stores metadata only; raw API keys, private account payloads, and raw debug bundles are excluded."
        ),
    )
