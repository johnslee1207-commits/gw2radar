from pathlib import Path
import shutil
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.repository import list_sources
from gw2radar.acquisition.seed_packs import import_acquisition_seed_pack, list_acquisition_seed_packs
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_acquisition_seed_pack_lists_safe_baseline_entries() -> None:
    packs = list_acquisition_seed_packs()
    pack = packs[0]

    assert pack.pack_id == "mvp_baseline"
    assert len(pack.entries) == 8
    assert {entry.source.source_type for entry in pack.entries} >= {
        "official_api_public",
        "official_api_private",
        "downloaded_pdf",
        "gw2_wiki",
        "public_build_site",
        "community_signal",
        "manual_note",
    }
    for entry in pack.entries:
        assert "automated_trade" in entry.policy.forbidden_use
        assert "ip_rotation" not in entry.policy.forbidden_use
        assert "proxy_pool" not in entry.policy.forbidden_use


def test_import_acquisition_seed_pack_requires_confirmation_and_is_idempotent() -> None:
    temp_dir = Path(".test_tmp") / f"acq-seeds-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'acq.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            with pytest.raises(ValueError, match="requires confirmation"):
                import_acquisition_seed_pack(session, "mvp_baseline", confirmed=False)

            first = import_acquisition_seed_pack(session, "mvp_baseline", confirmed=True)
            second = import_acquisition_seed_pack(session, "mvp_baseline", confirmed=True)
            sources = list_sources(session)

        assert first.created_count == 8
        assert first.skipped_existing_count == 0
        assert first.updated_policy_count == 8
        assert second.created_count == 0
        assert second.skipped_existing_count == 8
        assert second.updated_policy_count == 8
        assert len(sources) == 8
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_seed_pack_api_list_get_and_import() -> None:
    temp_dir = Path(".test_tmp") / f"acq-seed-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)

        listed = client.get("/api/v1/acquisition/seed-packs")
        detail = client.get("/api/v1/acquisition/seed-packs/mvp_baseline")
        rejected = client.post("/api/v1/acquisition/seed-packs/mvp_baseline/import", json={"confirmed": False})
        imported = client.post("/api/v1/acquisition/seed-packs/mvp_baseline/import", json={"confirmed": True})
        repeated = client.post("/api/v1/acquisition/seed-packs/mvp_baseline/import", json={"confirmed": True})

        assert listed.status_code == 200
        assert listed.json()["data"]["count"] == 1
        assert detail.status_code == 200
        assert len(detail.json()["data"]["pack"]["entries"]) == 8
        assert rejected.status_code == 400
        assert imported.status_code == 200
        assert imported.json()["data"]["result"]["created_count"] == 8
        assert repeated.status_code == 200
        assert repeated.json()["data"]["result"]["skipped_existing_count"] == 8
        assert "12345678-abcdef-secret-key" not in str(imported.json())
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
