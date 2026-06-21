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

    def health(self) -> dict:
        status = self.status()
        counts = status.get("counts", {})
        latest = status.get("latest", [])
        queued = int(counts.get("queued") or 0)
        delayed = int(counts.get("delayed") or 0)
        processing = int(counts.get("processing") or 0)
        failed = int(counts.get("failed") or 0)
        succeeded = int(counts.get("succeeded") or 0)
        if failed:
            health_status = "needs_review"
        elif processing or queued:
            health_status = "active"
        elif delayed:
            health_status = "waiting_retry"
        elif succeeded:
            health_status = "ready"
        else:
            health_status = "idle"
        next_actions = []
        if queued or processing:
            next_actions.append("Run the account sync worker loop or wait for the local worker to finish queued jobs.")
        if delayed:
            next_actions.append("Wait for the retry window, then run the worker loop again.")
        if failed:
            next_actions.append("Open the latest job diagnostics and requeue after fixing the failure.")
        if not latest:
            next_actions.append("Queue account sync before expecting account-aware results.")
        if not next_actions:
            next_actions.append("Queue sync again only when the player wants fresher account data.")
        return {
            "schema_version": "gw2radar.account_sync_worker_health.v1",
            "health_status": health_status,
            "counts": counts,
            "latest": latest,
            "queue_depth": queued + delayed + processing,
            "retry_depth": delayed,
            "failed_depth": failed,
            "endpoint_progress": status.get("endpoint_progress", []),
            "next_actions": next_actions,
            "boundary": "Account sync worker health is metadata-only and excludes raw API keys and private account payloads.",
        }

    def run_worker(self, *, max_jobs: int = 3, worker_id: str = "account-sync-worker-loop") -> dict:
        max_jobs = max(1, min(int(max_jobs or 1), 25))
        results: list[dict] = []
        for _index in range(max_jobs):
            result = self._drain_one_with_worker(worker_id)
            results.append(result)
            if result.get("status") == "idle":
                break
        processed = [result for result in results if result.get("status") != "idle"]
        succeeded = [result for result in processed if result.get("status") == "succeeded"]
        delayed = [result for result in processed if result.get("status") == "delayed"]
        failed = [result for result in processed if result.get("status") in {"failed", "skipped"}]
        health = self.health()
        if failed:
            worker_status = "needs_review"
        elif delayed:
            worker_status = "waiting_retry"
        elif succeeded:
            worker_status = "drained"
        else:
            worker_status = "idle"
        return {
            "schema_version": "gw2radar.account_sync_worker_run.v1",
            "worker_status": worker_status,
            "worker_id": worker_id,
            "max_jobs": max_jobs,
            "processed_count": len(processed),
            "succeeded_count": len(succeeded),
            "delayed_count": len(delayed),
            "failed_count": len(failed),
            "results": results,
            "health": health,
            "next_actions": health.get("next_actions", []),
            "boundary": "Account sync worker loop is explicit and bounded; it does not run as an unmanaged background daemon or expose raw API keys.",
        }

    def drain_one(self) -> dict:
        return self._drain_one_with_worker("account-sync-drain-one")

    def _drain_one_with_worker(self, worker_id: str) -> dict:
        api_key = self._require_api_key()
        repo = RefreshQueueRepository(self.session)
        task = repo.lease_next(worker_id, datetime.now(timezone.utc))
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
