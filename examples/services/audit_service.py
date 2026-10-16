"""Audit service for querying and exporting audit logs."""

import logging
from datetime import datetime, timezone
from typing import Optional

from examples.models.audit_log import AuditLog

logger = logging.getLogger("examples.services.audit")


def get_user_activity(user_id: int, limit: int = 50) -> list[dict]:
    """Get recent activity for a specific user."""
    logs = AuditLog.find_by_actor(user_id, limit=limit)
    return [log.to_dict() for log in logs]


def get_resource_history(resource_type: str, resource_id: int) -> list[dict]:
    """Get the full audit trail for a specific resource."""
    logs = AuditLog.find_by_resource(resource_type, resource_id)
    return [log.to_dict() for log in logs]


def export_audit_logs(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[dict]:
    """Export audit logs within a date range."""
    if start_date is None:
        start_date = datetime.min.replace(tzinfo=timezone.utc)
    if end_date is None:
        end_date = datetime.now(timezone.utc)

    return [
        log.to_dict()
        for log in AuditLog._store
        if start_date <= log.timestamp <= end_date
    ]
