"""Business logic for project management."""

import logging
from typing import Optional

from examples.models.project import Project
from examples.services.notification_service import notify_project_created, notify_project_deleted

logger = logging.getLogger("examples.services.project")


def create_project(name: str, owner_id: int, description: str = "") -> Project:
    """Create and persist a new project.

    Sends a notification after successful creation.
    """
    logger.info("Creating project '%s' for owner %d", name, owner_id)
    project = Project(name=name, owner_id=owner_id, description=description)
    project.save()
    notify_project_created(project)
    return project


def get_project(project_id: int) -> Optional[Project]:
    """Retrieve a project by its ID."""
    return Project.find_by_id(project_id)


def list_projects(user_id: int) -> list[Project]:
    """List all active projects for a user."""
    return Project.find_by_owner(user_id)


def delete_project(project_id: int) -> bool:
    """Soft-delete a project by marking its status as 'deleted'.

    Returns True if the project was found and deleted, False otherwise.
    """
    project = Project.find_by_id(project_id)
    if project is None:
        logger.warning("Attempted to delete non-existent project %d", project_id)
        return False

    project.status = "deleted"
    project.save()
    notify_project_deleted(project)
    logger.info("Project %d deleted", project_id)
    return True


def archive_project(project_id: int) -> bool:
    """Archive a project (soft action, can be reversed)."""
    project = Project.find_by_id(project_id)
    if project is None:
        return False

    project.archive()
    logger.info("Project %d archived", project_id)
    return True
