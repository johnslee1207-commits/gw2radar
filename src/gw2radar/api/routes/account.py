from pydantic import BaseModel
from fastapi import APIRouter

from gw2radar.api import state
from gw2radar.api.state import delete_account_snapshot, reset_cached_graph
from gw2radar.commercial.build_fit import list_character_snapshots
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.ingest.account_sync_coordinator import AccountSyncCoordinator
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError, Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ontology.graph_layers import GraphLayer
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
    return _with_key_store(_inspect_permissions)


@router.get("/diagnostic")
def get_account_connection_diagnostic() -> dict:
    def diagnose(store: EncryptedApiKeyStore) -> dict:
        key_status = store.status().__dict__
        permission_report = _inspect_permissions(store)
        graph = state.get_graph()
        has_key = key_status["is_configured"]
        sync_status = AccountSyncCoordinator(
            session=store.session,
            graph_loader=state.get_graph,
            graph_saver=state.save_graph,
            gateway=permission_gateway_factory(),
        ).status()
        snapshots = list_character_snapshots(graph)
        synced_snapshots = [snapshot for snapshot in snapshots if snapshot.source == "synced_official_api"]
        synced_gear_count = sum(len(snapshot.gear) for snapshot in synced_snapshots)
        private_state_count = sum(1 for item in graph.player_state if item.graph_layer is GraphLayer.PRIVATE_PLAYER_STATE)
        checks = [
            _diagnostic_check(
                "api_key_stored",
                "API key stored",
                key_status["is_configured"],
                "API key is stored and masked.",
                "No API key is stored. Save a read-only GW2 API key first.",
            ),
            _diagnostic_check(
                "permissions_ready",
                "Required permissions ready",
                key_status["is_configured"] and permission_report.get("limited_mode") is False,
                "Required permissions are present for account-aware features.",
                "Required permissions are missing or could not be checked.",
                warn=key_status["is_configured"] and permission_report.get("limited_mode") is True,
            ),
            _diagnostic_check(
                "sync_job_visible",
                "Sync queue visible",
                bool(sync_status.get("latest")) or sync_status.get("counts", {}).get("succeeded", 0) > 0,
                "An account sync job is visible in queue history.",
                "No account sync job is visible. Run Sync now, then re-run this diagnostic.",
                warn=key_status["is_configured"],
            ),
            _diagnostic_check(
                "private_snapshot_written",
                "Private account snapshot written",
                private_state_count > 0,
                f"{private_state_count} private player-state records are available.",
                "No private account snapshot is available yet. Drain one sync job after queueing.",
                warn=key_status["is_configured"],
            ),
            _diagnostic_check(
                "synced_character_snapshot",
                "Synced character snapshot available",
                bool(synced_snapshots),
                f"{len(synced_snapshots)} synced official character snapshots are available.",
                "Build Fit only has manual sample snapshots. Sync character details before using account gear.",
                warn=has_key,
            ),
            _diagnostic_check(
                "build_fit_bridge_ready",
                "Build Fit gear bridge ready",
                synced_gear_count > 0,
                f"{synced_gear_count} synced gear entries can be converted for Build Fit.",
                "No synced gear entries are available for Build Fit conversion.",
                warn=has_key,
            ),
        ]
        return {
            "schema_version": "gw2radar.account_connection_diagnostic.v1",
            "summary_status": _diagnostic_summary_status(checks),
            "checks": checks,
            "key_status": key_status,
            "permission_report": permission_report,
            "sync_status": sync_status,
            "snapshot_summary": {
                "private_player_state_count": private_state_count,
                "synced_character_snapshot_count": len(synced_snapshots),
                "manual_snapshot_count": len(snapshots) - len(synced_snapshots),
                "synced_gear_count": synced_gear_count,
            },
            "next_actions": _diagnostic_next_actions(checks),
            "boundary": "Read-only diagnostic. Raw API keys and private item payloads are not returned.",
        }

    return _with_key_store(diagnose)


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


def _inspect_permissions(store: EncryptedApiKeyStore) -> dict:
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


def _diagnostic_check(
    check_id: str,
    label: str,
    passed: bool,
    pass_message: str,
    fail_message: str,
    *,
    warn: bool = False,
) -> dict:
    status = "pass" if passed else "warn" if warn else "fail"
    return {
        "check_id": check_id,
        "label": label,
        "status": status,
        "player_message": pass_message if passed else fail_message,
    }


def _diagnostic_summary_status(checks: list[dict]) -> str:
    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        return "blocked"
    if "warn" in statuses:
        return "needs_sync"
    return "ready"


def _diagnostic_next_actions(checks: list[dict]) -> list[str]:
    actions = []
    for check in checks:
        if check["status"] == "pass":
            continue
        if check["check_id"] == "api_key_stored":
            actions.append("Save a GW2 API key, then check permissions.")
        elif check["check_id"] == "permissions_ready":
            actions.append("Create or update the GW2 API key with account, characters, inventories, wallet, and progression permissions.")
        elif check["check_id"] == "sync_job_visible":
            actions.append("Run Sync now to queue an account snapshot job.")
        elif check["check_id"] == "private_snapshot_written":
            actions.append("Drain one sync job in local development, then refresh the diagnostic.")
        elif check["check_id"] == "synced_character_snapshot":
            actions.append("Confirm character permission and rerun account sync so character detail can be saved.")
        elif check["check_id"] == "build_fit_bridge_ready":
            actions.append("Load character snapshots in Build Fit after sync completes.")
    return actions or ["Account connection, sync, and Build Fit bridge are ready."]
