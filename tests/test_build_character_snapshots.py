from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.commercial.build_fit import BuildRecord, evaluate_build_fit, get_character_snapshot, list_character_snapshots
from build_fit_helpers import sample_build_import
from gw2radar.db.models import utc_now


client = TestClient(app)


def test_manual_character_snapshots_are_available_with_assumptions() -> None:
    snapshots = list_character_snapshots()

    assert snapshots
    assert snapshots[0].source == "manual_sample"
    assert snapshots[0].assumptions
    assert snapshots[0].to_account_gear_snapshot().gear


def test_build_character_snapshot_api_converts_to_account_gear() -> None:
    response = client.get("/api/v1/builds/character-snapshots")

    assert response.status_code == 200
    payload = response.json()["data"]
    snapshot_id = payload["snapshots"][0]["snapshot_id"]
    assert "Manual sample snapshots only" in payload["boundary"]

    converted = client.get(f"/api/v1/builds/character-snapshots/{snapshot_id}/account-gear")

    assert converted.status_code == 200
    data = converted.json()["data"]
    assert data["account_gear"]["gear"]
    assert data["snapshot"]["assumptions"]


def test_manual_virtuoso_snapshot_matches_sample_build_better_than_manual_chest_only() -> None:
    build_import = sample_build_import()
    build = BuildRecord(
        **build_import.model_dump(),
        build_id="build_test",
        user_id="local-user",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    snapshot = get_character_snapshot("manual_virtuoso_power")
    assert snapshot is not None

    rich_fit = evaluate_build_fit(build, snapshot.to_account_gear_snapshot())
    light_fit = evaluate_build_fit(
        build,
        snapshot.to_account_gear_snapshot().model_copy(
            update={"gear": [snapshot.to_account_gear_snapshot().gear[2]]}
        ),
    )

    assert rich_fit.score.gear_match >= light_fit.score.gear_match
