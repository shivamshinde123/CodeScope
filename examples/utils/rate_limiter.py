"""Simple in-memory rate limiter for API endpoints."""

import time
import logging
from collections import defaultdict
from functools import wraps

from flask import request, jsonify

logger = logging.getLogger("examples.utils.rate_limiter")

# In-memory store: maps client IP → list of request timestamps.
_request_log: dict[str, list[float]] = defaultdict(list)


def rate_limit(max_calls: int = 60, period: int = 60):
    """Decorator that rate-limits an endpoint by client IP.

    Args:
        max_calls: Maximum number of requests allowed within the period.
        period: Time window in seconds.
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            client_ip = request.remote_addr or "unknown"
            now = time.time()
            window_start = now - period

            # Prune timestamps outside the current window.
            _request_log[client_ip] = [
                ts for ts in _request_log[client_ip] if ts > window_start
            ]

            if len(_request_log[client_ip]) >= max_calls:
                logger.warning(
                    "Rate limit exceeded for %s on %s",
                    client_ip,
                    request.path,
                )
                return jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": int(period - (now - _request_log[client_ip][0])),
                }), 429

            _request_log[client_ip].append(now)
            return f(*args, **kwargs)

        return decorated

    return decorator


def clear_rate_limits() -> None:
    """Reset all rate limit counters (useful for testing)."""
    _request_log.clear()
