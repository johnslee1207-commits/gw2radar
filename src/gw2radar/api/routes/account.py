from pydantic import BaseModel
from fastapi import APIRouter

from gw2radar.api.state import delete_account_snapshot, reset_cached_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError, Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.security.api_key_permissions import build_missing_key_permission_report, build_permission_report
from gw2radar.security.api_key_store import EncryptedApiKeyStore

router = APIRouter(prefix="/account", tags=["account"])
permission_gateway_factory = Gw2ApiGateway


class ApiKeyRequest(BaseModel):
    api_key: str


@router.get("/api-key/status")
def get_api_key_status() -> dict:
    return _with_key_store(lambda store: store.status().__dict__)


@router.get("/api-key/permissions")
def get_api_key_permissions() -> dict:
    def inspect(store: EncryptedApiKeyStore) -> dict:
        api_key = store.get()
        if not api_key:
            return build_missing_key_permission_report().model_dump(mode="json")

        gateway = permission_gateway_factory()
        try:
            tokeninfo_payload = gateway._fetch_tokeninfo(api_key, request_id="account:permissions:tokeninfo")
        except Gw2ApiRateLimitError:
            report = build_missing_key_permission_report().model_copy(
                update={
                    "key_configured": True,
                    "assumptions": ["Tokeninfo permission check is rate limited; try again later."],
                }
            )
            return report.model_dump(mode="json")
        except Gw2ApiClientError as error:
            report = build_missing_key_permission_report().model_copy(
                update={
                    "key_configured": True,
                    "assumptions": [f"Tokeninfo permission check failed with {error.error_code}."],
                }
            )
            return report.model_dump(mode="json")

        return build_permission_report(tokeninfo_payload).model_dump(mode="json")

    return _with_key_store(inspect)


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
