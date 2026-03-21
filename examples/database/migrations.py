"""Database migration runner."""

import logging
from typing import Callable

logger = logging.getLogger("examples.database.migrations")

_migrations: list[dict] = []


def register_migration(version: str, description: str):
    """Decorator to register a migration function."""
    def decorator(func: Callable):
        _migrations.append({
            "version": version,
            "description": description,
            "func": func,
            "applied": False,
        })
        return func
    return decorator


def run_pending_migrations() -> list[str]:
    """Run all migrations that haven't been applied yet."""
    applied = []
    for migration in _migrations:
        if not migration["applied"]:
            logger.info(
                "Applying migration %s: %s",
                migration["version"],
                migration["description"],
            )
            migration["func"]()
            migration["applied"] = True
            applied.append(migration["version"])
    return applied


@register_migration("001", "Create users table")
def _create_users():
    logger.info("Creating users table")


@register_migration("002", "Create projects table")
def _create_projects():
    logger.info("Creating projects table")


@register_migration("003", "Create dashboards table")
def _create_dashboards():
    logger.info("Creating dashboards table")


@register_migration("004", "Create audit_logs table")
def _create_audit_logs():
    logger.info("Creating audit_logs table")
