import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.build_fit import BuildRecord, evaluate_build_fit, get_character_snapshot, list_character_snapshots
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity
from build_fit_helpers import sample_build_import
from gw2radar.db.models import utc_now


def test_manual_character_snapshots_are_available_with_assumptions() -> None:
    snapshots = list_character_snapshots()

    assert snapshots
    assert snapshots[0].source == "manual_sample"
    assert snapshots[0].assumptions
    assert snapshots[0].to_account_gear_snapshot().gear


def test_build_character_snapshot_api_converts_to_account_gear() -> None:
    temp_dir = Path(".test_tmp") / f"build-snapshots-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        response = client.get("/api/v1/builds/character-snapshots")

        assert response.status_code == 200
        payload = response.json()["data"]
        snapshot_id = payload["snapshots"][0]["snapshot_id"]
        assert "manual samples remain as fallback" in payload["boundary"]

        converted = client.get(f"/api/v1/builds/character-snapshots/{snapshot_id}/account-gear")

        assert converted.status_code == 200
        data = converted.json()["data"]
        assert data["account_gear"]["gear"]
        assert data["snapshot"]["assumptions"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


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


def test_synced_character_snapshots_precede_manual_fallbacks() -> None:
    graph = GraphData(account_id="gw2:account:Test.1234")
    graph.add_entity(
        Entity(
            id="gw2:character:Hero One",
            type=EntityType.CHARACTER,
            canonical_name="Hero One",
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            properties={
                "profession": "Mesmer",
                "level": 80,
                "sync_detail_status": "detail_synced",
                "equipment": [
                    {
                        "slot": "Coat",
                        "item_id": 1001,
                        "item_name": "Synced Berserker Chest",
                        "stat_combo": "Berserker",
                        "equipment_category": "armor",
                    },
                    {
                        "slot": "Rune",
                        "item_id": 2001,
                        "item_name": "Superior Rune of the Scholar",
                        "stat_combo": "Rune",
                        "equipment_category": "rune",
                    }
                ],
            },
        )
    )

    snapshots = list_character_snapshots(graph)
    synced = get_character_snapshot("synced_hero_one", graph)

    assert snapshots[0].source == "synced_official_api"
    assert snapshots[0].character_name == "Hero One"
    assert synced is not None
    assert synced.to_account_gear_snapshot().gear[0].item_name == "Synced Berserker Chest"
    assert synced.to_account_gear_snapshot().gear[1].slot == "rune"
    assert synced.to_account_gear_snapshot().gear[1].equipment_category == "rune"
