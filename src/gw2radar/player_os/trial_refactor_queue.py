from __future__ import annotations

from csv import DictWriter
from io import StringIO

from pydantic import BaseModel, Field

from gw2radar.support.account_debug_bundle_audit import SupportReviewBacklogSummary, SupportReviewMetricsSummary


class TrialRefactorTask(BaseModel):
    task_id: str
    blocker_id: str
    priority: str
    title: str
    affected_cases: int
    refactor_scope: str
    target_files: list[str] = Field(default_factory=list)
    api_routes: list[str] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    verification_commands: list[str] = Field(default_factory=list)
    safety_boundary: str


class TrialRefactorQueue(BaseModel):
    schema_version: str = "gw2radar.player_os_trial_refactor_queue.v1"
    total_records: int
    task_count: int
    tasks: list[TrialRefactorTask] = Field(default_factory=list)
    summary: str
    boundary: str = (
        "Refactor queue is generated from aggregated Player OS trial feedback metadata only; "
        "it does not include raw feedback, raw API keys, private account payloads, or automatic code changes."
    )


class TrialFeedbackActionBundle(BaseModel):
    schema_version: str = "gw2radar.player_os_trial_feedback_action_bundle.v1"
    metrics: dict
    backlog: dict
    refactor_queue: TrialRefactorQueue
    next_operator_actions: list[str] = Field(default_factory=list)
    readiness_label: str
    boundary: str = (
        "Action bundle combines metadata-only trial metrics, backlog, and targeted refactor tasks for manual operator review."
    )


TASK_TEMPLATES: dict[str, dict] = {
    "intent_not_captured": {
        "refactor_scope": "Player OS intent entry and empty-state guidance",
        "target_files": [
            "src/gw2radar/ui/static/player.html",
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/player_os/intent/intent_parser.py",
        ],
        "api_routes": ["/api/v1/intents/parse", "/api/v1/intents/start"],
        "steps": [
            "Add a visible empty-intent recovery state before plan generation.",
            "Keep the selected template or typed intent visible after failed parsing.",
            "Return a structured next action instead of a silent empty plan.",
        ],
    },
    "plan_not_generated": {
        "refactor_scope": "Player OS plan generation diagnostics",
        "target_files": [
            "src/gw2radar/player_os/orchestration/player_os_orchestrator.py",
            "src/gw2radar/ui/static/app.js",
        ],
        "api_routes": ["/api/v1/intents/start", "/api/v1/plans/{plan_id}"],
        "steps": [
            "Expose plan generation status and missing action reasons in the plan panel.",
            "Add a retry path that preserves intent constraints.",
            "Assert that an empty action list renders a visible operator-safe diagnostic.",
        ],
    },
    "deep_link_not_opened": {
        "refactor_scope": "Player OS action bridge confirmation",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/ui/static/player.html",
        ],
        "api_routes": ["/api/v1/player-os/trial-feedback/review"],
        "steps": [
            "Record a post-click bridge confirmation for every Player OS action button.",
            "Display the target module and expected next manual action after bridge navigation.",
            "Refresh the trial checklist immediately after bridge confirmation.",
        ],
    },
    "target_result_not_run": {
        "refactor_scope": "Player OS target result action prominence",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/ui/static/player.html",
        ],
        "api_routes": ["/api/v1/player-os/trial-feedback/review"],
        "steps": [
            "Keep the next target-module result action visible after deep-link navigation.",
            "Disable trial-ready messaging until the target result action is completed.",
            "Write last_result metadata only after the expected action succeeds.",
        ],
    },
    "target_result_empty_after_run": {
        "refactor_scope": "Target-module empty result diagnostics",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/player_os/trial_feedback_review.py",
            "src/gw2radar/api/routes/player_dashboard.py",
        ],
        "api_routes": [
            "/api/v1/legendary/recompute",
            "/api/v1/builds/fit",
            "/api/v1/market/signals",
            "/api/v1/player/readiness",
        ],
        "steps": [
            "Map target action result payloads to explicit empty/ready diagnostics.",
            "Preserve the result status in trial feedback metadata.",
            "Show a support-safe next action when a target module returns empty output.",
        ],
    },
    "report_preview_not_opened": {
        "refactor_scope": "Player OS report handoff confirmation",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/ui/static/player.html",
        ],
        "api_routes": ["/api/v1/reports/{report_id}", "/api/v1/reports/{report_id}/revise"],
        "steps": [
            "Keep Player OS report preview controls visible until the Reports view confirms render.",
            "Show report id, preview status, and retry action in the cockpit.",
            "Update trial checklist status after report preview render.",
        ],
    },
    "feedback_packet_incomplete": {
        "refactor_scope": "Trial checklist export gating",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/ui/static/player.html",
        ],
        "api_routes": ["/api/v1/player-os/trial-feedback/review"],
        "steps": [
            "Warn before exporting feedback while gates are incomplete.",
            "Include the incomplete gate ids in the export confirmation.",
            "Keep export metadata-only and do not include raw account payloads.",
        ],
    },
    "result_generation_empty": {
        "refactor_scope": "Target-module result completion checks",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/ui/static/player.html",
            "src/gw2radar/api/routes/player_dashboard.py",
        ],
        "api_routes": [
            "/api/v1/legendary/recompute",
            "/api/v1/builds/fit",
            "/api/v1/market/radar",
            "/api/v1/player/dashboard",
        ],
        "steps": [
            "Map each bridge target to one explicit module result action.",
            "Surface visible empty-result diagnostics when the target action returns no user-facing output.",
            "Attach the target action status to trial feedback metadata.",
        ],
    },
    "privacy_boundary_violation": {
        "refactor_scope": "Trial feedback privacy preflight",
        "target_files": [
            "src/gw2radar/ui/static/app.js",
            "src/gw2radar/player_os/trial_feedback_review.py",
        ],
        "api_routes": ["/api/v1/player-os/trial-feedback/review"],
        "steps": [
            "Block export if sensitive-looking fields are present in client state.",
            "Keep server-side sensitive key detection as a second line of defense.",
            "Show a clear discard-and-reexport support message.",
        ],
    },
}


