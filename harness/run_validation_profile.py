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
from harness.validation_profiles import get_validation_profile, list_validation_profiles


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run staged GW2Radar validation profiles.")
    parser.add_argument(
        "profile",
        nargs="?",
        default="fast",
        choices=[profile.profile_id for profile in list_validation_profiles()],
        help="Validation profile to run.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available validation profiles and exit.",
    )
    args = parser.parse_args(argv)
    if args.list:
        for profile in list_validation_profiles():
            print(f"{profile.profile_id}: {profile.description}")
            for step in profile.steps:
                print(f"  - {step.step_id}: {' '.join(step.command)}")
        return 0

    profile = get_validation_profile(args.profile)
    print(f"RUN: validation profile {profile.profile_id}")
    print(profile.description)
    started = time.perf_counter()
    for step in profile.steps:
        print(f"\nSTEP {step.step_id}: {step.description}")
        print("CMD: " + " ".join(step.command))
        step_started = time.perf_counter()
        completed = subprocess.run(step.command)
        elapsed = time.perf_counter() - step_started
        if completed.returncode != 0:
            print(f"FAIL: {step.step_id} exited {completed.returncode} after {elapsed:.1f}s")
            return completed.returncode
        print(f"PASS: {step.step_id} in {elapsed:.1f}s")
    total = time.perf_counter() - started
    print(f"\nPASS: validation profile {profile.profile_id} completed in {total:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
