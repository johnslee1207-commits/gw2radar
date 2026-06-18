from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


EXPECTED_BUNDLE_SCHEMA = "gw2radar.account_debug_bundle.v1"
REVIEW_SCHEMA = "gw2radar.account_debug_bundle_review.v1"
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
)


class SupportReviewFinding(BaseModel):
    finding_id: str
    severity: str
    title: str
    player_message: str
    recommended_action: str
    evidence_refs: list[str] = Field(default_factory=list)


class SupportReviewReport(BaseModel):
    schema_version: str = REVIEW_SCHEMA
    bundle_schema_version: str | None = None
    overall_status: str
    summary: str
    findings: list[SupportReviewFinding] = Field(default_factory=list)
    redaction_boundary: list[str] = Field(
        default_factory=lambda: [
            "Do not request or store a raw GW2 API key.",
            "Do not include private inventory, bank, wallet, material, achievement, or equipment payloads.",
            "Use counts, statuses, missing permissions, endpoint progress, and UI state flags only.",
        ]
    )


def review_account_debug_bundle(bundle: dict[str, Any]) -> SupportReviewReport:
    findings: list[SupportReviewFinding] = []
    bundle_schema = bundle.get("schema_version") if isinstance(bundle, dict) else None

    if not isinstance(bundle, dict):
        findings.append(
            _finding(
                "invalid_bundle",
                "critical",
                "Debug bundle is not a JSON object",
                "The uploaded support file is not a valid GW2Radar account debug bundle.",
                "Export a fresh debug bundle from the Connect panel and review that file.",
                ["$"],
            )
        )
        return _report(bundle_schema, "invalid_bundle", findings)

    sensitive_paths = _find_sensitive_paths(bundle)
    if sensitive_paths:
        findings.append(
            _finding(
                "privacy_boundary_violation",
                "critical",
                "Debug bundle includes sensitive fields",
                "This file appears to include fields outside the privacy-safe support boundary.",
                "Discard this file, export a fresh debug bundle, and do not share raw keys or private payloads.",
                sensitive_paths[:12],
            )
        )

    if bundle_schema != EXPECTED_BUNDLE_SCHEMA:
        findings.append(
            _finding(
                "invalid_bundle",
                "critical",
                "Debug bundle schema is not recognized",
                "The support file does not match the current account debug bundle format.",
                "Export a fresh debug bundle from this GW2Radar build before troubleshooting.",
                ["schema_version"],
            )
        )

    key_status = _as_dict(bundle.get("key_status"))
    permission_summary = _as_dict(bundle.get("permission_summary"))
    sync_summary = _as_dict(bundle.get("sync_summary"))
    diagnostic_summary = _as_dict(bundle.get("diagnostic_summary"))
    snapshot_summary = _as_dict(bundle.get("snapshot_summary"))
    client_state = _as_dict(bundle.get("client_state"))
    checks = _checks_by_id(diagnostic_summary.get("checks"))

    if key_status.get("is_configured") is not True:
        findings.append(
            _finding(
                "needs_key",
                "critical",
                "No GW2 API key is connected",
                "GW2Radar has no stored key to inspect permissions or sync account state.",
                "Paste a read-only GW2 API key, save it, then run Sync now.",
                ["key_status.is_configured", "diagnostic_summary.checks.api_key_stored"],
            )
        )

    missing_required = _as_list(permission_summary.get("missing_required_permissions"))
    if missing_required:
        findings.append(
            _finding(
                "needs_permissions",
                "critical",
                "Required GW2 API permissions are missing",
                f"The connected key is missing: {', '.join(str(item) for item in missing_required)}.",
                "Create or update the key with the required scopes, save it again, then resync.",
                ["permission_summary.missing_required_permissions", "diagnostic_summary.checks.permissions_ready"],
            )
        )

    if _sync_is_delayed(sync_summary):
        findings.append(
            _finding(
                "sync_delayed",
                "warning",
                "Account sync is delayed or waiting for retry",
                "The sync queue shows delayed, retry, or needs-review work.",
                "Wait for the retry window or run the development drain-one action after queueing a sync.",
                ["sync_summary.status", "sync_summary.counts", "sync_summary.endpoint_progress"],
            )
        )

    if _check_needs_action(checks, "sync_job_visible"):
        findings.append(
            _finding(
                "needs_sync",
                "warning",
                "No account sync job is visible",
                "The account connection is saved, but no sync job has reached queue history yet.",
                "Click Sync now, then run the diagnostic again.",
                ["diagnostic_summary.checks.sync_job_visible"],
            )
        )

    if _check_needs_action(checks, "private_snapshot_written"):
        findings.append(
            _finding(
                "needs_drain",
                "warning",
                "Private account snapshot has not been written",
                "The sync job has not produced private player-state records yet.",
                "Use drain-one in development, or wait for the worker to finish the queued sync.",
                ["diagnostic_summary.checks.private_snapshot_written", "snapshot_summary.private_player_state_count"],
            )
        )

    if _check_needs_action(checks, "synced_character_snapshot"):
        findings.append(
            _finding(
                "needs_character_sync",
                "warning",
                "Synced character snapshot is unavailable",
                "Build Fit can only see manual sample snapshots, not account character gear.",
                "Resync the account with character permission enabled and load character snapshots again.",
                ["diagnostic_summary.checks.synced_character_snapshot", "snapshot_summary.synced_character_snapshot_count"],
            )
        )

    if _check_needs_action(checks, "build_fit_bridge_ready") and _has_synced_snapshot(snapshot_summary):
        findings.append(
            _finding(
                "needs_build_snapshot_load",
                "warning",
                "Build Fit has not loaded synced gear",
                "The account snapshot exists, but Build Fit has not converted it into account gear yet.",
                "Open Build Fit and load the synced character snapshot before running the fit check.",
                ["diagnostic_summary.checks.build_fit_bridge_ready", "snapshot_summary.synced_gear_count"],
            )
        )

    if _server_ready(diagnostic_summary, checks) and _frontend_flow_incomplete(client_state):
        findings.append(
            _finding(
                "frontend_flow_incomplete",
                "info",
                "Backend is ready; player flow is not complete",
                "The account connection looks healthy, but the player has not completed the Build Fit flow in the UI.",
                "Open Build Fit, select or import a build, load account gear, then generate the expected result.",
                ["diagnostic_summary.summary_status", "client_state.active_view", "client_state.active_build_id_present"],
            )
        )

    return _report(bundle_schema, _overall_status(findings), findings)


