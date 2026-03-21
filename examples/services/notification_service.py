"""Notification service — sends alerts on key events."""

import logging
from typing import Any

logger = logging.getLogger("examples.services.notification")


def notify_project_created(project: Any) -> None:
    """Send notification when a project is created."""
    logger.info(
        "NOTIFICATION: Project '%s' (id=%d) created by user %d",
        project.name,
        project.id,
        project.owner_id,
    )


def notify_project_deleted(project: Any) -> None:
    """Send notification when a project is deleted."""
    logger.info(
        "NOTIFICATION: Project '%s' (id=%d) deleted",
        project.name,
        project.id,
    )


def notify_user_registered(user: Any) -> None:
    """Send welcome notification to a newly registered user."""
    logger.info(
        "NOTIFICATION: Welcome email sent to %s (%s)",
        user.name,
        user.email,
    )
