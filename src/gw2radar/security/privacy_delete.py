from pathlib import Path
import shutil

from sqlalchemy.orm import Session

from gw2radar.api import state
from gw2radar.db.repositories import GraphRepository
from gw2radar.security.secret_store import SecretStore


def delete_private_data(
    session: Session,
    secret_store: SecretStore,
    *,
    user_id: str = "local-user",
    delete_api_key: bool = True,
    delete_account_snapshot: bool = True,
    delete_private_player_state: bool = True,
    delete_personal_intelligence: bool = True,
    delete_exports: bool = True,
) -> dict:
    api_key_deleted = secret_store.delete_api_key(user_id) if delete_api_key else False
    deleted_graph = {"actions": 0, "player_state": 0, "relations": 0, "entities": 0}
    if delete_account_snapshot or delete_private_player_state or delete_personal_intelligence:
        deleted_graph = GraphRepository(session).delete_account_snapshot()
        state.reset_cached_graph()
    exports_deleted = False
    if delete_exports:
        output_dir = Path("outputs")
        exports_deleted = output_dir.exists()
        shutil.rmtree(output_dir, ignore_errors=True)
    return {
        "api_key_deleted": api_key_deleted,
        "account_snapshot_deleted": delete_account_snapshot and sum(deleted_graph.values()) > 0,
        "private_player_state_deleted": delete_private_player_state and deleted_graph["player_state"] > 0,
        "personal_intelligence_deleted": delete_personal_intelligence and deleted_graph["actions"] > 0,
        "exports_deleted": exports_deleted,
        "deleted": deleted_graph,
    }
