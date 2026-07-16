from collections import deque
from time import monotonic

from ..time_utils import utc_now


APP_START_TIME = utc_now()
_START_MONOTONIC = monotonic()
_EVENTS: deque[dict[str, str]] = deque(maxlen=300)


def uptime_seconds() -> int:
    return int(monotonic() - _START_MONOTONIC)


def record_event(event: str, details: str = "", level: str = "info") -> None:
    _EVENTS.appendleft(
        {
            "timestamp": utc_now().isoformat(),
            "level": level[:20],
            "event": event[:80],
            "details": details[:255],
        }
    )


def recent_events(limit: int = 100) -> list[dict[str, str]]:
    return list(_EVENTS)[:limit]


record_event("startup", "application module loaded")
