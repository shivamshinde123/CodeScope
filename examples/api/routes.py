"""API route definitions for the example application."""

from flask import Blueprint, jsonify, request

from examples.models.user import User
from examples.models.project import Project
from examples.services.auth_service import authenticate, authorize
from examples.services.project_service import (
    create_project,
    get_project,
    list_projects,
    delete_project,
)
from examples.utils.validators import validate_email, validate_project_name
from examples.utils.rate_limiter import rate_limit

api = Blueprint("api", __name__)


@api.route("/users", methods=["POST"])
@rate_limit(max_calls=10, period=60)
def register_user():
    """Register a new user account."""
    data = request.get_json()
    if not validate_email(data.get("email", "")):
        return jsonify({"error": "Invalid email"}), 400

    user = User(
        email=data["email"],
        name=data.get("name", ""),
        role=data.get("role", "viewer"),
    )
    user.save()
    return jsonify(user.to_dict()), 201


@api.route("/projects", methods=["GET"])
@authenticate
def list_all_projects(current_user):
    """List all projects the user has access to."""
    projects = list_projects(user_id=current_user.id)
    return jsonify([p.to_dict() for p in projects])


@api.route("/projects", methods=["POST"])
@authenticate
@authorize(roles=["admin", "editor"])
def create_new_project(current_user):
    """Create a new project."""
    data = request.get_json()
    if not validate_project_name(data.get("name", "")):
        return jsonify({"error": "Invalid project name"}), 400

    project = create_project(
        name=data["name"],
        owner_id=current_user.id,
        description=data.get("description", ""),
    )
    return jsonify(project.to_dict()), 201


@api.route("/projects/<int:project_id>", methods=["GET"])
@authenticate
def get_single_project(current_user, project_id):
    """Get a single project by ID."""
    project = get_project(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify(project.to_dict())


@api.route("/projects/<int:project_id>", methods=["DELETE"])
@authenticate
@authorize(roles=["admin"])
def remove_project(current_user, project_id):
    """Delete a project (admin only)."""
    delete_project(project_id)
    return jsonify({"message": "Project deleted"}), 200
