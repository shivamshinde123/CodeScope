"""Request/response middleware for logging and error handling."""

import logging
import time
from functools import wraps

from flask import request, jsonify, g

logger = logging.getLogger("examples.api.middleware")


def request_logger(app):
    """Attach request logging hooks to the Flask app."""

    @app.before_request
    def log_request_start():
        g.start_time = time.time()
        logger.info(
            "REQUEST %s %s from %s",
            request.method,
            request.path,
            request.remote_addr,
        )

    @app.after_request
    def log_request_end(response):
        duration = time.time() - g.get("start_time", time.time())
        logger.info(
            "RESPONSE %s %s → %d (%.3fs)",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        return response


def error_handler(app):
    """Register global error handlers."""

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "details": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error("Internal server error: %s", error)
        return jsonify({"error": "Internal server error"}), 500
