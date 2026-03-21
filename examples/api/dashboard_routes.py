"""Dashboard API endpoints."""

from flask import Blueprint, jsonify, request

from examples.services.auth_service import authenticate, authorize
from examples.services.dashboard_service import (
    create_dashboard,
    get_dashboard,
    list_dashboards,
    add_widget,
    share_dashboard,
)

dashboard_api = Blueprint("dashboard_api", __name__)


@dashboard_api.route("/dashboards", methods=["GET"])
@authenticate
def list_user_dashboards(current_user):
    """List all dashboards for the authenticated user."""
    dashboards = list_dashboards(current_user.id)
    return jsonify([d.to_dict() for d in dashboards])


@dashboard_api.route("/dashboards", methods=["POST"])
@authenticate
def create_new_dashboard(current_user):
    """Create a new dashboard."""
    data = request.get_json()
    dashboard = create_dashboard(
        name=data["name"],
        owner_id=current_user.id,
        layout=data.get("layout", "grid"),
    )
    return jsonify(dashboard.to_dict()), 201


@dashboard_api.route("/dashboards/<int:dashboard_id>", methods=["GET"])
@authenticate
def get_single_dashboard(current_user, dashboard_id):
    """Get a dashboard by ID."""
    dashboard = get_dashboard(dashboard_id)
    if not dashboard:
        return jsonify({"error": "Dashboard not found"}), 404
    return jsonify(dashboard.to_dict())


@dashboard_api.route("/dashboards/<int:dashboard_id>/widgets", methods=["POST"])
@authenticate
def add_dashboard_widget(current_user, dashboard_id):
    """Add a widget to a dashboard."""
    data = request.get_json()
    widget = add_widget(
        dashboard_id=dashboard_id,
        widget_type=data["type"],
        config=data.get("config", {}),
        actor_id=current_user.id,
    )
    if not widget:
        return jsonify({"error": "Dashboard not found"}), 404
    return jsonify(widget), 201


@dashboard_api.route("/dashboards/<int:dashboard_id>/share", methods=["POST"])
@authenticate
@authorize(roles=["admin", "editor"])
def share_existing_dashboard(current_user, dashboard_id):
    """Make a dashboard public."""
    if share_dashboard(dashboard_id, current_user.id):
        return jsonify({"message": "Dashboard shared"})
    return jsonify({"error": "Dashboard not found"}), 404
