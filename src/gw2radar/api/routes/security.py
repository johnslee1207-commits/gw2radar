from pydantic import BaseModel
from fastapi import APIRouter

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.config.settings import get_settings
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.security.privacy_delete import delete_private_data
from gw2radar.security.store_factory import build_secret_store

router = APIRouter(prefix="/api/v1/security", tags=["security"])

LOCAL_USER_ID = "local-user"


class SecurityApiKeyRequest(BaseModel):
    api_key: str


class PrivateDataDeleteRequest(BaseModel):
    delete_api_key: bool = True
    delete_account_snapshot: bool = True
    delete_private_player_state: bool = True
    delete_personal_intelligence: bool = True
    delete_exports: bool = True


@router.post("/api-key", response_model=ApiDataEnvelope)
def save_api_key(request: SecurityApiKeyRequest) -> ApiDataEnvelope:
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data=store.put_api_key(LOCAL_USER_ID, request.api_key).model_dump(mode="json")
        )
    )


@router.get("/api-key/status", response_model=ApiDataEnvelope)
def get_api_key_status() -> ApiDataEnvelope:
    return _with_store(
        lambda store, _session: ApiDataEnvelope(
            data=store.get_status(LOCAL_USER_ID).model_dump(mode="json")
        )
    )


@router.delete("/api-key", response_model=ApiDataEnvelope)
def delete_api_key() -> ApiDataEnvelope:
    return _with_store(lambda store, _session: ApiDataEnvelope(data={"deleted": store.delete_api_key(LOCAL_USER_ID)}))


@router.delete("/private-data", response_model=ApiDataEnvelope)
def delete_private_account_data(request: PrivateDataDeleteRequest) -> ApiDataEnvelope:
    return _with_store(
        lambda store, session: ApiDataEnvelope(
            data=delete_private_data(
                session,
                store,
                user_id=LOCAL_USER_ID,
                delete_api_key=request.delete_api_key,
                delete_account_snapshot=request.delete_account_snapshot,
                delete_private_player_state=request.delete_private_player_state,
                delete_personal_intelligence=request.delete_personal_intelligence,
                delete_exports=request.delete_exports,
            )
        )
    )


def _with_store(callback):
    init_db()
    with db_session.SessionLocal() as session:
        store = build_secret_store(get_settings(), session)
        return callback(store, session)
