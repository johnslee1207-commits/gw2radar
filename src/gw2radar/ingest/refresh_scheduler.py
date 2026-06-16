from dataclasses import dataclass

from gw2radar.ingest.request_queue import QueuedRequest, RequestQueue


@dataclass(frozen=True)
class RefreshPriorities:
    user_triggered_active_goal: str = "P0"
    account_snapshot: str = "P1"
    goal_price_refresh: str = "P2"
    public_static_data: str = "P3"
    historical_market_backfill: str = "P4"


class RefreshScheduler:
    def __init__(self, queue: RequestQueue | None = None) -> None:
        self.queue = queue or RequestQueue()

    def schedule(self, endpoint: str, *, params: dict | None = None, priority: str = "P3") -> QueuedRequest:
        return self.queue.enqueue(QueuedRequest(endpoint=endpoint, params=params or {}, priority=priority))
