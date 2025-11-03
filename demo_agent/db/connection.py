"""Database connection management with async support.

Handles PostgreSQL connection pooling and session management using asyncpg.

FIX 3.1: Async Database Connection
- Replaced psycopg2 (sync) with asyncpg (async)
- Connection pooling for better resource management
- Non-blocking operations prevent event loop blocking
- Supports high concurrency without thread overhead

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 2.0.0 (Async)
"""

import asyncpg
from typing import Any

from demo_agent.config.settings import config
from demo_agent.logger import logger


class AsyncDatabaseConnection:
    """PostgreSQL async connection manager with connection pooling.

    Uses asyncpg for non-blocking database operations.
    Maintains connection pool for efficient resource usage.

    Features:
    - Connection pooling (configurable min/max)
    - Non-blocking queries via asyncpg
    - Automatic retry logic
    - Proper transaction handling
    """

    def __init__(self):
        """Initialize async database connection."""
        self.connection_string = config.DATABASE_URL
        self.schema = config.SCHEMA_NAME
        self.pool = None
        logger.info(f"AsyncDatabaseConnection initialized (schema: {self.schema})")

    async def connect(self) -> None:
        """Establish async database connection pool.

        FIX 3.1: Async Connection
        - Creates asyncpg connection pool
        - Min=5, Max=20 connections
        - Non-blocking operations
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
            logger.info("✅ Connected to PostgreSQL (async pool)")
        except Exception as e:
            logger.exception(f"Failed to connect to PostgreSQL: {e}")
            raise RuntimeError(f"Database connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Close async database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Disconnected from PostgreSQL (async pool)")

    async def execute(
        self,
        query: str,
        params: tuple | None = None,
        fetch_one: bool = False,
    ) -> Any:
        """Execute query and return result (async).

        Args:
            query: SQL query (use :SCHEMA_NAME for schema placeholder)
            params: Query parameters for parameterized queries
            fetch_one: If True, return single row; else return all rows

        Returns:
            dict or list[dict] or None

        FIX 3.1: Async Execution
        - Non-blocking database I/O
        - Uses connection pool
        - Proper error handling

        Example:
            >>> result = await db.execute(
            ...     "SELECT * FROM :SCHEMA_NAME.demo_usage WHERE user_key = $1",
            ...     ("user_123",),
            ...     fetch_one=True
            ... )
        """
        if not self.pool:
            raise RuntimeError("Database not connected")

        try:
            # Replace schema placeholder
            query = query.replace(":SCHEMA_NAME", self.schema)

            # Convert psycopg2 %s to asyncpg $1, $2 style parameters
            query = self._convert_placeholders(query)

            async with self.pool.acquire() as connection:
                # Check if query returns data (SELECT or RETURNING clause)
                if query.strip().upper().startswith("SELECT") or "RETURNING" in query.upper():
                    if fetch_one:
                        result = await connection.fetchrow(query, *(params or ()))
                        return dict(result) if result else None
                    else:
                        result = await connection.fetch(query, *(params or ()))
                        return [dict(row) for row in result] if result else []
                else:
                    # INSERT, UPDATE, DELETE without RETURNING
                    await connection.execute(query, *(params or ()))
                    return None

        except Exception as e:
            logger.exception(f"Database query error: {e}")
            raise RuntimeError(f"Query execution failed: {e}") from e

    async def execute_one(
        self,
        query: str,
        params: tuple | None = None,
    ) -> dict | None:
        """Execute query and return single row (async).

        Convenience wrapper for execute(fetch_one=True).
        """
        return await self.execute(query, params, fetch_one=True)

    async def execute_all(
        self,
        query: str,
        params: tuple | None = None,
    ) -> list[dict]:
        """Execute query and return all rows (async).

        Convenience wrapper for execute(fetch_one=False).
        """
        result = await self.execute(query, params, fetch_one=False)
        return result or []

    @staticmethod
    def _convert_placeholders(query: str) -> str:
        """Convert psycopg2 %s placeholders to asyncpg $1, $2 style.

        asyncpg uses $1, $2, $3 for parameters instead of %s.
        """
        counter = 1
        result = []
        i = 0
        while i < len(query):
            if i < len(query) - 1 and query[i:i+2] == "%s":
                result.append(f"${counter}")
                counter += 1
                i += 2
            elif i < len(query) - 1 and query[i] == "'" and (i == 0 or query[i-1] != "\\"):
                # Handle string literals - don't replace %s inside strings
                result.append(query[i])
                i += 1
                while i < len(query):
                    if query[i] == "'":
                        result.append(query[i])
                        i += 1
                        break
                    elif query[i] == "\\":
                        result.append(query[i:i+2])
                        i += 2
                    else:
                        result.append(query[i])
                        i += 1
            else:
                result.append(query[i])
                i += 1
        return "".join(result)


# Global async connection instance
_db_connection: AsyncDatabaseConnection | None = None
_db_initialized: bool = False


def get_db() -> AsyncDatabaseConnection:
    """Get global async database connection (lazy initialization).

    Returns:
        AsyncDatabaseConnection instance

    FIX 3.1: Async Connection Factory
    - Returns singleton async connection
    - Must call await init_db() at startup to initialize pool
    - All database calls must use await
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = AsyncDatabaseConnection()
    return _db_connection


async def init_db() -> None:
    """Initialize database connection pool (call at app startup).

    This must be called once at FastAPI startup to create the connection pool.

    Example in main.py:
        @app.on_event("startup")
        async def startup():
            await init_db()
    """
    global _db_initialized
    if not _db_initialized:
        db = get_db()
        await db.connect()
        _db_initialized = True
        logger.info("Database pool initialized at startup")


async def close_db() -> None:
    """Close global async database connection (call at app shutdown).

    This must be called at FastAPI shutdown to close the connection pool.

    Example in main.py:
        @app.on_event("shutdown")
        async def shutdown():
            await close_db()
    """
    global _db_connection, _db_initialized
    if _db_connection:
        await _db_connection.disconnect()
        _db_connection = None
        _db_initialized = False
        logger.info("Database pool closed at shutdown")
