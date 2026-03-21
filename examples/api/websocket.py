"""WebSocket handler for real-time project updates."""

import logging
from typing import Any

logger = logging.getLogger("examples.api.websocket")

# Connected clients registry.
_clients: dict[str, Any] = {}


def on_connect(client_id: str, user_id: int) -> None:
    """Register a new WebSocket client."""
    _clients[client_id] = {"user_id": user_id, "subscriptions": set()}
    logger.info("Client %s connected (user %d)", client_id, user_id)


def on_disconnect(client_id: str) -> None:
    """Remove a WebSocket client."""
    _clients.pop(client_id, None)
    logger.info("Client %s disconnected", client_id)


def subscribe(client_id: str, project_id: int) -> None:
    """Subscribe a client to project updates."""
    if client_id in _clients:
        _clients[client_id]["subscriptions"].add(project_id)


def broadcast_project_update(project_id: int, event: str, data: dict) -> None:
    """Send an update to all clients subscribed to a project."""
    message = {"project_id": project_id, "event": event, "data": data}
    for client_id, info in _clients.items():
        if project_id in info["subscriptions"]:
            logger.debug("Sending to %s: %s", client_id, event)
            # In a real implementation, send via WebSocket here.
