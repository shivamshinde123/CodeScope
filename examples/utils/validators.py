"""Input validation utilities."""

import re


def validate_email(email: str) -> bool:
    """Check if the email address has a valid format.

    Uses a simple regex — not RFC 5322 compliant, but good enough
    for most practical purposes.
    """
    if not email or len(email) > 254:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_project_name(name: str) -> bool:
    """Validate a project name.

    Rules:
        - Must be between 1 and 100 characters.
        - Must start with a letter or digit.
        - May contain letters, digits, hyphens, and underscores.
    """
    if not name or len(name) > 100:
        return False
    pattern = r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
    return bool(re.match(pattern, name))


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength.

    Returns a tuple of (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    return True, ""
