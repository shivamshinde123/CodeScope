"""Application configuration loaded from environment variables."""

import os


class Settings:
    """Central configuration container."""

    # Server
    HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("APP_PORT", "8000"))
    DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///app.db")

    # Auth
    SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "dev-secret-change-me")
    TOKEN_TTL: int = int(os.getenv("TOKEN_TTL", "7200"))

    # Rate limiting
    RATE_LIMIT_MAX: int = int(os.getenv("RATE_LIMIT_MAX", "60"))
    RATE_LIMIT_PERIOD: int = int(os.getenv("RATE_LIMIT_PERIOD", "60"))

    # Claude / AI
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    # Dashboard
    DASHBOARD_MAX_WIDGETS: int = int(os.getenv("DASHBOARD_MAX_WIDGETS", "20"))
    DASHBOARD_REFRESH_INTERVAL: int = int(os.getenv("DASHBOARD_REFRESH_SEC", "30"))

    # Audit logging
    AUDIT_LOG_ENABLED: bool = os.getenv("AUDIT_LOG_ENABLED", "true").lower() == "true"
    AUDIT_LOG_RETENTION_DAYS: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))

    # Database pool
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "5"))

    # CORS
    CORS_ALLOWED_ORIGINS: list[str] = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")


settings = Settings()
