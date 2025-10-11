"""PostgreSQL database adapter for pagination context persistence.

This module provides a database layer for storing and retrieving pagination contexts,
enabling persistence across bot restarts. It uses psycopg2 for PostgreSQL connectivity
with connection pooling and graceful degradation.

Author: Claude AI
Date: 2025-01-08
"""

import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from config.settings import settings

logger = logging.getLogger(__name__)


class PaginationDB:
    """Database adapter for pagination context persistence.

    This class manages PostgreSQL connections and provides CRUD operations
    for pagination contexts. It implements connection pooling for efficiency
    and graceful degradation when the database is unavailable.

    Attributes:
        _pool: Connection pool for PostgreSQL connections.
        _enabled: Whether database persistence is enabled.
    """

    def __init__(self) -> None:
        """Initialize the database adapter with connection pooling."""
        self._pool: pool.SimpleConnectionPool | None = None
        self._enabled: bool = settings.PAGINATION_PERSISTENCE_ENABLED

        if self._enabled:
            self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize PostgreSQL connection pool.

        Creates a connection pool with min/max connections based on configuration.
        Logs errors and disables persistence if initialization fails.
        """
        # Validate password when persistence is enabled
        if not settings.PAGINATION_DB_PASSWORD:
            logger.error("❌ PAGINATION_DB_PASSWORD must be set when persistence is enabled")
            logger.warning("⚠️  Pagination persistence disabled - password not configured")
            self._enabled = False
            self._pool = None
            return

        try:
            self._pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                host=settings.PAGINATION_DB_HOST,
                port=settings.PAGINATION_DB_PORT,
                database=settings.PAGINATION_DB_NAME,
                user=settings.PAGINATION_DB_USER,
                password=settings.PAGINATION_DB_PASSWORD,
            )
            logger.info(
                "✅ Pagination database pool initialized: %s:%s/%s",
                settings.PAGINATION_DB_HOST,
                settings.PAGINATION_DB_PORT,
                settings.PAGINATION_DB_NAME,
            )
        except Exception as e:
            logger.exception("❌ Failed to initialize pagination database pool: %s", e)
            logger.warning("⚠️  Pagination persistence disabled - using memory only")
            self._enabled = False
            self._pool = None

    @contextmanager
    def _get_connection(self):
        """Get a connection from the pool (context manager).

        Yields:
            Connection object from the pool.

        Raises:
            RuntimeError: If persistence is disabled or pool is unavailable.
        """
        if not self._enabled or not self._pool:
            raise RuntimeError("Database persistence is not available")

        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception("Database operation failed: %s", e)
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    def save_context(
        self,
        session_id: UUID,
        category: str,
        tool_name: str,
        query: str,
        products: list[dict[str, Any]],
        current_page: int = 0,
        page_size: int = 4,
    ) -> bool:
        """Save or update pagination context in the database.

        Args:
            session_id: Unique session identifier (UUID).
            category: Search category (e.g., "search_results").
            tool_name: Name of the tool that generated results.
            query: Search query string.
            products: List of product dictionaries.
            current_page: Current page number (0-indexed).
            page_size: Number of items per page.

        Returns:
            True if saved successfully, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            expires_at = datetime.now() + timedelta(hours=settings.PAGINATION_TTL_HOURS)

            with self._get_connection() as conn, conn.cursor() as cur:
                # Upsert: Insert or update if session_id + category exists
                cur.execute(
                    """
                    INSERT INTO test.pagination_contexts (
                        session_id, category, tool_name, query,
                        products, current_page, page_size, total_items, expires_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (session_id, category) DO UPDATE SET
                        tool_name = EXCLUDED.tool_name,
                        query = EXCLUDED.query,
                        products = EXCLUDED.products,
                        current_page = EXCLUDED.current_page,
                        page_size = EXCLUDED.page_size,
                        total_items = EXCLUDED.total_items,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        str(session_id),
                        category,
                        tool_name,
                        query,
                        json.dumps(products),
                        current_page,
                        page_size,
                        len(products),
                        expires_at,
                    ),
                )

            logger.debug(
                "💾 Saved pagination context: session=%s, category=%s, products=%d",
                session_id,
                category,
                len(products),
            )
            return True

        except Exception as e:
            logger.exception("Failed to save pagination context: %s", e)
            return False

    def load_context(self, session_id: UUID, category: str) -> dict[str, Any] | None:
        """Load pagination context from the database.

        Args:
            session_id: Unique session identifier (UUID).
            category: Search category to retrieve.

        Returns:
            Dictionary with context data if found and not expired, None otherwise.
            Dictionary keys: tool_name, query, products, current_page, page_size,
                           total_items, created_at, updated_at
        """
        if not self._enabled:
            return None

        try:
            with (
                self._get_connection() as conn,
                conn.cursor(cursor_factory=RealDictCursor) as cur,
            ):
                cur.execute(
                    """
                    SELECT
                        tool_name, query, products, current_page,
                        page_size, total_items, created_at, updated_at
                    FROM test.pagination_contexts
                    WHERE session_id = %s
                      AND category = %s
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    """,
                    (str(session_id), category),
                )

                row = cur.fetchone()
                if not row:
                    return None

                # Parse JSONB products back to list
                context = dict(row)
                context["products"] = (
                    json.loads(context["products"])
                    if isinstance(context["products"], str)
                    else context["products"]
                )

                logger.debug(
                    "📂 Loaded pagination context: session=%s, category=%s",
                    session_id,
                    category,
                )
                return context

        except Exception as e:
            logger.exception("Failed to load pagination context: %s", e)
            return None

    def delete_context(self, session_id: UUID, category: str) -> bool:
        """Delete pagination context from the database.

        Args:
            session_id: Unique session identifier (UUID).
            category: Search category to delete.

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            with self._get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM test.pagination_contexts
                    WHERE session_id = %s AND category = %s
                    """,
                    (str(session_id), category),
                )

                deleted_count = cur.rowcount
                logger.debug(
                    "🗑️  Deleted pagination context: session=%s, category=%s (count=%d)",
                    session_id,
                    category,
                    deleted_count,
                )
                return deleted_count > 0

        except Exception as e:
            logger.exception("Failed to delete pagination context: %s", e)
            return False

    def cleanup_expired(self) -> int:
        """Clean up expired pagination contexts.

        Returns:
            Number of contexts deleted, -1 if operation failed.
        """
        if not self._enabled:
            return 0

        try:
            with self._get_connection() as conn, conn.cursor() as cur:
                # Call the stored function
                cur.execute("SELECT test.cleanup_expired_pagination_contexts()")
                deleted_count = cur.fetchone()[0]

                if deleted_count > 0:
                    logger.info(
                        "🧹 Cleaned up %d expired pagination contexts", deleted_count
                    )
                return deleted_count

        except Exception as e:
            logger.exception("Failed to cleanup expired contexts: %s", e)
            return -1

    def cleanup_session(self, session_id: UUID) -> int:
        """Delete all pagination contexts for a specific session.

        Args:
            session_id: Unique session identifier (UUID).

        Returns:
            Number of contexts deleted, -1 if operation failed.
        """
        if not self._enabled:
            return 0

        try:
            with self._get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM test.pagination_contexts
                    WHERE session_id = %s
                    """,
                    (str(session_id),),
                )

                deleted_count = cur.rowcount
                logger.info(
                    "🧹 Cleaned up %d contexts for session %s", deleted_count, session_id
                )
                return deleted_count

        except Exception as e:
            logger.exception("Failed to cleanup session contexts: %s", e)
            return -1

    def close(self) -> None:
        """Close all connections in the pool.

        Should be called when shutting down the application.
        """
        if self._pool:
            self._pool.closeall()
            logger.info("🔌 Pagination database pool closed")

    @property
    def is_enabled(self) -> bool:
        """Check if database persistence is enabled and available.

        Returns:
            True if persistence is enabled and working, False otherwise.
        """
        return self._enabled and self._pool is not None