def build_trial_refactor_queue(backlog: SupportReviewBacklogSummary) -> TrialRefactorQueue:
    tasks = [_task_from_backlog_item(item) for item in backlog.backlog_items]
    tasks.sort(key=lambda task: (_priority_rank(task.priority), -task.affected_cases, task.task_id))
    return TrialRefactorQueue(
        total_records=backlog.total_records,
        task_count=len(tasks),
        tasks=tasks,
        summary=_queue_summary(backlog.total_records, tasks),
    )


def build_trial_feedback_action_bundle(
    *,
    metrics: SupportReviewMetricsSummary,
    backlog: SupportReviewBacklogSummary,
    queue: TrialRefactorQueue,
) -> TrialFeedbackActionBundle:
    return TrialFeedbackActionBundle(
        metrics=metrics.model_dump(mode="json"),
        backlog=backlog.model_dump(mode="json"),
        refactor_queue=queue,
        next_operator_actions=_next_operator_actions(queue),
        readiness_label=_readiness_label(queue),
    )


def render_trial_refactor_queue_markdown(queue: TrialRefactorQueue) -> str:
    lines = [
        "# Player OS Trial Targeted Refactor Queue",
        "",
        f"Summary: {queue.summary}",
        f"Boundary: {queue.boundary}",
        "",
    ]
    if not queue.tasks:
        lines.append("No targeted refactor tasks are generated for the current filters.")
        return "\n".join(lines) + "\n"
    for task in queue.tasks:
        lines.extend(
            [
                f"## {task.priority} - {task.title}",
                "",
                f"- Task ID: `{task.task_id}`",
                f"- Blocker: `{task.blocker_id}`",
                f"- Affected cases: {task.affected_cases}",
                f"- Scope: {task.refactor_scope}",
                f"- API routes: {', '.join(task.api_routes) if task.api_routes else 'none'}",
                "- Target files:",
            ]
        )
        lines.extend(f"  - `{path}`" for path in task.target_files)
        lines.extend(["- Implementation steps:"])
        lines.extend(f"  - {step}" for step in task.implementation_steps)
        lines.extend(["- Acceptance criteria:"])
        lines.extend(f"  - {criterion}" for criterion in task.acceptance_criteria)
        lines.extend(["- Verification:"])
        lines.extend(f"  - `{command}`" for command in task.verification_commands)
        lines.extend(["", f"Safety boundary: {task.safety_boundary}", ""])
    return "\n".join(lines)


