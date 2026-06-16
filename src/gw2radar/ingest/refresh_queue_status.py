from enum import Enum


class RefreshQueueStatus(str, Enum):
    QUEUED = "queued"
    DELAYED = "delayed"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
