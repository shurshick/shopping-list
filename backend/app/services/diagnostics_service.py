from collections import deque
from datetime import datetime
from time import monotonic


APP_START_TIME = datetime.utcnow()
_START_MONOTONIC = monotonic()
_EVENTS: deque[dict[str, str]] = deque(maxlen=300)


def uptime_seconds() -> int:
    return int(monotonic() - _START_MONOTONIC)


def record_event(event: str, details: str = "", level: str = "info") -> None:
    _EVENTS.appendleft(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level[:20],
            "event": event[:80],
            "details": details[:255],
        }
    )


def recent_events(limit: int = 100) -> list[dict[str, str]]:
    return list(_EVENTS)[:limit]


record_event("startup", "application module loaded")
