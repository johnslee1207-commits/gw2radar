from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationStep:
    step_id: str
    description: str
    command: tuple[str, ...]


@dataclass(frozen=True)
class ValidationProfile:
    profile_id: str
    description: str
    steps: tuple[ValidationStep, ...]


@dataclass(frozen=True)
class ValidationStageGate:
    gate_id: str
    description: str
    profile_ids: tuple[str, ...]


PYTHON = sys.executable


VALIDATION_PROFILES: dict[str, ValidationProfile] = {
    "fast": ValidationProfile(
        profile_id="fast",
        description="High-signal developer loop for changed delivery, report, and player workflow contracts.",
        steps=(
            ValidationStep(
                "delivery_lifecycle",
                "Shared delivery lifecycle unit contract.",
                (PYTHON, "-m", "pytest", "tests\\test_delivery_lifecycle.py", "-q"),
            ),
            ValidationStep(
                "productized_report",
                "Productized report artifact and packet regression.",
                (PYTHON, "-m", "pytest", "tests\\test_report_productization.py", "-q"),
            ),
            ValidationStep(
                "player_use_path_audit",
                "Executable player use-path and semantic maturity audit.",
                (PYTHON, "harness\\run_player_use_path_audit.py"),
            ),
            ValidationStep(
                "spec_registry",
                "Spec registry and backlog index freshness check.",
                (PYTHON, "harness\\run_spec_registry.py", "--check"),
            ),
            ValidationStep(
                "spec_reconciliation",
                "Partial spec reconciliation freshness check.",
                (PYTHON, "harness\\run_spec_reconciliation.py", "--check"),
            ),
            ValidationStep(
                "closure_readiness",
                "MVP closure readiness freshness check.",
                (PYTHON, "harness\\run_closure_readiness.py", "--check"),
            ),
            ValidationStep(
                "post_mvp_roadmap",
                "Post-MVP production roadmap freshness check.",
                (PYTHON, "harness\\run_post_mvp_roadmap.py", "--check"),
            ),
            ValidationStep(
                "operational_hardening_readiness",
                "Operational hardening readiness freshness check.",
                (PYTHON, "harness\\run_operational_hardening_readiness.py", "--check"),
            ),
            ValidationStep(
                "operator_release_packet",
                "Operator release packet readiness freshness check.",
                (PYTHON, "harness\\run_operator_release_packet.py", "--check"),
            ),
            ValidationStep(
                "final_closeout_dashboard",
                "Final closeout dashboard freshness check.",
                (PYTHON, "harness\\run_final_closeout_dashboard.py", "--check"),
            ),
        ),
    ),
    "smoke": ValidationProfile(
        profile_id="smoke",
        description="Harness smoke checks for core MVP, player UI, and account connection contracts.",
        steps=(
            ValidationStep(
                "mvp_smoke",
                "MVP mock legendary goal loop.",
                (PYTHON, "harness\\run_smoke.py"),
            ),
            ValidationStep(
                "player_ui_e2e",
                "Player UI E2E smoke without browser automation.",
                (PYTHON, "harness\\run_player_ui_e2e_smoke.py"),
            ),
            ValidationStep(
                "account_connection",
                "Account connection diagnostic with fake GW2 API gateway.",
                (PYTHON, "harness\\run_account_connection_diagnostic.py"),
            ),
        ),
    ),
    "full": ValidationProfile(
        profile_id="full",
        description="Complete repository regression suite.",
        steps=(
            ValidationStep(
                "pytest_full",
                "Full pytest regression.",
                (PYTHON, "-m", "pytest", "-q"),
            ),
        ),
    ),
}


VALIDATION_STAGE_GATES: dict[str, ValidationStageGate] = {
    "stage": ValidationStageGate(
        gate_id="stage",
        description="Default stage gate for ordinary development slices; runs fast and smoke checks only.",
        profile_ids=("fast", "smoke"),
    ),
    "release": ValidationStageGate(
        gate_id="release",
        description="Milestone or release gate; runs fast, smoke, and full regression.",
        profile_ids=("fast", "smoke", "full"),
    ),
}


def get_validation_profile(profile_id: str) -> ValidationProfile:
    try:
        return VALIDATION_PROFILES[profile_id]
    except KeyError as exc:
        raise ValueError(f"Unknown validation profile: {profile_id}") from exc


def list_validation_profiles() -> list[ValidationProfile]:
    return [VALIDATION_PROFILES[key] for key in sorted(VALIDATION_PROFILES)]


def get_validation_stage_gate(gate_id: str) -> ValidationStageGate:
    try:
        return VALIDATION_STAGE_GATES[gate_id]
    except KeyError as exc:
        raise ValueError(f"Unknown validation stage gate: {gate_id}") from exc


def list_validation_stage_gates() -> list[ValidationStageGate]:
    return [VALIDATION_STAGE_GATES[key] for key in sorted(VALIDATION_STAGE_GATES)]
