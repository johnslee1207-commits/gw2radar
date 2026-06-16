from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RefreshQueueStatus(str, Enum):
    QUEUED = "queued"
    DELAYED = "delayed"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RefreshQueuePriority(str, Enum):
    P0_USER_TRIGGERED_ACTIVE_GOAL = "P0_USER_TRIGGERED_ACTIVE_GOAL"
    P1_ACCOUNT_SNAPSHOT = "P1_ACCOUNT_SNAPSHOT"
    P2_GOAL_RELATED_PRICE = "P2_GOAL_RELATED_PRICE"
    P3_PUBLIC_STATIC = "P3_PUBLIC_STATIC"
    P4_MARKET_HISTORY_BACKFILL = "P4_MARKET_HISTORY_BACKFILL"


class RefreshTaskType(str, Enum):
    ACCOUNT_SNAPSHOT_SYNC = "account_snapshot_sync"
    PUBLIC_STATIC_REFRESH = "public_static_refresh"
    GOAL_PRICE_REFRESH = "goal_price_refresh"
    MARKET_HISTORY_BACKFILL = "market_history_backfill"


class RefreshQueueCreate(BaseModel):
    task_type: RefreshTaskType = RefreshTaskType.PUBLIC_STATIC_REFRESH
    priority: RefreshQueuePriority = RefreshQueuePriority.P3_PUBLIC_STATIC
    endpoint: str
    method: str = "GET"
    params_json: dict[str, Any] | None = None
    account_id: str | None = None
    feature_scope: str | None = None
    max_attempts: int = Field(default=3, ge=1)


class RefreshQueueItem(BaseModel):
    id: str
    task_type: RefreshTaskType
    priority: RefreshQueuePriority
    status: RefreshQueueStatus
    endpoint: str
    method: str
    params_hash: str | None = None
    params_json: dict[str, Any] | None = None
    account_id: str | None = None
    feature_scope: str | None = None
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None = None
    leased_until: datetime | None = None
    worker_id: str | None = None
    last_status_code: int | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
