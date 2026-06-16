from dataclasses import dataclass, field
from time import monotonic


@dataclass
class TokenBucketRateLimiter:
    burst_capacity: int = 250
    refill_rate_per_second: float = 4.0
    hard_max_per_minute: int = 240
    _tokens: float = field(init=False)
    _last_refill: float = field(default_factory=monotonic)
    _minute_window_started: float = field(default_factory=monotonic)
    _minute_count: int = 0
    _penalty_multiplier: float = 1.0

    def __post_init__(self) -> None:
        self._tokens = float(self.burst_capacity)

    def allow_request(self) -> bool:
        now = monotonic()
        self._refill(now)
        if now - self._minute_window_started >= 60:
            self._minute_window_started = now
            self._minute_count = 0
        if self._minute_count >= self.hard_max_per_minute:
            return False
        if self._tokens < 1:
            return False
        self._tokens -= 1
        self._minute_count += 1
        return True

    def apply_429_penalty(self) -> None:
        self._penalty_multiplier = min(self._penalty_multiplier * 2, 8)

    def _refill(self, now: float) -> None:
        elapsed = max(now - self._last_refill, 0)
        refill = elapsed * (self.refill_rate_per_second / self._penalty_multiplier)
        self._tokens = min(float(self.burst_capacity), self._tokens + refill)
        self._last_refill = now
