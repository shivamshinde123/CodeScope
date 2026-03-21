"""Request ID middleware for distributed tracing."""

import logging
import uuid

from flask import request, g

logger = logging.getLogger("examples.middleware.request_id")


def request_id_middleware(app):
    """Assign a unique request ID to every incoming request."""

    @app.before_request
    def assign_request_id():
        # Use X-Request-ID header if provided, otherwise generate one.
        g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        logger.debug("Request ID: %s", g.request_id)

    @app.after_request
    def add_request_id_header(response):
        response.headers["X-Request-ID"] = g.get("request_id", "unknown")
        return response

    logger.info("Request ID middleware attached")
