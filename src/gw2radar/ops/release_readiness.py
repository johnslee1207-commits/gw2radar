from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = ROOT / "docs" / "analysis"
PLAYER_AUDIT_MD = ROOT / "docs" / "ui" / "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md"
CLOSURE_JSON = ANALYSIS_DIR / "MVP_CLOSURE_READINESS.json"
ROADMAP_JSON = ANALYSIS_DIR / "POST_MVP_PRODUCTION_ROADMAP.json"
SPEC_REGISTRY_JSON = ANALYSIS_DIR / "SPEC_REGISTRY_BACKLOG.json"
SPEC_RECONCILIATION_JSON = ANALYSIS_DIR / "PARTIAL_SPEC_RECONCILIATION.json"


class OperationalGate(BaseModel):
    gate_id: str
    status: str
    evidence: str
    blocker: bool = False


class OperationalHardeningReadiness(BaseModel):
    schema_version: str = "gw2radar.operational_hardening_readiness.v1"
    status: str
    readiness_score: float
    gate_count: int
    blocker_count: int
    gates: list[OperationalGate]
    required_commands: list[str]
    deferred_tracks: list[str]
    safety_boundaries: list[str]
    next_priority: str
    evidence_files: list[str] = Field(default_factory=list)


def build_operational_hardening_readiness() -> OperationalHardeningReadiness:
    closure = _load_json(CLOSURE_JSON)
    roadmap = _load_json(ROADMAP_JSON)
    registry = _load_json(SPEC_REGISTRY_JSON)
    reconciliation = _load_json(SPEC_RECONCILIATION_JSON)
    player_failed_checks = _player_failed_checks()
    phases = roadmap.get("phases", [])
    implemented_phase_count = _implemented_phase_count(phases)
    phase_count = int(roadmap.get("phase_count", 0) or 0)

    gates = [
        OperationalGate(
            gate_id="mvp_closure_ready",
            status="pass" if closure.get("status") == "ready_to_close_mvp_stage" else "blocked",
            evidence=f"closure_status={closure.get('status')}",
            blocker=closure.get("status") != "ready_to_close_mvp_stage",
        ),
        OperationalGate(
            gate_id="post_mvp_phases_a_f_implemented",
            status="pass" if phase_count >= 6 and implemented_phase_count == phase_count else "blocked",
            evidence=f"implemented_phase_count={implemented_phase_count}/{phase_count}",
            blocker=not (phase_count >= 6 and implemented_phase_count == phase_count),
        ),
        OperationalGate(
            gate_id="player_use_path_maturity",
            status="pass" if player_failed_checks == 0 else "blocked",
            evidence=f"failed_checks={player_failed_checks}",
            blocker=player_failed_checks != 0,
        ),
        OperationalGate(
            gate_id="spec_reconciliation_current",
            status="pass" if reconciliation.get("needs_review_count") == 0 else "blocked",
            evidence=f"needs_review_count={reconciliation.get('needs_review_count')}",
            blocker=reconciliation.get("needs_review_count") != 0,
        ),
        OperationalGate(
            gate_id="spec_registry_depth",
            status="pass" if int(registry.get("spec_count", 0) or 0) >= 50 else "blocked",
            evidence=f"spec_count={registry.get('spec_count')}",
            blocker=int(registry.get("spec_count", 0) or 0) < 50,
        ),
        OperationalGate(
            gate_id="release_command_declared",
            status="pass" if "python harness/run_stage_gate.py release" in closure.get("required_closeout_commands", []) else "blocked",
            evidence="release gate command is listed in closure readiness",
            blocker="python harness/run_stage_gate.py release" not in closure.get("required_closeout_commands", []),
        ),
        OperationalGate(
            gate_id="gitnexus_command_declared",
            status="pass" if "npx gitnexus analyze" in closure.get("required_closeout_commands", []) else "blocked",
            evidence="GitNexus analysis command is listed in closure readiness",
            blocker="npx gitnexus analyze" not in closure.get("required_closeout_commands", []),
        ),
    ]
    blocker_count = sum(1 for gate in gates if gate.blocker)
    readiness_score = round(((len(gates) - blocker_count) / len(gates)) * 100, 1)
    return OperationalHardeningReadiness(
        status="ready" if blocker_count == 0 else "blocked",
        readiness_score=readiness_score,
        gate_count=len(gates),
        blocker_count=blocker_count,
        gates=gates,
        required_commands=[
            "python harness/run_stage_gate.py stage",
            "python harness/run_stage_gate.py release",
            "npx gitnexus analyze",
        ],
        deferred_tracks=[
            "real billing provider integration",
            "team workspace credential sharing",
            "full SaaS launch",
            "autonomous agents",
        ],
        safety_boundaries=[
            "local-first mode remains the default",
            "no raw secret or private payload export",
            "no automated gameplay action",
            "no automated trading instruction",
            "no guaranteed outcome claim",
        ],
        next_priority=(
            "Run release gate and GitNexus analysis before external packaging; keep provider integrations as explicit later tracks."
        ),
        evidence_files=[
            "docs/analysis/MVP_CLOSURE_READINESS.json",
            "docs/analysis/POST_MVP_PRODUCTION_ROADMAP.json",
            "docs/analysis/SPEC_REGISTRY_BACKLOG.json",
            "docs/analysis/PARTIAL_SPEC_RECONCILIATION.json",
            "docs/ui/PLAYER_USE_PATH_COMPLETENESS_AUDIT.md",
        ],
    )


def render_operational_hardening_markdown(readiness: OperationalHardeningReadiness) -> str:
    lines = [
        "# Operational Hardening Readiness",
        "",
        f"- Schema: {readiness.schema_version}",
        f"- Status: {readiness.status}",
        f"- Readiness score: {readiness.readiness_score}",
        f"- Gate count: {readiness.gate_count}",
        f"- Blocker count: {readiness.blocker_count}",
        "",
        "## Gates",
        "",
        "| Gate | Status | Blocker | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for gate in readiness.gates:
        lines.append(f"| {gate.gate_id} | {gate.status} | {str(gate.blocker).lower()} | {gate.evidence} |")
    lines.extend(["", "## Required Commands", ""])
    for command in readiness.required_commands:
        lines.append(f"- `{command}`")
    lines.extend(["", "## Deferred Tracks", ""])
    for track in readiness.deferred_tracks:
        lines.append(f"- {track}")
    lines.extend(["", "## Safety Boundaries", ""])
    for boundary in readiness.safety_boundaries:
        lines.append(f"- {boundary}")
    lines.extend(["", "## Next Priority", "", readiness.next_priority, ""])
    return "\n".join(lines)


def render_operational_hardening_csv(readiness: OperationalHardeningReadiness) -> str:
    rows = ["gate_id,status,blocker,evidence"]
    for gate in readiness.gates:
        rows.append(f"{gate.gate_id},{gate.status},{str(gate.blocker).lower()},{gate.evidence}")
    return "\n".join(rows) + "\n"


def _implemented_phase_count(phases: object) -> int:
    if not isinstance(phases, list):
        return 0
    implemented_statuses = {"implemented_mvp", "implemented_foundation"}
    return sum(1 for phase in phases if isinstance(phase, dict) and phase.get("status") in implemented_statuses)


def _load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"Missing operational readiness input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _player_failed_checks() -> int:
    if not PLAYER_AUDIT_MD.exists():
        return 999
    for line in PLAYER_AUDIT_MD.read_text(encoding="utf-8").splitlines():
        if line.startswith("- Failed checks:"):
            return int(line.split(":", 1)[1].strip())
    return 999
