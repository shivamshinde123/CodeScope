"""Tests for the dashboard service."""

import pytest

from examples.models.dashboard import Dashboard
from examples.services.dashboard_service import (
    create_dashboard,
    get_dashboard,
    list_dashboards,
    add_widget,
    remove_widget,
)


class TestCreateDashboard:
    """Test dashboard creation."""

    def test_create_with_required_fields(self):
        dashboard = create_dashboard(name="My Dashboard", owner_id=1)
        assert dashboard.name == "My Dashboard"
        assert dashboard.owner_id == 1
        assert dashboard.widgets == []

    def test_create_with_description(self):
        dashboard = create_dashboard(
            name="Sales Overview",
            owner_id=1,
            description="Monthly sales metrics",
        )
        assert dashboard.description == "Monthly sales metrics"


class TestWidgetManagement:
    """Test adding and removing widgets."""

    def test_add_widget(self):
        dashboard = create_dashboard(name="Test", owner_id=1)
        add_widget(dashboard.id, widget_type="chart", config={"metric": "sales"})
        updated = get_dashboard(dashboard.id)
        assert len(updated.widgets) == 1

    def test_remove_widget(self):
        dashboard = create_dashboard(name="Test", owner_id=1)
        add_widget(dashboard.id, widget_type="chart", config={"metric": "users"})
        remove_widget(dashboard.id, widget_index=0)
        updated = get_dashboard(dashboard.id)
        assert len(updated.widgets) == 0


class TestListDashboards:
    """Test dashboard listing and filtering."""

    def test_list_by_owner(self):
        create_dashboard(name="D1", owner_id=42)
        create_dashboard(name="D2", owner_id=42)
        create_dashboard(name="D3", owner_id=99)
        dashboards = list_dashboards(owner_id=42)
        assert all(d.owner_id == 42 for d in dashboards)
