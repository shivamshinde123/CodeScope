"""Project model for organizing work items."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Project:
    """Represents a project owned by a user.

    Attributes:
        id: Unique project identifier (auto-assigned on save).
        name: Project name (must be unique per owner).
        owner_id: ID of the user who owns this project.
        description: Optional project description.
        status: Current status — 'active', 'archived', or 'deleted'.
        created_at: Timestamp of project creation.
        updated_at: Timestamp of last modification.
    """

    name: str
    owner_id: int
    description: str = ""
    status: str = "active"
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    _store: dict = field(default_factory=dict, repr=False)

    def save(self) -> "Project":
        """Persist the project to the store."""
        if self.id is None:
            self.id = len(Project._store) + 1
        self.updated_at = datetime.now(timezone.utc)
        Project._store[self.id] = self
        return self

    def to_dict(self) -> dict:
        """Serialize project to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "owner_id": self.owner_id,
            "description": self.description,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def archive(self) -> None:
        """Mark the project as archived."""
        self.status = "archived"
        self.save()

    @classmethod
    def find_by_id(cls, project_id: int) -> Optional["Project"]:
        """Look up a project by ID."""
        return cls._store.get(project_id)

    @classmethod
    def find_by_owner(cls, owner_id: int) -> list["Project"]:
        """List all projects owned by a specific user."""
        return [p for p in cls._store.values() if p.owner_id == owner_id and p.status != "deleted"]
