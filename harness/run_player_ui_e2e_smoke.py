"""Player UI E2E smoke harness.

This harness verifies the primary player flow without requiring a browser:
load demo graph, import a build, import and enable reviewed KB upgrade evidence,
re-run Build Fit, then generate and retrieve a paid report artifact.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api import state  # noqa: E402
from gw2radar.api.main import app  # noqa: E402
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products  # noqa: E402
from gw2radar.db import session as db_session  # noqa: E402
from gw2radar.db.init_db import init_db  # noqa: E402
from gw2radar.db.session import close_database, configure_database  # noqa: E402


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"player-ui-e2e-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    try:
        configure_database(f"sqlite:///{temp_dir / 'player-ui.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)

        _check_page_shell(client, failures)
        _check_response(client.post("/mock/load"), "load demo graph", failures)

        imported = _check_response(
            client.post("/api/v1/builds/import", json=_sample_build_import()),
            "import sample build",
            failures,
        )
        build_id = _get(imported, "data", "build", "build_id")
        if not build_id:
            failures.append("imported build did not return build_id")
            build_id = "missing-build-id"

        _check_response(client.get("/api/v1/kb/rule-packs/build_upgrade_effects"), "preview upgrade rule pack", failures)
        _check_response(
            client.post("/api/v1/kb/rule-packs/build_upgrade_effects/import", json={"confirmed": True}),
            "import disabled upgrade rules",
            failures,
        )
        listed_rules = _check_response(
            client.get("/api/v1/kb/rules?domain=build&name_contains=Build%20upgrade"),
            "list persisted upgrade rules",
            failures,
        )
        rules = _get(listed_rules, "data", "rules") or []
        power_rule = next((rule for rule in rules if rule.get("name") == "Build upgrade power damage family"), None)
        if power_rule is None and rules:
            power_rule = rules[0]
        if power_rule is None:
            failures.append("no build upgrade rule was available to enable")
        else:
            _check_response(
                client.post(
                    f"/api/v1/kb/rules/{power_rule['rule_id']}/enable",
                    json={"confirmed_reviewed": True, "reviewer": "player_ui_e2e_smoke"},
                ),
                "enable reviewed upgrade rule",
                failures,
            )

        fit = _check_response(
            client.post(
                "/api/v1/builds/fit",
                json={"build_id": build_id, "account_gear": _matching_account_gear()},
            ),
            "calculate fit score",
            failures,
        )
        fit_score = _get(fit, "data", "fit", "score") or {}
        upgrade_effects = _get(fit, "data", "fit", "upgrade_effects") or []
        if fit_score.get("playable_now") is not True:
            failures.append("fit score did not mark matching account gear as playable_now")
        if not upgrade_effects:
            failures.append("fit score did not return upgrade effects")
        else:
            first_effect = upgrade_effects[0]
            if first_effect.get("evidence_source") != "reviewed_kb_rule":
                failures.append("upgrade effect did not use reviewed KB rule evidence")
            if not first_effect.get("evidence_refs"):
                failures.append("upgrade effect did not include evidence_refs")

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "build_fit_report")

        report = _check_response(
            client.post(
                "/api/v1/builds/report",
                json={
                    "build_id": build_id,
                    "account_gear": _matching_account_gear(),
                    "format": "markdown",
                },
            ),
            "generate build fit report",
            failures,
        )
        job = _get(report, "data", "job") or {}
        if job.get("status") != "succeeded":
            failures.append("build fit report job did not succeed")
        artifact_path = job.get("artifact_path")
        if not artifact_path:
            failures.append("build fit report did not return artifact_path")
        else:
            artifact_name = Path(artifact_path).name
            artifact = client.get(f"/api/v1/reports/artifacts/{artifact_name}")
            if artifact.status_code != 200:
                failures.append(f"report artifact retrieval returned HTTP {artifact.status_code}")
            elif "Build Fit Report" not in artifact.text or "Upgrade Effects" not in artifact.text:
                failures.append("report artifact did not include Build Fit and Upgrade Effects sections")

    except Exception as exc:  # pragma: no cover - harness defensive reporting
        failures.append(f"unexpected harness error: {exc}")
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(ROOT / "outputs", ignore_errors=True)

    if failures:
        print("FAIL: GW2Radar Player UI E2E smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: GW2Radar Player UI E2E smoke succeeded")
    return 0


def _check_page_shell(client: TestClient, failures: list[str]) -> None:
    response = client.get("/player")
    if response.status_code != 200:
        failures.append(f"player page returned HTTP {response.status_code}")
        return
    for marker in ["GW2Radar", "Build Fit Advisor", "Upgrade evidence rules"]:
        if marker not in response.text:
            failures.append(f"player page is missing marker: {marker}")


def _check_response(response, label: str, failures: list[str]) -> dict:
    if response.status_code != 200:
        failures.append(f"{label} returned HTTP {response.status_code}: {response.text[:240]}")
        return {}
    try:
        return response.json()
    except ValueError:
        failures.append(f"{label} did not return JSON")
        return {}


def _get(data: dict, *path: str):
    cursor = data
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def _sample_build_import() -> dict:
    return {
        "name": "Power Quickness Herald",
        "source": {
            "name": "manual_player_ui_smoke",
            "url": "https://example.invalid/build/herald",
            "attribution": "Smoke test structured build data.",
        },
        "profession": "Revenant",
        "specialization": "Herald",
        "role": "quickness_dps",
        "game_mode": "strike",
        "patch_version": "2026-06",
        "patch_freshness_days": 20,
        "difficulty": "medium",
        "requirements": [
            {
                "slot": "chest",
                "item_name": "Ascended Chest",
                "stat_combo": "Berserker",
                "required": True,
                "estimated_cost_gold": 25,
            },
            {
                "slot": "weapon_1",
                "item_name": "Sword",
                "stat_combo": "Berserker",
                "required": True,
                "estimated_cost_gold": 20,
            },
            {
                "slot": "relic",
                "item_name": "Relic of Speed",
                "stat_combo": "Power",
                "required": False,
                "estimated_cost_gold": 10,
            },
        ],
        "estimated_transition_cost_gold": 80,
    }


def _matching_account_gear() -> dict:
    return {
        "profession": "Revenant",
        "specializations": ["Herald"],
        "preferred_game_modes": ["strike"],
        "difficulty_preference": "medium",
        "wallet_gold": 120,
        "gear": [
            {"slot": "chest", "item_name": "Owned Ascended Chest", "stat_combo": "Berserker"},
            {"slot": "weapon_1", "item_name": "Owned Sword", "stat_combo": "Berserker"},
            {"slot": "relic", "item_name": "Owned Relic", "stat_combo": "Power"},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
