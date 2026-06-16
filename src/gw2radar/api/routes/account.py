from pydantic import BaseModel
from fastapi import APIRouter

from gw2radar.api.state import delete_account_snapshot, reset_cached_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.security.api_key_store import EncryptedApiKeyStore

router = APIRouter(prefix="/account", tags=["account"])


class ApiKeyRequest(BaseModel):
    api_key: str


@router.get("/api-key/status")
def get_api_key_status() -> dict:
    return _with_key_store(lambda store: store.status().__dict__)


@router.put("/api-key")
def put_api_key(request: ApiKeyRequest) -> dict:
    return _with_key_store(lambda store: store.set(request.api_key).__dict__)


@router.delete("/api-key")
def delete_api_key() -> dict:
    return _with_key_store(lambda store: store.delete().__dict__)


@router.delete("/snapshot")
def delete_snapshot() -> dict:
    deleted = delete_account_snapshot()
    reset_cached_graph()
    return {"status": "deleted", "deleted": deleted}


def _with_key_store(callback):
    init_db()
    with db_session.SessionLocal() as session:
        return callback(EncryptedApiKeyStore(session))
