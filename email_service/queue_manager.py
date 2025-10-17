"""Email Queue Manager - PostgreSQL operations wrapper.

Handles all database operations for the email queue system:
- Enqueueing new emails (bookings, reminders)
- Polling pending emails for worker
- Updating email status (sent/failed)
- Retry logic with exponential backoff

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from email_service.config import settings
from email_service.models import EmailCreateRequest, EmailRecord, EmailStatus, EmailType


class EmailQueueManager:
    """Manages email queue operations with PostgreSQL.

    Uses connection pooling for efficient database access.
    Thread-safe for multi-worker deployments.
    """

    def __init__(self) -> None:
        """Initialize connection pool."""
        self._pool: pool.SimpleConnectionPool | None = None
        self._init_pool()

    def _init_pool(self) -> None:
        """Initialize PostgreSQL connection pool.

        Raises:
            psycopg2.Error: If connection fails.
        """
        self._pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=settings.DATABASE_URL,
            cursor_factory=RealDictCursor,
        )

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get connection from pool.

        Returns:
            Database connection.

        Raises:
            RuntimeError: If pool not initialized.
        """
        if not self._pool:
            raise RuntimeError("Connection pool not initialized")
        return self._pool.getconn()

    def _return_connection(self, conn: psycopg2.extensions.connection) -> None:
        """Return connection to pool."""
        if self._pool:
            self._pool.putconn(conn)

    def enqueue_email(
        self,
        email_type: EmailType,
        recipient_email: str,
        recipient_name: str | None,
        subject: str,
        body_html: str,
        body_text: str | None = None,
        booking_id: int | None = None,
        template_context: dict[str, Any] | None = None,
        scheduled_for: datetime | None = None,
        priority: int = 5,
    ) -> int:
        """Enqueue a new email for delivery.

        Args:
            email_type: Type of email (booking_created, reminder_24h, etc.)
            recipient_email: Recipient email address.
            recipient_name: Recipient full name.
            subject: Email subject line.
            body_html: HTML email body.
            body_text: Plain text fallback (optional).
            booking_id: Related booking ID (optional).
            template_context: JSON context for template (optional).
            scheduled_for: When to send (default: now).
            priority: 1=highest, 10=lowest (default: 5).

        Returns:
            Created email ID.

        Raises:
            psycopg2.Error: If database operation fails.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Convert template_context dict to JSON string for PostgreSQL
                # DEBUG: Log what we receive
                import logging
                logger_debug = logging.getLogger("email_queue_mgr")
                logger_debug.warning(f"🔍 enqueue_email template_context: {bool(template_context)}, keys: {list(template_context.keys()) if isinstance(template_context, dict) else type(template_context).__name__}")

                template_json = json.dumps(template_context) if template_context else None
                logger_debug.warning(f"🔍 template_json bytes: {len(template_json) if template_json else 0}")

                # Use SQL function from create_email_queue.sql
                cur.execute(
                    f"""
                    SELECT {settings.SCHEMA_NAME}.enqueue_email(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        email_type.value,
                        recipient_email,
                        recipient_name,
                        subject,
                        body_html,
                        body_text,
                        booking_id,
                        template_json,  # ✅ FIXED: Converted to JSON string
                        scheduled_for or datetime.now(),
                        priority,
                    ),
                )
                email_id = cur.fetchone()["enqueue_email"]
                conn.commit()
                return email_id
        except Exception as exc:
            conn.rollback()
            raise RuntimeError(f"Failed to enqueue email: {exc}") from exc
        finally:
            self._return_connection(conn)

    def get_pending_emails(self, limit: int = 50) -> list[EmailRecord]:
        """Get pending emails ready for delivery.

        Uses FOR UPDATE SKIP LOCKED to prevent race conditions.
        Deserializes template_context from JSON string to dict for template rendering.

        Args:
            limit: Max emails to retrieve (default: 50).

        Returns:
            List of pending email records.

        Raises:
            psycopg2.Error: If database operation fails.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Use SQL function from create_email_queue.sql
                cur.execute(
                    f"SELECT * FROM {settings.SCHEMA_NAME}.get_pending_emails(%s)",
                    (limit,),
                )
                rows = cur.fetchall()
                conn.commit()

                # Convert to Pydantic models
                import logging
                logger_debug = logging.getLogger("email_queue_mgr")

                email_records = []
                for row in rows:
                    # Convert row dict to regular dict to modify
                    row_dict = dict(row)

                    # CRITICAL FIX: Deserialize template_context from JSON string to dict
                    # PostgreSQL stores template_context as JSONB, but psycopg2 returns it as
                    # a string when using regular DictCursor (not RealDictCursor with json support)
                    template_context_raw = row_dict.get("template_context")
                    logger_debug.warning(f"🔍 get_pending_emails email_id={row_dict.get('id')}, template_context_type={type(template_context_raw).__name__}, value_exists={template_context_raw is not None}")

                    if template_context_raw:
                        if isinstance(template_context_raw, str):
                            # Deserialize JSON string to dict
                            logger_debug.warning(f"   → Deserializing JSON string: {len(template_context_raw)} bytes")
                            row_dict["template_context"] = json.loads(template_context_raw)
                        else:
                            # Already a dict (RealDictCursor with json support)
                            logger_debug.warning(f"   → Already a dict with {len(template_context_raw) if isinstance(template_context_raw, dict) else 'N/A'} keys")
                    else:
                        logger_debug.warning(f"   → Setting template_context to None")
                        row_dict["template_context"] = None

                    logger_debug.warning(f"   → Final template_context before EmailRecord: {type(row_dict.get('template_context')).__name__}")

                    # Create EmailRecord with deserialized template_context
                    email_records.append(
                        EmailRecord(
                            **row_dict,
                            created_at=datetime.now(),  # Placeholder
                            updated_at=datetime.now(),  # Placeholder
                        )
                    )

                return email_records
        finally:
            self._return_connection(conn)

    def update_email_status(
        self,
        email_id: int,
        status: EmailStatus,
        error: str | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        """Update email delivery status.

        Args:
            email_id: Email ID to update.
            status: New status (sent, failed, processing).
            error: Error message if failed (optional).
            sent_at: Delivery timestamp if sent (optional).

        Raises:
            psycopg2.Error: If database operation fails.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {settings.SCHEMA_NAME}.update_email_status(
                        %s, %s, %s, %s
                    )
                    """,
                    (email_id, status.value, error, sent_at),
                )
                conn.commit()
        finally:
            self._return_connection(conn)

    def retry_email(
        self, email_id: int, error: str, backoff_seconds: int = 300
    ) -> None:
        """Retry failed email with exponential backoff.

        Args:
            email_id: Email ID to retry.
            error: Error message from failed attempt.
            backoff_seconds: Initial backoff (default: 300 = 5 min).

        Raises:
            psycopg2.Error: If database operation fails.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {settings.SCHEMA_NAME}.retry_email(
                        %s, %s, %s
                    )
                    """,
                    (email_id, error, backoff_seconds),
                )
                conn.commit()
        finally:
            self._return_connection(conn)

    def get_email_by_id(self, email_id: int) -> EmailRecord | None:
        """Get email record by ID.

        Args:
            email_id: Email ID to retrieve.

        Returns:
            Email record or None if not found.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT * FROM {settings.SCHEMA_NAME}.email_queue
                    WHERE id = %s
                    """,
                    (email_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None

                return EmailRecord(**row)
        finally:
            self._return_connection(conn)

    def cleanup_old_emails(self, days_to_keep: int = 90) -> int:
        """Cleanup old sent/failed emails for maintenance.

        Args:
            days_to_keep: Keep emails from last N days (default: 90).

        Returns:
            Number of deleted emails.

        Raises:
            psycopg2.Error: If database operation fails.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT {settings.SCHEMA_NAME}.cleanup_old_emails(%s)
                    """,
                    (days_to_keep,),
                )
                deleted_count = cur.fetchone()["cleanup_old_emails"]
                conn.commit()
                return deleted_count
        finally:
            self._return_connection(conn)

    def close(self) -> None:
        """Close all connections in pool."""
        if self._pool:
            self._pool.closeall()
