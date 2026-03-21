"""Analytics service — tracks usage events for metrics."""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("examples.services.analytics")

_event_log: list[dict[str, Any]] = []


def track_event(event_name: str, metadata: dict[str, Any] | None = None) -> None:
    """Record an analytics event.

    Args:
        event_name: Name of the event (e.g. "project_created").
        metadata: Optional key-value pairs with event context.
    """
    entry = {
        "event": event_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    _event_log.append(entry)
    logger.info("Event tracked: %s %s", event_name, metadata)


def get_event_count(event_name: str) -> int:
    """Return the total count of a specific event."""
    return sum(1 for e in _event_log if e["event"] == event_name)


def get_recent_events(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recent events."""
    return _event_log[-limit:]
