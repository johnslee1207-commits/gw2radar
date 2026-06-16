import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database
from gw2radar.ontology.graph_layers import GraphLayer


def test_private_data_delete_preserves_public_graph() -> None:
    temp_dir = Path(".test_tmp") / f"private-delete-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'private.db'}")
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        assert client.post("/goals/gw2:goal:aurora/actions/generate").status_code == 200
        assert client.post("/api/v1/security/api-key", json={"api_key": "12345678-abcdef-secret-key"}).status_code == 200

        deleted = client.request(
            "DELETE",
            "/api/v1/security/private-data",
            json={
                "delete_api_key": True,
                "delete_account_snapshot": True,
                "delete_private_player_state": True,
                "delete_personal_intelligence": True,
                "delete_exports": True,
            },
        )

        assert deleted.status_code == 200
        assert deleted.json()["data"]["api_key_deleted"] is True
        state.reset_cached_graph()
        graph = state.get_graph()
        assert graph.entities["gw2:goal:aurora"].graph_layer == GraphLayer.PUBLIC_GAME
        assert not graph.player_state
        assert not graph.actions
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
