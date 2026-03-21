"""Tests for project service."""

from examples.models.project import Project
from examples.services.project_service import (
    create_project,
    get_project,
    list_projects,
    delete_project,
    archive_project,
)


class TestProjectService:
    def setup_method(self):
        Project._store.clear()

    def test_create_project(self):
        project = create_project("test-project", owner_id=1, description="A test")
        assert project.id is not None
        assert project.name == "test-project"
        assert project.status == "active"

    def test_get_project(self):
        created = create_project("findme", owner_id=1)
        found = get_project(created.id)
        assert found is not None
        assert found.name == "findme"

    def test_list_projects(self):
        create_project("p1", owner_id=1)
        create_project("p2", owner_id=1)
        create_project("p3", owner_id=2)
        assert len(list_projects(user_id=1)) == 2

    def test_delete_project(self):
        project = create_project("deleteme", owner_id=1)
        assert delete_project(project.id) is True
        assert get_project(project.id).status == "deleted"

    def test_delete_nonexistent(self):
        assert delete_project(999) is False

    def test_archive_project(self):
        project = create_project("archiveme", owner_id=1)
        assert archive_project(project.id) is True
        assert get_project(project.id).status == "archived"
