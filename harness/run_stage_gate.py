from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from harness.validation_profiles import get_validation_profile, get_validation_stage_gate, list_validation_stage_gates


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GW2Radar stage validation gates.")
    parser.add_argument(
        "gate",
        nargs="?",
        default="stage",
        choices=[gate.gate_id for gate in list_validation_stage_gates()],
        help="Stage gate to run.",
    )
    parser.add_argument("--list", action="store_true", help="List available stage gates and exit.")
    args = parser.parse_args(argv)
    if args.list:
        for gate in list_validation_stage_gates():
            print(f"{gate.gate_id}: {gate.description}")
            print(f"  profiles: {', '.join(gate.profile_ids)}")
        return 0

    gate = get_validation_stage_gate(args.gate)
    print(f"RUN: validation stage gate {gate.gate_id}")
    print(gate.description)
    started = time.perf_counter()
    for profile_id in gate.profile_ids:
        profile = get_validation_profile(profile_id)
        print(f"\nPROFILE {profile.profile_id}: {profile.description}")
        for step in profile.steps:
            print(f"STEP {step.step_id}: {step.description}")
            print("CMD: " + " ".join(step.command))
            step_started = time.perf_counter()
            completed = subprocess.run(step.command)
            elapsed = time.perf_counter() - step_started
            if completed.returncode != 0:
                print(f"FAIL: {profile.profile_id}/{step.step_id} exited {completed.returncode} after {elapsed:.1f}s")
                return completed.returncode
            print(f"PASS: {profile.profile_id}/{step.step_id} in {elapsed:.1f}s")
    total = time.perf_counter() - started
    print(f"\nPASS: validation stage gate {gate.gate_id} completed in {total:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

