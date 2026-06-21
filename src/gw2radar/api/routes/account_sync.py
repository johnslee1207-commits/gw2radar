from fastapi import APIRouter, HTTPException

from gw2radar.api import state
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.ingest.account_sync_coordinator import AccountSyncCoordinator
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError, Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.permission_validator import Gw2PermissionError

router = APIRouter(prefix="/api/v1/account/sync", tags=["account-sync"])

gateway_factory = Gw2ApiGateway


@router.post("")
def enqueue_account_sync() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.enqueue_sync())


@router.get("/status")
def get_account_sync_status() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.status())


@router.get("/health")
def get_account_sync_worker_health() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.health())


@router.post("/drain-one")
def drain_one_account_sync() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.drain_one())


@router.post("/worker/run")
def run_account_sync_worker(max_jobs: int = 3, worker_id: str = "account-sync-worker-loop") -> dict:
    return _with_coordinator(lambda coordinator: coordinator.run_worker(max_jobs=max_jobs, worker_id=worker_id))


def _with_coordinator(callback):
    init_db()
    with db_session.SessionLocal() as session:
        coordinator = AccountSyncCoordinator(
            session=session,
            graph_loader=state.get_graph,
            graph_saver=state.save_graph,
            gateway=gateway_factory(),
        )
        try:
            return callback(coordinator)
        except Gw2ApiRateLimitError as error:
            raise HTTPException(status_code=429, detail=f"GW2 API token check is rate limited; request_id={error.request_id}") from error
        except Gw2ApiClientError as error:
            raise HTTPException(
                status_code=400,
                detail=f"GW2 API token check failed with status_code={error.status_code}.",
            ) from error
        except (Gw2PermissionError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
