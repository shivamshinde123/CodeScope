"""CORS middleware for cross-origin request handling."""

import logging

logger = logging.getLogger("examples.middleware.cors")

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://app.example.com",
]


def cors_middleware(app):
    """Attach CORS headers to all responses."""

    @app.after_request
    def add_cors_headers(response):
        origin = response.headers.get("Origin", "")
        if origin in ALLOWED_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGINS[0]

        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "3600"
        return response

    logger.info("CORS middleware attached")