def render_trial_refactor_queue_csv(queue: TrialRefactorQueue) -> str:
    output = StringIO()
    fieldnames = [
        "task_id",
        "priority",
        "blocker_id",
        "title",
        "affected_cases",
        "refactor_scope",
        "target_files",
        "api_routes",
        "verification_commands",
    ]
    writer = DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for task in queue.tasks:
        writer.writerow(
            {
                "task_id": task.task_id,
                "priority": task.priority,
                "blocker_id": task.blocker_id,
                "title": task.title,
                "affected_cases": task.affected_cases,
                "refactor_scope": task.refactor_scope,
                "target_files": " | ".join(task.target_files),
                "api_routes": " | ".join(task.api_routes),
                "verification_commands": " | ".join(task.verification_commands),
            }
        )
    return output.getvalue()


def _task_from_backlog_item(item) -> TrialRefactorTask:
    template = TASK_TEMPLATES.get(item.blocker_id, {})
    return TrialRefactorTask(
        task_id=f"trial-refactor-{item.blocker_id}",
        blocker_id=item.blocker_id,
        priority=item.priority,
        title=item.title,
        affected_cases=item.affected_cases,
        refactor_scope=template.get("refactor_scope", "Manual Player OS support review"),
        target_files=list(template.get("target_files", ["src/gw2radar/ui/static/app.js"])),
        api_routes=list(template.get("api_routes", ["/api/v1/player-os/trial-feedback/review"])),
        implementation_steps=list(template.get("steps", [item.product_fix_suggestion])),
        acceptance_criteria=list(item.acceptance_criteria)
        + [
            "The fix is covered by a targeted pytest or harness smoke check.",
            "Generated output remains metadata-only and excludes raw API keys or private account payloads.",
        ],
        verification_commands=[
            "python -m pytest tests/player_os tests/test_support_review_ui.py -q",
            "python harness/run_stage_gate.py stage",
        ],
        safety_boundary="Manual targeted refactor task only; it does not automate gameplay, trading, external publishing, or code changes.",
    )


def _queue_summary(total_records: int, tasks: list[TrialRefactorTask]) -> str:
    if not tasks:
        return "No Player OS trial blockers are present for the current filters."
    top = tasks[0]
    return f"{len(tasks)} targeted refactor tasks generated from {total_records} trial audit records; top task is {top.priority} `{top.blocker_id}`."


def _next_operator_actions(queue: TrialRefactorQueue) -> list[str]:
    if not queue.tasks:
        return ["Continue collecting metadata-only Player OS trial feedback before scheduling refactors."]
    actions = [f"Start with {queue.tasks[0].task_id} because it has the highest priority/support signal."]
    actions.append("Implement only one targeted refactor at a time and rerun the stage gate after each slice.")
    actions.append("Keep trial feedback exports metadata-only; collect account debug bundles separately only when module results remain empty.")
    return actions


def _readiness_label(queue: TrialRefactorQueue) -> str:
    if queue.task_count == 0:
        return "monitor"
    if any(task.priority == "P0" for task in queue.tasks):
        return "urgent_refactor_ready"
    return "targeted_refactor_ready"


def _priority_rank(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(priority, 9)
