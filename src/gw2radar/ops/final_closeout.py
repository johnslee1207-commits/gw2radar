from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from gw2radar.ops.operator_release_packet import build_operator_release_packet_summary
from gw2radar.ops.release_readiness import ROOT, build_operational_hardening_readiness


ANALYSIS_DIR = ROOT / "docs" / "analysis"
CLOSURE_JSON = ANALYSIS_DIR / "MVP_CLOSURE_READINESS.json"
ROADMAP_JSON = ANALYSIS_DIR / "POST_MVP_PRODUCTION_ROADMAP.json"
SPEC_REGISTRY_JSON = ANALYSIS_DIR / "SPEC_REGISTRY_BACKLOG.json"
OPERATIONAL_JSON = ANALYSIS_DIR / "OPERATIONAL_HARDENING_READINESS.json"
OPERATOR_PACKET_JSON = ANALYSIS_DIR / "OPERATOR_RELEASE_PACKET_READINESS.json"


class FinalCloseoutArea(BaseModel):
    area_id: str
    status: str
    evidence: str
    stop_line: bool = False


class StopLineReview(BaseModel):
    schema_version: str = "gw2radar.stop_line_review.v1"
    decision: str
    no_more_horizontal_copy: bool
    continue_mode: str
    stop_conditions: list[str]
    allowed_next_work: list[str]
    deferred_tracks: list[str]
    rationale: str


class FinalCloseoutDashboard(BaseModel):
    schema_version: str = "gw2radar.final_closeout_dashboard.v1"
    status: str
    closeout_score: float
    area_count: int
    stop_line_count: int
    areas: list[FinalCloseoutArea]
    completed_tracks: list[str]
    deferred_tracks: list[str]
    trial_entrypoints: list[str]
    defect_intake_channels: list[str]
    required_commands: list[str]
    evidence_files: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    stop_line_review: StopLineReview
    next_priority: str


def build_stop_line_review() -> StopLineReview:
    readiness = build_operational_hardening_readiness()
    return StopLineReview(
        decision="stop_new_phase_expansion",
        no_more_horizontal_copy=True,
        continue_mode="real_user_trial_and_defect_fix",
        stop_conditions=[
            "A-F post-MVP phases are implemented at MVP or foundation level",
            "operational hardening readiness is ready",
            "operator release packet is ready",
            "stage and release gates are declared as required before handoff",
        ],
        allowed_next_work=[
            "fix user-reported defects",
            "improve diagnostics for failed real API key sessions",
            "run optional live GW2 API smoke with explicit operator credentials",
            "polish UI flows only when a trial user reports friction",
            "add reviewed KB content only when a concrete content pack is selected",
        ],
        deferred_tracks=readiness.deferred_tracks,
        rationale=(
            "The current bottleneck is no longer missing lifecycle scaffolding. Further horizontal phase copying should stop; "
            "the project should shift to real player trial feedback, defect triage, and targeted hardening."
        ),
    )


def build_final_closeout_dashboard() -> FinalCloseoutDashboard:
    closure = _load_json(CLOSURE_JSON)
    roadmap = _load_json(ROADMAP_JSON)
    registry = _load_json(SPEC_REGISTRY_JSON)
    readiness = build_operational_hardening_readiness()
    operator_packet = build_operator_release_packet_summary()
    stop_line = build_stop_line_review()
    phase_count = int(roadmap.get("phase_count", 0) or 0)
    implemented_phase_count = _implemented_phase_count(roadmap.get("phases", []))
    areas = [
        FinalCloseoutArea(
            area_id="mvp_closure",
            status="ready" if closure.get("status") == "ready_to_close_mvp_stage" else "blocked",
            evidence=f"closure_status={closure.get('status')}",
            stop_line=closure.get("status") != "ready_to_close_mvp_stage",
        ),
        FinalCloseoutArea(
            area_id="post_mvp_phases",
            status="ready" if implemented_phase_count == phase_count and phase_count >= 6 else "blocked",
            evidence=f"implemented_phase_count={implemented_phase_count}/{phase_count}",
            stop_line=not (implemented_phase_count == phase_count and phase_count >= 6),
        ),
        FinalCloseoutArea(
            area_id="operational_hardening",
            status=readiness.status,
            evidence=f"readiness_score={readiness.readiness_score}; blockers={readiness.blocker_count}",
            stop_line=readiness.status != "ready" or readiness.blocker_count != 0,
        ),
        FinalCloseoutArea(
            area_id="operator_release_packet",
            status=operator_packet.status,
            evidence=f"readiness_score={operator_packet.readiness_score}; blockers={operator_packet.blocker_count}",
            stop_line=operator_packet.status != "ready" or operator_packet.blocker_count != 0,
        ),
        FinalCloseoutArea(
            area_id="spec_and_semantic_registry",
            status="ready" if int(registry.get("spec_count", 0) or 0) >= 50 else "blocked",
            evidence=f"spec_count={registry.get('spec_count')}",
            stop_line=int(registry.get("spec_count", 0) or 0) < 50,
        ),
        FinalCloseoutArea(
            area_id="work_mode_stop_line",
            status="ready" if stop_line.no_more_horizontal_copy else "blocked",
            evidence=stop_line.decision,
            stop_line=not stop_line.no_more_horizontal_copy,
        ),
    ]
    stop_line_count = sum(1 for area in areas if area.stop_line)
    closeout_score = round(((len(areas) - stop_line_count) / len(areas)) * 100, 1)
    return FinalCloseoutDashboard(
        status="ready_for_user_trial" if stop_line_count == 0 else "blocked",
        closeout_score=closeout_score,
        area_count=len(areas),
        stop_line_count=stop_line_count,
        areas=areas,
        completed_tracks=[
            "MVP closure readiness",
            "Phase A Trust & Credential MVP",
            "Phase B Report Product Close Loop",
            "Phase C Progression Decision Engine v1",
            "Phase D 7-Day Planning / DAG",
            "Phase E Production SaaS Foundation",
            "Phase F Growth / Retention",
            "Operational Hardening Readiness",
            "Operator Release Packet Handoff",
        ],
        deferred_tracks=readiness.deferred_tracks,
        trial_entrypoints=[
            "/player",
            "/support",
            "/api/v1/ops/release-readiness",
            "/api/v1/ops/release-packet",
            "/api/v1/account/connection/diagnostic",
        ],
        defect_intake_channels=[
            "privacy-safe account debug bundle review",
            "support review UI audit",
            "operator release packet verification",
            "GitHub issue or commit-linked defect note",
        ],
        required_commands=operator_packet.required_commands,
        evidence_files=[
            "docs/analysis/MVP_CLOSURE_READINESS.json",
            "docs/analysis/POST_MVP_PRODUCTION_ROADMAP.json",
            "docs/analysis/OPERATIONAL_HARDENING_READINESS.json",
            "docs/analysis/OPERATOR_RELEASE_PACKET_READINESS.json",
            "docs/analysis/SPEC_REGISTRY_BACKLOG.json",
            "docs/ui/PLAYER_USE_PATH_COMPLETENESS_AUDIT.md",
        ],
        safety_boundaries=readiness.safety_boundaries,
        stop_line_review=stop_line,
        next_priority=(
            "Stop broad phase expansion; start real player trial, defect triage, optional live API smoke, and targeted UI friction fixes."
        ),
    )


