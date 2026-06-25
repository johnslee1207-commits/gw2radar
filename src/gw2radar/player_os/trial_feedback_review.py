from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import SupportReviewAuditModel


EXPECTED_FEEDBACK_SCHEMA = "gw2radar.player_os_trial_feedback.v1"
EXPECTED_CHECKLIST_SCHEMA = "gw2radar.player_os_trial_checklist.v1"
REVIEW_SCHEMA = "gw2radar.player_os_trial_feedback_review.v1"
SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "raw_key",
    "encrypted_value",
    "private_payload",
    "equipment_payload",
    "inventory_payload",
    "bank_payload",
    "materials_payload",
    "wallet_payload",
    "characters_payload",
)


class PlayerOsTrialFeedbackFinding(BaseModel):
    finding_id: str
    severity: str
    title: str
    player_message: str
    recommended_action: str
    evidence_refs: list[str] = Field(default_factory=list)


class PlayerOsTrialFeedbackReview(BaseModel):
    schema_version: str = REVIEW_SCHEMA
    feedback_schema_version: str | None = None
    checklist_schema_version: str | None = None
    overall_status: str
    summary: str
    support_classification: str
    ready_gate_count: int = 0
    total_gate_count: int = 0
    plan_id: str | None = None
    report_id: str | None = None
    last_bridge_target: str | None = None
    findings: list[PlayerOsTrialFeedbackFinding] = Field(default_factory=list)
    player_reply_template: str
    operator_next_actions: list[str] = Field(default_factory=list)
    redaction_boundary: list[str] = Field(
        default_factory=lambda: [
            "Do not request or store a raw GW2 API key.",
            "Do not include private account payloads, inventory, bank, wallet, material, character, or equipment data.",
            "Use Player OS checklist gates, plan/report ids, bridge target, and UI state metadata only.",
        ]
    )


