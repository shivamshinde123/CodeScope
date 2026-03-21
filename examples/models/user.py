"""User model for authentication and authorization."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class User:
    """Represents an application user.

    Attributes:
        id: Unique user identifier (auto-assigned on save).
        email: User's email address (must be unique).
        name: Display name.
        role: Authorization role — one of 'admin', 'editor', 'viewer'.
        created_at: Timestamp of account creation.
        last_login: Timestamp of most recent login.
    """

    email: str
    name: str
    role: str = "viewer"
    is_active: bool = True
    id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None

    # In-memory store for demonstration purposes.
    _store: dict = field(default_factory=dict, repr=False)

    def save(self) -> "User":
        """Persist the user to the store."""
        if self.id is None:
            self.id = len(User._store) + 1
        User._store[self.id] = self
        return self

    def to_dict(self) -> dict:
        """Serialize user to a JSON-safe dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }

    @classmethod
    def find_by_email(cls, email: str) -> Optional["User"]:
        """Look up a user by email address."""
        for user in cls._store.values():
            if user.email == email:
                return user
        return None

    @classmethod
    def find_by_id(cls, user_id: int) -> Optional["User"]:
        """Look up a user by ID."""
        return cls._store.get(user_id)
