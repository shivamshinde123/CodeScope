"""Audit log model for tracking all system actions."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class AuditLog:
    """Immutable record of a system action for compliance and debugging."""

    action: str
    actor_id: int
    resource_type: str
    resource_id: int
    details: dict = field(default_factory=dict)
    ip_address: str = ""
    id: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _store: list = field(default_factory=list, repr=False)

    def save(self) -> "AuditLog":
        if self.id is None:
            self.id = len(AuditLog._store) + 1
        AuditLog._store.append(self)
        return self

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "action": self.action,
            "actor_id": self.actor_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def find_by_actor(cls, actor_id: int, limit: int = 100) -> list["AuditLog"]:
        return [log for log in cls._store if log.actor_id == actor_id][-limit:]

    @classmethod
    def find_by_resource(cls, resource_type: str, resource_id: int) -> list["AuditLog"]:
        return [
            log for log in cls._store
            if log.resource_type == resource_type and log.resource_id == resource_id
        ]