def render_final_closeout_dashboard_markdown(dashboard: FinalCloseoutDashboard) -> str:
    lines = [
        "# Final Closeout Dashboard",
        "",
        f"- Schema: {dashboard.schema_version}",
        f"- Status: {dashboard.status}",
        f"- Closeout score: {dashboard.closeout_score}",
        f"- Stop-line count: {dashboard.stop_line_count}",
        "",
        "## Areas",
        "",
        "| Area | Status | Stop Line | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for area in dashboard.areas:
        lines.append(f"| {area.area_id} | {area.status} | {str(area.stop_line).lower()} | {area.evidence} |")
    lines.extend(["", "## Stop-Line Review", ""])
    lines.append(f"- Decision: {dashboard.stop_line_review.decision}")
    lines.append(f"- Continue mode: {dashboard.stop_line_review.continue_mode}")
    lines.append(f"- No more horizontal copy: {str(dashboard.stop_line_review.no_more_horizontal_copy).lower()}")
    lines.extend(["", "## Allowed Next Work", ""])
    for item in dashboard.stop_line_review.allowed_next_work:
        lines.append(f"- {item}")
    lines.extend(["", "## Trial Entrypoints", ""])
    for endpoint in dashboard.trial_entrypoints:
        lines.append(f"- `{endpoint}`")
    lines.extend(["", "## Deferred Tracks", ""])
    for track in dashboard.deferred_tracks:
        lines.append(f"- {track}")
    lines.extend(["", "## Safety Boundaries", ""])
    for boundary in dashboard.safety_boundaries:
        lines.append(f"- {boundary}")
    lines.extend(["", "## Next Priority", "", dashboard.next_priority, ""])
    return "\n".join(lines)


def render_final_closeout_dashboard_csv(dashboard: FinalCloseoutDashboard) -> str:
    rows = ["area_id,status,stop_line,evidence"]
    for area in dashboard.areas:
        rows.append(f"{area.area_id},{area.status},{str(area.stop_line).lower()},{area.evidence}")
    return "\n".join(rows) + "\n"


def render_stop_line_review_markdown(review: StopLineReview) -> str:
    lines = [
        "# Stop-Line Review",
        "",
        f"- Schema: {review.schema_version}",
        f"- Decision: {review.decision}",
        f"- Continue mode: {review.continue_mode}",
        f"- No more horizontal copy: {str(review.no_more_horizontal_copy).lower()}",
        "",
        "## Stop Conditions",
        "",
    ]
    for item in review.stop_conditions:
        lines.append(f"- {item}")
    lines.extend(["", "## Allowed Next Work", ""])
    for item in review.allowed_next_work:
        lines.append(f"- {item}")
    lines.extend(["", "## Deferred Tracks", ""])
    for item in review.deferred_tracks:
        lines.append(f"- {item}")
    lines.extend(["", "## Rationale", "", review.rationale, ""])
    return "\n".join(lines)


def render_stop_line_review_csv(review: StopLineReview) -> str:
    rows = ["field,value"]
    rows.append(f"decision,{review.decision}")
    rows.append(f"continue_mode,{review.continue_mode}")
    rows.append(f"no_more_horizontal_copy,{str(review.no_more_horizontal_copy).lower()}")
    return "\n".join(rows) + "\n"


def _implemented_phase_count(phases: object) -> int:
    if not isinstance(phases, list):
        return 0
    return sum(
        1
        for phase in phases
        if isinstance(phase, dict) and phase.get("status") in {"implemented_mvp", "implemented_foundation"}
    )


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing final closeout input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
