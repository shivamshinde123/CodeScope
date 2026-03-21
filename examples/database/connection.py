"""Database connection manager with connection pooling."""

import logging
from typing import Optional

logger = logging.getLogger("examples.database.connection")


class ConnectionPool:
    """Simple connection pool for database connections."""

    def __init__(self, database_url: str, pool_size: int = 5):
        self.database_url = database_url
        self.pool_size = pool_size
        self._connections: list = []
        self._available: list = []
        logger.info("Connection pool initialized (size=%d)", pool_size)

    def acquire(self):
        """Acquire a connection from the pool."""
        if self._available:
            conn = self._available.pop()
            logger.debug("Reusing pooled connection")
            return conn

        if len(self._connections) < self.pool_size:
            conn = {"url": self.database_url, "id": len(self._connections)}
            self._connections.append(conn)
            logger.debug("Created new connection (total=%d)", len(self._connections))
            return conn

        raise RuntimeError("Connection pool exhausted")

    def release(self, conn):
        """Return a connection to the pool."""
        self._available.append(conn)

    def close_all(self):
        """Close all connections."""
        self._connections.clear()
        self._available.clear()
        logger.info("All connections closed")


_pool: Optional[ConnectionPool] = None


def get_pool(database_url: str = "sqlite:///app.db") -> ConnectionPool:
    """Get or create the global connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(database_url)
    return _pool
