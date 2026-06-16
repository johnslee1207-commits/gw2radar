from enum import Enum


class GatewayStatus(str, Enum):
    OK = "ok"
    CACHE_HIT = "cache_hit"
    REFRESH_PENDING = "refresh_pending"
    RATE_LIMITED_RETRYING = "rate_limited_retrying"
