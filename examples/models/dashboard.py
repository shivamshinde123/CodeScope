"""Dashboard model for analytics and metrics display."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Dashboard:
    """Represents a user-configurable analytics dashboard.

    Attributes:
        id: Unique dashboard identifier.
        name: Dashboard display name.
        owner_id: ID of the dashboard owner.
        layout: JSON layout configuration.
        widgets: List of widget configurations.
        is_public: Whether the dashboard is publicly accessible.
        created_at: Creation timestamp.
    """

    name: str
    owner_id: int
    layout: str = "grid"
    is_public: bool = False
    id: Optional[int] = None
    widgets: list = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _store: dict = field(default_factory=dict, repr=False)

    def save(self) -> "Dashboard":
        if self.id is None:
            self.id = len(Dashboard._store) + 1
        Dashboard._store[self.id] = self
        return self

    def add_widget(self, widget_type: str, config: dict) -> dict:
        widget = {
            "id": len(self.widgets) + 1,
            "type": widget_type,
            "config": config,
        }
        self.widgets.append(widget)
        self.save()
        return widget

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "layout": self.layout,
            "is_public": self.is_public,
            "widgets": self.widgets,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def find_by_owner(cls, owner_id: int) -> list["Dashboard"]:
        return [d for d in cls._store.values() if d.owner_id == owner_id]
