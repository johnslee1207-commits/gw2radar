from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from gw2radar.db.refresh_queue_repository import RefreshQueueRepository
from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.public_static_refresh import PUBLIC_STATIC_ENDPOINT_TYPES, refresh_public_static
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.refresh_queue import (
    RefreshQueueCreate,
    RefreshQueuePriority,
    RefreshQueueStatus,
    RefreshTaskType,
)


@dataclass
class PublicRefreshCoordinator:
    session: Session
    graph_loader: Callable[[], GraphData]
    graph_saver: Callable[[GraphData], None]
    gateway: Gw2ApiGateway

    def enqueue(self, endpoint: str, ids: list[int], *, chunk_size: int = 200) -> dict:
        if endpoint not in PUBLIC_STATIC_ENDPOINT_TYPES:
            raise ValueError(f"Unsupported public static endpoint: {endpoint}")
        normalized_ids = sorted(set(int(item_id) for item_id in ids))
        if not normalized_ids:
            raise ValueError("ids must not be empty.")
        repo = RefreshQueueRepository(self.session)
        item = repo.enqueue(
            RefreshQueueCreate(
                task_type=RefreshTaskType.PUBLIC_STATIC_REFRESH,
                priority=RefreshQueuePriority.P3_PUBLIC_STATIC,
                endpoint=endpoint,
                method="GET",
                params_json={"ids": normalized_ids, "chunk_size": chunk_size},
                feature_scope="public_static_refresh",
            )
        )
        return {
            "status": "queued",
            "task_id": item.id,
            "endpoint": item.endpoint,
            "ids": normalized_ids,
            "chunk_size": chunk_size,
        }

    def status(self) -> dict:
        repo = RefreshQueueRepository(self.session)
        counts = {status.value: 0 for status in RefreshQueueStatus}
        latest = []
        for status in RefreshQueueStatus:
            items = [
                item
                for item in repo.list_by_status(status, as_items=True)
                if item.task_type is RefreshTaskType.PUBLIC_STATIC_REFRESH
            ]
            counts[status.value] = len(items)
            latest.extend(items)
        latest = sorted(latest, key=lambda item: item.created_at, reverse=True)[:5]
        return {
            "status": "ok",
            "counts": counts,
            "latest": [
                {
                    "task_id": item.id,
                    "endpoint": item.endpoint,
                    "status": item.status.value,
                    "params_hash": item.params_hash,
                    "created_at": item.created_at.isoformat(),
                }
                for item in latest
            ],
        }

    def health(self) -> dict:
        repo = RefreshQueueRepository(self.session)
        counts = {status.value: 0 for status in RefreshQueueStatus}
        latest = []
        for status in RefreshQueueStatus:
            items = [
                item
                for item in repo.list_by_status(status, as_items=True)
                if item.task_type is RefreshTaskType.PUBLIC_STATIC_REFRESH
            ]
            counts[status.value] = len(items)
            latest.extend(items)
        latest = sorted(latest, key=lambda item: item.updated_at, reverse=True)[:5]
        queue_depth = counts[RefreshQueueStatus.QUEUED.value] + counts[RefreshQueueStatus.PROCESSING.value]
        retry_depth = counts[RefreshQueueStatus.DELAYED.value]
        failed_depth = counts[RefreshQueueStatus.FAILED.value]
        if failed_depth:
            health_status = "needs_review"
        elif retry_depth:
            health_status = "waiting_retry"
        elif queue_depth:
            health_status = "active"
        else:
            health_status = "idle"
        next_actions = []
        if retry_depth:
            next_actions.append("Wait for the GW2 API backoff window, then run drain-one again.")
        if failed_depth:
            next_actions.append("Review the latest public refresh error code before enqueueing more ids.")
        if not latest:
            next_actions.append("Queue a public static refresh when item, achievement, currency, or recipe facts are stale.")
        return {
            "schema_version": "gw2radar.public_refresh_worker_health.v1",
            "health_status": health_status,
            "counts": counts,
            "queue_depth": queue_depth,
            "retry_depth": retry_depth,
            "failed_depth": failed_depth,
            "latest": [
                {
                    "task_id": item.id,
                    "endpoint": item.endpoint,
                    "status": item.status.value,
                    "attempt_count": item.attempt_count,
                    "max_attempts": item.max_attempts,
                    "next_attempt_at": item.next_attempt_at.isoformat() if item.next_attempt_at else None,
                    "last_error_code": item.last_error_code,
                    "params_hash": item.params_hash,
                    "updated_at": item.updated_at.isoformat(),
                }
                for item in latest
            ],
            "next_actions": next_actions,
            "boundary": "Public refresh health is metadata-only; it must not include raw API keys or private account payloads.",
        }

    def drain_one(self) -> dict:
        repo = RefreshQueueRepository(self.session)
        task = repo.lease_next("public-refresh-drain-one", datetime.now(timezone.utc))
        if task is None:
            return {"status": "idle"}
        if task.task_type is not RefreshTaskType.PUBLIC_STATIC_REFRESH:
            repo.mark_retry(
                task.id,
                error_code="unsupported_task_type",
                error_message=f"Unsupported task type for public refresh drain: {task.task_type.value}",
            )
            return {"status": "skipped", "task_id": task.id}
        params = task.params_json or {}
        graph = self.graph_loader()
        result = refresh_public_static(
            graph,
            self.gateway,
            endpoint=task.endpoint,
            ids=[int(item_id) for item_id in params.get("ids", [])],
            chunk_size=int(params.get("chunk_size", 200)),
        )
        if result["status"] == "synced":
            self.graph_saver(graph)
            repo.mark_done(task.id)
            return {**result, "status": "succeeded", "task_id": task.id}
        repo.mark_retry(
            task.id,
            error_code=result["status"],
            error_message="Public static refresh returned non-ok status.",
            retry_after_seconds=result.get("retry_after_seconds"),
        )
        return {**result, "status": "delayed", "task_id": task.id}
