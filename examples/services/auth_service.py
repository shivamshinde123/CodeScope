"""Authentication and authorization service."""

import hashlib
import hmac
import logging
import os
import time
from functools import wraps
from typing import Optional

from flask import request, jsonify

from examples.models.user import User

logger = logging.getLogger("examples.services.auth")

# Secret key for HMAC token signing.
SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_SECONDS = 7200  # 2 hours (extended from 1h for better UX)


def generate_token(user: User) -> str:
    """Generate an HMAC-signed authentication token for a user.

    The token format is: ``{user_id}:{expiry_timestamp}:{signature}``
    """
    expiry = int(time.time()) + TOKEN_TTL_SECONDS
    payload = f"{user.id}:{expiry}"
    signature = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}:{signature}"


def verify_token(token: str) -> Optional[User]:
    """Verify a token and return the associated user, or None."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None

        user_id, expiry, signature = int(parts[0]), int(parts[1]), parts[2]

        # Check expiry.
        if time.time() > expiry:
            logger.debug("Token expired for user %d", user_id)
            return None

        # Verify HMAC signature.
        payload = f"{user_id}:{expiry}"
        expected = hmac.new(
            SECRET_KEY.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            logger.warning("Invalid token signature for user %d", user_id)
            return None

        return User.find_by_id(user_id)

    except (ValueError, TypeError) as exc:
        logger.warning("Malformed token: %s", exc)
        return None


def authenticate(f):
    """Decorator that requires a valid Bearer token."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[len("Bearer "):]
        user = verify_token(token)
        if user is None:
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(user, *args, **kwargs)

    return decorated


def authorize(roles: list[str]):
    """Decorator that restricts access to users with specific roles."""

    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(current_user, *args, **kwargs)

        return decorated

    return decorator
