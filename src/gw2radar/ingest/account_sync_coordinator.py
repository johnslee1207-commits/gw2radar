from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.account_snapshot_sync import sync_account_snapshot
from gw2radar.ingest.endpoint_schema import endpoint_schema
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.permission_validator import validate_endpoint_permissions
from gw2radar.ingest.refresh_queue import (
    RefreshQueueCreate,
    RefreshQueueItem,
    RefreshQueuePriority,
    RefreshQueueStatus,
    RefreshTaskType,
)
from gw2radar.security.api_key_store import EncryptedApiKeyStore

ACCOUNT_SYNC_ENDPOINTS = (
    "/v2/account",
    "/v2/characters",
    "/v2/account/wallet",
    "/v2/account/materials",
    "/v2/account/bank",
    "/v2/account/inventory",
    "/v2/account/achievements",
    "/v2/commerce/transactions/current/buys",
    "/v2/commerce/transactions/current/sells",
)

REQUIRED_ACCOUNT_SYNC_ENDPOINTS = (
    "/v2/account",
    "/v2/characters",
    "/v2/account/wallet",
    "/v2/account/materials",
    "/v2/account/bank",
    "/v2/account/inventory",
    "/v2/account/achievements",
)

ENDPOINT_LABELS = {
    "/v2/account": "Account profile",
    "/v2/characters": "Characters",
    "/v2/account/wallet": "Wallet currencies",
    "/v2/account/materials": "Materials",
    "/v2/account/bank": "Bank",
    "/v2/account/inventory": "Shared inventory",
    "/v2/account/achievements": "Achievements",
    "/v2/commerce/transactions/current/buys": "Trading post buy orders",
    "/v2/commerce/transactions/current/sells": "Trading post sell orders",
}


@dataclass
class AccountSyncCoordinator:
    session: Session
    graph_loader: Callable[[], GraphData]
    graph_saver: Callable[[GraphData], None]
    gateway: Gw2ApiGateway

    def enqueue_sync(self) -> dict:
        api_key = self._require_api_key()
        tokeninfo = self.gateway._fetch_tokeninfo(api_key, request_id="account-sync:tokeninfo")
        for endpoint in REQUIRED_ACCOUNT_SYNC_ENDPOINTS:
            validate_endpoint_permissions(endpoint, tokeninfo)

        repo = RefreshQueueRepository(self.session)
        item = repo.enqueue(
            RefreshQueueCreate(
                task_type=RefreshTaskType.ACCOUNT_SNAPSHOT_SYNC,
                priority=RefreshQueuePriority.P1_ACCOUNT_SNAPSHOT,
                endpoint="/v2/account",
                method="GET",
                params_json={"sync_scope": "account_snapshot"},
                feature_scope="account_snapshot_sync",
                max_attempts=3,
            )
        )
        return {
            "status": "queued",
            "task_id": item.id,
            "task_type": item.task_type.value,
            "masked_key": EncryptedApiKeyStore(self.session).status().masked_key,
            "endpoint_progress": self._endpoint_progress("queued", token_permissions=set(tokeninfo.get("permissions", []))),
        }

    def status(self) -> dict:
        repo = RefreshQueueRepository(self.session)
        tasks: list[RefreshQueueItem] = []
        counts = {status.value: 0 for status in RefreshQueueStatus}
        for status in RefreshQueueStatus:
            items = [
                item
                for item in repo.list_by_status(status, as_items=True)
                if item.task_type is RefreshTaskType.ACCOUNT_SNAPSHOT_SYNC
            ]
            counts[status.value] = len(items)
            tasks.extend(items)
        latest = sorted(tasks, key=lambda item: item.created_at, reverse=True)[:5]
        latest_status = latest[0].status.value if latest else "not_started"
        return {
            "status": "ok",
            "counts": counts,
            "endpoint_progress": self._endpoint_progress(latest_status),
            "latest": [
                {
                    "task_id": item.id,
                    "status": item.status.value,
                    "attempt_count": item.attempt_count,
                    "last_error_code": item.last_error_code,
                    "created_at": item.created_at.isoformat(),
                }
                for item in latest
            ],
        }

    def drain_one(self) -> dict:
        api_key = self._require_api_key()
        repo = RefreshQueueRepository(self.session)
        task = repo.lease_next("account-sync-drain-one", datetime.now(timezone.utc))
        if task is None:
            return {"status": "idle"}
        if task.task_type is not RefreshTaskType.ACCOUNT_SNAPSHOT_SYNC:
            repo.mark_retry(
                task.id,
                error_code="unsupported_task_type",
                error_message=f"Unsupported task type for account sync drain: {task.task_type.value}",
            )
            return {"status": "skipped", "task_id": task.id}

        graph = self.graph_loader()
        result = sync_account_snapshot(graph, self.gateway, api_key=api_key)
        if result["status"] == "synced":
            self.graph_saver(graph)
            repo.mark_done(task.id)
            return {**result, "status": "succeeded", "task_id": task.id, "endpoint_progress": self._endpoint_progress("succeeded")}
        repo.mark_retry(
            task.id,
            error_code="refresh_pending",
            error_message="Account sync returned refresh_pending.",
        )
        return {"status": "delayed", "task_id": task.id, **result, "endpoint_progress": self._endpoint_progress("delayed")}

    def _require_api_key(self) -> str:
        api_key = EncryptedApiKeyStore(self.session).get()
        if not api_key:
            raise ValueError("API key is not configured.")
        return api_key

    def _endpoint_progress(self, status: str, token_permissions: set[str] | None = None) -> list[dict]:
        normalized = {
            "queued": "queued",
            "processing": "syncing",
            "succeeded": "succeeded",
            "failed": "needs_review",
            "retry_scheduled": "delayed",
            "not_started": "not_started",
            "delayed": "delayed",
        }.get(status, status)
        progress = []
        for endpoint in ACCOUNT_SYNC_ENDPOINTS:
            required = endpoint_schema(endpoint).required_permissions
            missing = sorted(set(required).difference(token_permissions or set())) if token_permissions is not None else []
            endpoint_status = "blocked" if missing else normalized
            progress.append(
                {
                    "endpoint": endpoint,
                    "label": ENDPOINT_LABELS[endpoint],
                    "required_permissions": required,
                    "missing_permissions": missing,
                    "status": endpoint_status,
                    "player_message": _player_sync_message(endpoint_status, ENDPOINT_LABELS[endpoint]),
                }
            )
        return progress


def _player_sync_message(status: str, label: str) -> str:
    if status == "succeeded":
        return f"{label} synced into the private account layer."
    if status == "queued":
        return f"{label} is queued for the next account sync worker."
    if status == "syncing":
        return f"{label} is currently being refreshed."
    if status == "blocked":
        return f"{label} is blocked by missing API key permissions."
    if status == "delayed":
        return f"{label} is delayed and should be retried later."
    return f"{label} has not started."