def create_player_os_trial_feedback_audit(
    session: Session,
    *,
    review: PlayerOsTrialFeedbackReview,
    reviewer: str | None = None,
    source: str = "player_os_trial_feedback",
) -> dict[str, Any]:
    finding_ids = [finding.finding_id for finding in review.findings]
    severities = [finding.severity for finding in review.findings]
    record = SupportReviewAuditModel(
        case_id=f"player-os-trial-feedback-{uuid4().hex}",
        bundle_schema_version=review.feedback_schema_version,
        review_schema_version=review.schema_version,
        overall_status=review.overall_status,
        summary=review.summary,
        highest_severity=_highest_severity(severities),
        finding_count=len(review.findings),
        finding_ids_json=finding_ids,
        reviewer=_safe_text(reviewer or "support", max_length=80),
        source=_safe_text(source, max_length=80),
        reply_template_summary=_safe_text(review.player_reply_template, max_length=360),
        properties_json={
            "checklist_schema_version": review.checklist_schema_version,
            "support_classification": review.support_classification,
            "ready_gate_count": review.ready_gate_count,
            "total_gate_count": review.total_gate_count,
            "plan_id": review.plan_id,
            "report_id": review.report_id,
            "last_bridge_target": review.last_bridge_target,
            "evidence_refs": [ref for finding in review.findings for ref in finding.evidence_refs],
            "redaction_boundary": list(review.redaction_boundary),
            "stores_raw_feedback": False,
            "stores_raw_bundle": False,
            "stores_raw_api_key": False,
            "stores_private_account_payload": False,
        },
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return {
        "case_id": record.case_id,
        "bundle_schema_version": record.bundle_schema_version,
        "review_schema_version": record.review_schema_version,
        "overall_status": record.overall_status,
        "summary": record.summary,
        "highest_severity": record.highest_severity,
        "finding_count": record.finding_count,
        "finding_ids": list(record.finding_ids_json or []),
        "reviewer": record.reviewer,
        "source": record.source,
        "reply_template_summary": record.reply_template_summary,
        "properties": dict(record.properties_json or {}),
        "created_at": record.created_at.isoformat(),
    }


def review_player_os_trial_feedback(feedback: dict[str, Any]) -> PlayerOsTrialFeedbackReview:
    findings: list[PlayerOsTrialFeedbackFinding] = []
    if not isinstance(feedback, dict):
        findings.append(
            _finding(
                "invalid_feedback",
                "critical",
                "Trial feedback is not a JSON object",
                "The uploaded Player OS trial feedback file is not valid review input.",
                "Export a fresh Player OS trial feedback JSON from the Dashboard checklist.",
                ["$"],
            )
        )
        return _review(None, None, {}, {}, findings)

    sensitive_paths = _find_sensitive_paths(feedback)
    if sensitive_paths:
        findings.append(
            _finding(
                "privacy_boundary_violation",
                "critical",
                "Trial feedback includes sensitive fields",
                "This file appears to include fields outside the Player OS metadata-only boundary.",
                "Discard this file and export fresh trial feedback; do not share raw keys or private account payloads.",
                sensitive_paths[:12],
            )
        )

    feedback_schema = _string_or_none(feedback.get("schema_version"))
    if feedback_schema != EXPECTED_FEEDBACK_SCHEMA:
        findings.append(
            _finding(
                "invalid_feedback",
                "critical",
                "Trial feedback schema is not recognized",
                "The support file does not match the current Player OS trial feedback format.",
                "Use Export trial feedback from this GW2Radar build, then review that file.",
                ["schema_version"],
            )
        )

    checklist = _as_dict(feedback.get("checklist"))
    checklist_schema = _string_or_none(checklist.get("schema_version"))
    if checklist_schema != EXPECTED_CHECKLIST_SCHEMA:
        findings.append(
            _finding(
                "invalid_checklist",
                "critical",
                "Trial checklist schema is missing or not recognized",
                "The feedback does not include a current Player OS trial checklist.",
                "Refresh the trial checklist, complete the Player OS path again, and export new feedback.",
                ["checklist.schema_version"],
            )
        )

    rows = _rows_by_id(checklist.get("rows"))
    _append_gate_finding(
        findings,
        rows,
        "intent",
        "intent_not_captured",
        "Intent was not captured",
        "The player has not started from a recognized Player OS intent.",
        "Enter a goal or choose What should I do now, then build the Player OS plan again.",
        "checklist.rows.intent",
    )
    _append_gate_finding(
        findings,
        rows,
        "plan",
        "plan_not_generated",
        "Player OS plan was not generated",
        "The Player OS flow did not produce a plan with next actions.",
        "Start the intent again and confirm the plan panel shows actions before moving to another module.",
        "checklist.rows.plan",
    )
    _append_gate_finding(
        findings,
        rows,
        "deep_link",
        "deep_link_not_opened",
        "Plan action was not opened into a module",
        "The player has a plan but has not opened a deep-link action into Legendary, Build Fit, Market, or readiness.",
        "Click one Player OS action button, verify the target module opens, then continue the module-specific result flow.",
        "checklist.rows.deep_link",
    )
    _append_gate_finding(
        findings,
        rows,
        "report_preview",
        "report_preview_not_opened",
        "Report preview was not opened",
        "The trial did not reach the Player OS report preview handoff.",
        "Open the Player OS report from the plan panel and confirm the Reports view renders the preview.",
        "checklist.rows.report_preview",
    )
    _append_gate_finding(
        findings,
        rows,
        "feedback_packet",
        "feedback_packet_incomplete",
        "Feedback metadata packet is incomplete",
        "The exported trial feedback is missing one or more checklist gates.",
        "Complete intent, plan, deep-link, and report preview gates before exporting feedback.",
        "checklist.rows.feedback_packet",
    )

    ready_count = _int_value(checklist.get("ready_count"))
    total_count = _int_value(checklist.get("total_count"))
    if not findings and checklist.get("status") == "ready":
        findings.append(
            _finding(
                "result_generation_empty",
                "info",
                "Trial gates are ready but no expected player result was reported",
                "Player OS gates are complete, so the next issue is likely inside the target module result step.",
                "Ask which target module was opened, then run the module-specific result action such as recompute, evaluate, or report preview.",
                ["checklist.status", "player_os_context.last_bridge.target_view", "player_os_context.report_id"],
            )
        )

    return _review(feedback_schema, checklist_schema, feedback, checklist, findings, ready_count, total_count)


def _review(
    feedback_schema: str | None,
    checklist_schema: str | None,
    feedback: dict[str, Any],
    checklist: dict[str, Any],
    findings: list[PlayerOsTrialFeedbackFinding],
    ready_count: int | None = None,
    total_count: int | None = None,
) -> PlayerOsTrialFeedbackReview:
    context = _as_dict(feedback.get("player_os_context"))
    last_bridge = _as_dict(context.get("last_bridge") or checklist.get("last_bridge"))
    overall_status = _overall_status(findings)
    return PlayerOsTrialFeedbackReview(
        feedback_schema_version=feedback_schema,
        checklist_schema_version=checklist_schema,
        overall_status=overall_status,
        summary=_summary(overall_status),
        support_classification=overall_status,
        ready_gate_count=ready_count if ready_count is not None else _int_value(checklist.get("ready_count")),
        total_gate_count=total_count if total_count is not None else _int_value(checklist.get("total_count")),
        plan_id=_string_or_none(context.get("plan_id") or checklist.get("plan_id")),
        report_id=_string_or_none(context.get("report_id") or checklist.get("report_id")),
        last_bridge_target=_string_or_none(last_bridge.get("target_view") or last_bridge.get("targetView")),
        findings=findings,
        player_reply_template=_reply_template(overall_status, findings),
        operator_next_actions=_operator_next_actions(overall_status),
    )


def _overall_status(findings: list[PlayerOsTrialFeedbackFinding]) -> str:
    if not findings:
        return "ready"
    priority = [
        "privacy_boundary_violation",
        "invalid_feedback",
        "invalid_checklist",
        "intent_not_captured",
        "plan_not_generated",
        "deep_link_not_opened",
        "report_preview_not_opened",
        "feedback_packet_incomplete",
        "result_generation_empty",
    ]
    ids = {finding.finding_id for finding in findings}
    for status in priority:
        if status in ids:
            return status
    return "manual_review"


def _summary(overall_status: str) -> str:
    summaries = {
        "ready": "The Player OS trial feedback has no blocking metadata issue.",
        "privacy_boundary_violation": "The feedback must be discarded because it includes sensitive-looking fields.",
        "invalid_feedback": "The file is not a current Player OS trial feedback export.",
        "invalid_checklist": "The feedback is missing a current Player OS checklist.",
        "intent_not_captured": "The player needs to start from a recognized Player OS intent.",
        "plan_not_generated": "The Player OS plan did not generate next actions.",
        "deep_link_not_opened": "The player has not opened a plan action into a target module.",
        "report_preview_not_opened": "The Player OS report preview handoff has not been opened.",
        "feedback_packet_incomplete": "The trial feedback was exported before all required gates were ready.",
        "result_generation_empty": "Player OS gates are ready; inspect the target module result step next.",
    }
    return summaries.get(overall_status, "The Player OS trial feedback needs manual inspection.")


def _reply_template(overall_status: str, findings: list[PlayerOsTrialFeedbackFinding]) -> str:
    first = findings[0] if findings else None
    if first is None:
        return "\n".join(
            [
                "Your Player OS trial feedback looks complete.",
                "Please tell us which module result you expected to see next so we can check that specific result step.",
                "Do not send your raw GW2 API key or private account payloads.",
            ]
        )
    return "\n".join(
        [
            f"I reviewed your Player OS trial feedback. Current status: {overall_status}.",
            first.player_message,
            f"Next step: {first.recommended_action}",
            "Please do not send your raw GW2 API key or private account payloads.",
        ]
    )


def _operator_next_actions(overall_status: str) -> list[str]:
    actions = {
        "privacy_boundary_violation": ["Discard the uploaded file.", "Ask the player to export metadata-only trial feedback again."],
        "invalid_feedback": ["Confirm the player used the current build.", "Ask for a fresh Dashboard trial feedback export."],
        "invalid_checklist": ["Ask the player to refresh the trial checklist before exporting.", "Do not infer missing gates from memory."],
        "intent_not_captured": ["Guide the player to start from the Player OS intent box or template list."],
        "plan_not_generated": ["Check `/api/v1/intents/start` and plan panel rendering.", "Ask for a screenshot of the plan panel if needed."],
        "deep_link_not_opened": ["Ask which Player OS action button was clicked.", "Verify the target module deep-link opens."],
        "report_preview_not_opened": ["Ask the player to open the Player OS report preview.", "Verify Reports view bridge state."],
        "feedback_packet_incomplete": ["Have the player complete all checklist gates before export."],
        "result_generation_empty": ["Identify the last bridge target.", "Run the target module result action and collect a debug bundle if still empty."],
    }
    return actions.get(overall_status, ["Review the metadata-only findings and keep the no-secret boundary."])


def _append_gate_finding(
    findings: list[PlayerOsTrialFeedbackFinding],
    rows: dict[str, dict[str, Any]],
    row_id: str,
    finding_id: str,
    title: str,
    player_message: str,
    recommended_action: str,
    evidence_ref: str,
) -> None:
    row = rows.get(row_id)
    if row and row.get("ready") is True:
        return
    findings.append(_finding(finding_id, "warning", title, player_message, recommended_action, [evidence_ref]))


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    player_message: str,
    recommended_action: str,
    evidence_refs: list[str],
) -> PlayerOsTrialFeedbackFinding:
    return PlayerOsTrialFeedbackFinding(
        finding_id=finding_id,
        severity=severity,
        title=title,
        player_message=player_message,
        recommended_action=recommended_action,
        evidence_refs=evidence_refs,
    )


def _rows_by_id(value: Any) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    if not isinstance(value, list):
        return rows
    for row in value:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            rows[row["id"]] = row
    return rows


def _find_sensitive_paths(value: Any, prefix: str = "$") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{prefix}.{key_text}"
            if any(fragment in key_text.lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
                paths.append(child_path)
            paths.extend(_find_sensitive_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_find_sensitive_paths(child, f"{prefix}[{index}]"))
    return paths


def _highest_severity(severities: list[str]) -> str:
    rank = {"critical": 3, "warning": 2, "info": 1}
    if not severities:
        return "info"
    return max(severities, key=lambda value: rank.get(value, 0))


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_text(value: Any, *, max_length: int) -> str:
    text = str(value or "").replace("\x00", "").strip()
    return text[:max_length]