def render_account_debug_bundle_review_markdown(report: SupportReviewReport) -> str:
    lines = [
        "# Account Debug Bundle Support Review",
        "",
        f"- Status: {report.overall_status}",
        f"- Summary: {report.summary}",
        f"- Bundle schema: {report.bundle_schema_version or 'unknown'}",
        "",
        "## Findings",
    ]
    if not report.findings:
        lines.append("- No action needed. The support bundle is ready for normal player flow verification.")
    for finding in report.findings:
        lines.extend(
            [
                f"- [{finding.severity}] {finding.title}",
                f"  - Player message: {finding.player_message}",
                f"  - Recommended action: {finding.recommended_action}",
                f"  - Evidence: {', '.join(finding.evidence_refs) if finding.evidence_refs else 'none'}",
            ]
        )
    lines.extend(["", "## Privacy Boundary"])
    lines.extend(f"- {item}" for item in report.redaction_boundary)
    return "\n".join(lines) + "\n"


def _report(bundle_schema: str | None, overall_status: str, findings: list[SupportReviewFinding]) -> SupportReviewReport:
    return SupportReviewReport(
        bundle_schema_version=bundle_schema,
        overall_status=overall_status,
        summary=_summary(overall_status),
        findings=findings,
    )


def _summary(overall_status: str) -> str:
    summaries = {
        "ready": "The account support bundle shows no blocking issue.",
        "privacy_boundary_violation": "The bundle must be discarded because it appears to include sensitive fields.",
        "invalid_bundle": "The support file is not a current GW2Radar account debug bundle.",
        "needs_key": "The player needs to save a GW2 API key before sync can work.",
        "needs_permissions": "The stored key lacks permissions needed for account-aware results.",
        "sync_delayed": "The sync queue is delayed or waiting for retry.",
        "needs_sync": "The player needs to queue an account sync.",
        "needs_drain": "The queued sync has not written private player-state records yet.",
        "needs_character_sync": "The player needs synced character snapshots before Build Fit can use account gear.",
        "needs_build_snapshot_load": "Build Fit needs to load the synced character snapshot.",
        "frontend_flow_incomplete": "The backend is ready, but the UI flow has not reached the expected result step.",
    }
    return summaries.get(overall_status, "The support review needs manual inspection.")


def _overall_status(findings: list[SupportReviewFinding]) -> str:
    if not findings:
        return "ready"
    priority = [
        "privacy_boundary_violation",
        "invalid_bundle",
        "needs_key",
        "needs_permissions",
        "sync_delayed",
        "needs_sync",
        "needs_drain",
        "needs_character_sync",
        "needs_build_snapshot_load",
        "frontend_flow_incomplete",
    ]
    finding_ids = {finding.finding_id for finding in findings}
    for status in priority:
        if status in finding_ids:
            return status
    return "manual_review"


def _finding(
    finding_id: str,
    severity: str,
    title: str,
    player_message: str,
    recommended_action: str,
    evidence_refs: list[str],
) -> SupportReviewFinding:
    return SupportReviewFinding(
        finding_id=finding_id,
        severity=severity,
        title=title,
        player_message=player_message,
        recommended_action=recommended_action,
        evidence_refs=evidence_refs,
    )


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


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _checks_by_id(value: Any) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    if not isinstance(value, list):
        return checks
    for item in value:
        if isinstance(item, dict) and isinstance(item.get("check_id"), str):
            checks[item["check_id"]] = item
    return checks


def _check_needs_action(checks: dict[str, dict[str, Any]], check_id: str) -> bool:
    status = checks.get(check_id, {}).get("status")
    return status in {"warn", "fail"}


def _sync_is_delayed(sync_summary: dict[str, Any]) -> bool:
    counts = _as_dict(sync_summary.get("counts"))
    if int(counts.get("retry_scheduled") or 0) > 0:
        return True
    endpoint_progress = _as_list(sync_summary.get("endpoint_progress"))
    return any(
        isinstance(item, dict) and item.get("status") in {"delayed", "needs_review", "retry_scheduled"}
        for item in endpoint_progress
    )


def _has_synced_snapshot(snapshot_summary: dict[str, Any]) -> bool:
    return int(snapshot_summary.get("synced_character_snapshot_count") or 0) > 0


def _server_ready(diagnostic_summary: dict[str, Any], checks: dict[str, dict[str, Any]]) -> bool:
    if diagnostic_summary.get("summary_status") != "ready":
        return False
    return all(check.get("status") == "pass" for check in checks.values())


def _frontend_flow_incomplete(client_state: dict[str, Any]) -> bool:
    return client_state.get("active_view") != "build" or client_state.get("active_build_id_present") is not True
