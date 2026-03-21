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


def get_events_by_type(event_name: str, limit: int = 100) -> list[dict[str, Any]]:
    """Return events filtered by type."""
    return [e for e in _event_log if e["event"] == event_name][-limit:]


def get_dashboard_analytics(dashboard_id: int) -> dict[str, Any]:
    """Get aggregated analytics for a specific dashboard."""
    dashboard_events = [
        e for e in _event_log
        if e.get("metadata", {}).get("dashboard_id") == dashboard_id
    ]
    return {
        "dashboard_id": dashboard_id,
        "total_events": len(dashboard_events),
        "event_types": list({e["event"] for e in dashboard_events}),
        "last_activity": dashboard_events[-1]["timestamp"] if dashboard_events else None,
    }
