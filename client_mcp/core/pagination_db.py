"""PostgreSQL database adapter for pagination context persistence.

This module provides a database layer for storing and retrieving pagination contexts,
enabling persistence across bot restarts. It uses psycopg2 for PostgreSQL connectivity
with connection pooling and graceful degradation.

IMPORTANT: Schema matches SQL/01_ddl/utils/01_pagination_contexts.sql
- Uses dynamic schema from PAGINATION_SCHEMA_NAME setting
- Maps Python fields to SQL columns correctly

Author: Claude AI
Date: 2025-01-19 (Refactored to match SQL schema)
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
        _schema: PostgreSQL schema name (default: 'test').
    """

    def __init__(self) -> None:
        """Initialize the database adapter with connection pooling."""
        self._pool: pool.SimpleConnectionPool | None = None
        self._enabled: bool = settings.PAGINATION_PERSISTENCE_ENABLED
        self._schema: str = getattr(settings, 'PAGINATION_SCHEMA_NAME', 'test')

        if self._enabled:
            self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize PostgreSQL connection pool.

        Creates a connection pool with min/max connections based on configuration.
        Logs errors and disables persistence if initialization fails.
        """
        # Validate password when persistence is enabled
        if not settings.PAGINATION_DB_PASSWORD:
            logger.error(
                "❌ PAGINATION_DB_PASSWORD must be set when persistence is enabled"
            )
            logger.warning(
                "⚠️  Pagination persistence disabled - password not configured"
            )
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
                "✅ Pagination database pool initialized: %s:%s/%s (schema: %s)",
                settings.PAGINATION_DB_HOST,
                settings.PAGINATION_DB_PORT,
                settings.PAGINATION_DB_NAME,
                self._schema,
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
            category: Search category (e.g., "search_results") → maps to context_type.
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

            # Generate context_name from session_id + category
            context_name = f"{session_id}_{category}"

            # Calculate offset from current_page
            last_offset = current_page * page_size

            # Build query_params JSONB
            query_params = {
                "tool_name": tool_name,
                "query": query,
                "products": products,
            }

            with self._get_connection() as conn, conn.cursor() as cur:
                # Upsert: Insert or update if context_name exists
                # Note: Always use "custom" as context_type to satisfy CHECK constraint
                cur.execute(
                    f"""
                    INSERT INTO {self._schema}.pagination_contexts (
                        context_name, context_type, session_id,
                        last_offset, last_limit, total_records,
                        has_more, query_params, expires_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (context_name) DO UPDATE SET
                        last_offset = EXCLUDED.last_offset,
                        last_limit = EXCLUDED.last_limit,
                        total_records = EXCLUDED.total_records,
                        has_more = EXCLUDED.has_more,
                        query_params = EXCLUDED.query_params,
                        expires_at = EXCLUDED.expires_at,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        context_name,
                        "custom",  # context_type (use "custom" to satisfy CHECK constraint)
                        str(session_id),
                        last_offset,
                        page_size,  # last_limit
                        len(products),  # total_records
                        True,  # has_more (assume true for now)
                        json.dumps(query_params),
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
            category: Search category to retrieve (maps to context_type).

        Returns:
            Dictionary with context data if found and not expired, None otherwise.
            Dictionary keys: tool_name, query, products, current_page, page_size,
                           total_items, created_at, updated_at
        """
        if not self._enabled:
            return None

        try:
            context_name = f"{session_id}_{category}"

            with (
                self._get_connection() as conn,
                conn.cursor(cursor_factory=RealDictCursor) as cur,
            ):
                cur.execute(
                    f"""
                    SELECT
                        last_offset, last_limit, total_records,
                        query_params, created_at, updated_at
                    FROM {self._schema}.pagination_contexts
                    WHERE context_name = %s
                      AND session_id = %s
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    """,
                    (context_name, str(session_id)),
                )

                row = cur.fetchone()
                if not row:
                    return None

                # Parse query_params JSONB and reconstruct original format
                row_dict = dict(row)
                query_params = row_dict.get("query_params", {})

                # Calculate current_page from last_offset and last_limit
                last_offset = row_dict.get("last_offset", 0)
                last_limit = row_dict.get("last_limit", 4)
                current_page = last_offset // last_limit if last_limit > 0 else 0

                # Build response in expected format
                context = {
                    "tool_name": query_params.get("tool_name", ""),
                    "query": query_params.get("query", ""),
                    "products": query_params.get("products", []),
                    "current_page": current_page,
                    "page_size": last_limit,
                    "total_items": row_dict.get("total_records", 0),
                    "created_at": row_dict.get("created_at"),
                    "updated_at": row_dict.get("updated_at"),
                }

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
            category: Search category to delete (maps to context_type).

        Returns:
            True if deleted successfully, False otherwise.
        """
        if not self._enabled:
            return False

        try:
            context_name = f"{session_id}_{category}"

            with self._get_connection() as conn, conn.cursor() as cur:
                cur.execute(
                    f"""
                    DELETE FROM {self._schema}.pagination_contexts
                    WHERE context_name = %s AND session_id = %s
                    """,
                    (context_name, str(session_id)),
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
                # Delete expired contexts directly
                cur.execute(
                    f"""
                    DELETE FROM {self._schema}.pagination_contexts
                    WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP
                    """
                )
                deleted_count = cur.rowcount

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
                    f"""
                    DELETE FROM {self._schema}.pagination_contexts
                    WHERE session_id = %s
                    """,
                    (str(session_id),),
                )

                deleted_count = cur.rowcount
                logger.info(
                    "🧹 Cleaned up %d contexts for session %s",
                    deleted_count,
                    session_id,
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
