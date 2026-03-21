"""Business logic for dashboard management."""

import logging
from typing import Optional

from examples.models.dashboard import Dashboard
from examples.models.audit_log import AuditLog
from examples.services.analytics_service import track_event

logger = logging.getLogger("examples.services.dashboard")


def create_dashboard(name: str, owner_id: int, layout: str = "grid") -> Dashboard:
    """Create a new dashboard and log the action."""
    logger.info("Creating dashboard '%s' for user %d", name, owner_id)
    dashboard = Dashboard(name=name, owner_id=owner_id, layout=layout)
    dashboard.save()

    AuditLog(
        action="dashboard.created",
        actor_id=owner_id,
        resource_type="dashboard",
        resource_id=dashboard.id,
    ).save()

    track_event("dashboard_created", {"dashboard_id": dashboard.id})
    return dashboard


def get_dashboard(dashboard_id: int) -> Optional[Dashboard]:
    return Dashboard._store.get(dashboard_id)


def list_dashboards(owner_id: int) -> list[Dashboard]:
    return Dashboard.find_by_owner(owner_id)


def add_widget(dashboard_id: int, widget_type: str, config: dict, actor_id: int) -> Optional[dict]:
    """Add a widget to a dashboard."""
    dashboard = get_dashboard(dashboard_id)
    if not dashboard:
        return None

    widget = dashboard.add_widget(widget_type, config)

    AuditLog(
        action="widget.added",
        actor_id=actor_id,
        resource_type="dashboard",
        resource_id=dashboard_id,
        details={"widget_type": widget_type},
    ).save()

    return widget


def share_dashboard(dashboard_id: int, actor_id: int) -> bool:
    """Make a dashboard publicly accessible."""
    dashboard = get_dashboard(dashboard_id)
    if not dashboard:
        return False

    dashboard.is_public = True
    dashboard.save()

    AuditLog(
        action="dashboard.shared",
        actor_id=actor_id,
        resource_type="dashboard",
        resource_id=dashboard_id,
    ).save()

    track_event("dashboard_shared", {"dashboard_id": dashboard_id})
    return True
