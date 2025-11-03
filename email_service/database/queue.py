"""Email queue manager for PostgreSQL operations.

Handles all database operations for the email queue system including
enqueueing, retrieving, status updates, and retry logic.

Author: Lab01-MCP Team
Created: 2025-10-18
Version: 1.0.0
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from email_service.config import EmailConfig
from email_service.core.exceptions import EmailQueueError
from email_service.core.logger import get_logger
from email_service.models.email import EmailRecord, EmailStatus, EmailType
from email_service.observability.metrics import get_metrics_collector
from email_service.observability.structured_logger import get_structured_logger

logger = get_logger(__name__)


class EmailQueueManager:
    """Manages email queue operations with PostgreSQL.

    Uses connection pooling for efficient database access. Thread-safe
    for multi-worker deployments.

    Attributes:
        config: Email service configuration.

    Example:
        queue = EmailQueueManager()

        # Enqueue an email
        email_id = queue.enqueue_email(
            email_type=EmailType.BOOKING_CREATED,
            recipient_email="user@example.com",
            recipient_name="John Doe",
            subject="Booking Confirmed",
            body_html="<h1>Confirmed</h1>",
        )

        # Get pending emails
        pending = queue.get_pending_emails(limit=50)
        for email in pending:
            print(f"Email {email.id} to {email.recipient_email}")

        # Mark as sent
        queue.update_email_status(email_id, EmailStatus.SENT)
    """

    def __init__(self, config: EmailConfig | None = None) -> None:
        """Initialize queue manager with connection pool.

        Args:
            config: Email service configuration (uses global if None).

        Raises:
            EmailQueueError: If connection pool initialization fails.
        """
        # Initialize observability (OPCIÓN 6)
        self.logger = get_structured_logger(__name__)
        self.metrics = get_metrics_collector()

        self.config = config or EmailConfig()
        self._pool: pool.SimpleConnectionPool | None = None

        try:
            self._init_pool()
            logger.info("✅ Email Queue Manager initialized")
            self.logger.info("Queue manager initialized", schema=self.config.SCHEMA_NAME)
        except Exception as e:
            logger.error(f"❌ Failed to initialize queue manager: {e}")
            raise EmailQueueError(f"Connection pool initialization failed: {e}") from e

    def _init_pool(self) -> None:
        """Initialize PostgreSQL connection pool.

        Raises:
            psycopg2.Error: If connection pool creation fails.
        """
        logger.debug("🔧 Initializing PostgreSQL connection pool...")
        self._pool = pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=self.config.DATABASE_URL,
            cursor_factory=RealDictCursor,
        )

    def _get_connection(self) -> psycopg2.extensions.connection:
        """Get connection from pool.

        Returns:
            Database connection from pool.

        Raises:
            EmailQueueError: If pool not initialized or connection unavailable.
        """
        if not self._pool:
            raise EmailQueueError("Connection pool not initialized")
        return self._pool.getconn()

    def _return_connection(self, conn: psycopg2.extensions.connection) -> None:
        """Return connection to pool.

        Args:
            conn: Database connection to return.
        """
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
            email_type: Email category (booking_created, reminder_24h, etc).
            recipient_email: Recipient email address.
            recipient_name: Recipient full name (optional).
            subject: Email subject line.
            body_html: HTML-formatted email body.
            body_text: Plain-text email body (optional).
            booking_id: Related booking ID (optional).
            template_context: JSON context for template rendering (optional).
            scheduled_for: When to send email (default: now).
            priority: Priority level 1-10 (1=highest, default=5).

        Returns:
            Created email record ID.

        Raises:
            EmailQueueError: If database operation fails.

        Example:
            email_id = queue.enqueue_email(
                email_type=EmailType.BOOKING_CREATED,
                recipient_email="user@example.com",
                recipient_name="John",
                subject="Booking Confirmed",
                body_html="<h1>Confirmed</h1>",
                template_context={"booking_id": 123}
            )
        """
        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_enqueue", tags={"email_type": email_type.value}):
                with conn.cursor() as cur:
                    # Convert template_context to JSON string
                    template_json = (
                        json.dumps(template_context) if template_context else None
                    )

                    logger.debug(
                        f"📝 Enqueueing email: type={email_type.value}, "
                        f"to={recipient_email}, priority={priority}"
                    )
                    self.logger.debug(
                        "Enqueueing email",
                        email_type=email_type.value,
                        recipient=recipient_email,
                        priority=priority
                    )

                    # Call PostgreSQL function
                    cur.execute(
                        f"""
                        SELECT {self.config.SCHEMA_NAME}.enqueue_email(
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
                            template_json,
                            scheduled_for or datetime.now(),
                            priority,
                        ),
                    )
                    email_id = cur.fetchone()["enqueue_email"]
                    conn.commit()

                    logger.info(f"✅ Email #{email_id} enqueued successfully")
                    self.logger.info("Email enqueued", email_id=email_id, recipient=recipient_email)
                    self.metrics.increment_counter("queue_enqueued")
                    return email_id

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to enqueue email: {e}", exc_info=True)
            self.logger.exception("Email enqueue failed", recipient=recipient_email)
            self.metrics.increment_counter("queue_enqueue_errors")
            raise EmailQueueError(f"Failed to enqueue email: {e}") from e
        finally:
            self._return_connection(conn)

    def get_pending_emails(self, limit: int = 50) -> list[EmailRecord]:
        """Get pending emails ready for delivery.

        Uses FOR UPDATE SKIP LOCKED to prevent race conditions.
        Deserializes template_context from JSON for template rendering.

        Args:
            limit: Max emails to retrieve (default: 50, max: 1000).

        Returns:
            List of pending email records.

        Raises:
            EmailQueueError: If database operation fails.

        Example:
            pending = queue.get_pending_emails(limit=50)
            for email in pending:
                if email.template_context:
                    # Render template
                    html = renderer.render_html(email.type, email.template_context)
        """
        # Clamp limit
        limit = min(max(limit, 1), 1000)

        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_query", tags={"operation": "get_pending"}):
                with conn.cursor() as cur:
                    logger.debug(f"🔍 Fetching up to {limit} pending emails...")
                    self.logger.debug("Fetching pending emails", limit=limit)

                    # Call PostgreSQL function
                    cur.execute(
                        f"SELECT * FROM {self.config.SCHEMA_NAME}.get_pending_emails(%s)",
                        (limit,),
                    )
                    rows = cur.fetchall()
                    conn.commit()

                    if not rows:
                        logger.debug("📭 No pending emails in queue")
                        self.metrics.set_gauge("queue_size_pending", 0)
                        return []

                    # Convert rows to EmailRecord models
                    email_records = []
                    for row in rows:
                        row_dict = dict(row)

                        # Deserialize template_context from JSON string to dict
                        template_context_raw = row_dict.get("template_context")
                        if template_context_raw:
                            if isinstance(template_context_raw, str):
                                row_dict["template_context"] = json.loads(
                                    template_context_raw
                                )
                            # else: already a dict

                        # Create EmailRecord with deserialized data
                        email_records.append(
                            EmailRecord(
                                **row_dict,
                                created_at=row_dict.get("created_at", datetime.now()),
                                updated_at=row_dict.get("updated_at", datetime.now()),
                            )
                        )

                    logger.info(f"📬 Retrieved {len(email_records)} pending emails")
                    self.logger.info("Pending emails retrieved", count=len(email_records))
                    self.metrics.increment_counter("queue_fetches")
                    self.metrics.set_gauge("queue_size_pending", len(email_records))
                    return email_records

        except Exception as e:
            logger.error(f"❌ Failed to get pending emails: {e}", exc_info=True)
            self.logger.exception("Failed to get pending emails")
            self.metrics.increment_counter("queue_query_errors")
            raise EmailQueueError(f"Failed to retrieve pending emails: {e}") from e
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
            EmailQueueError: If database operation fails.

        Example:
            queue.update_email_status(123, EmailStatus.SENT)
            queue.update_email_status(
                456,
                EmailStatus.FAILED,
                error="Connection timeout"
            )
        """
        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_update", tags={"status": status.value}):
                with conn.cursor() as cur:
                    logger.debug(f"📊 Updating email #{email_id} status to {status.value}")
                    self.logger.debug(
                        "Updating email status",
                        email_id=email_id,
                        status=status.value,
                        has_error=error is not None
                    )

                    cur.execute(
                        f"""
                        SELECT {self.config.SCHEMA_NAME}.update_email_status(
                            %s, %s, %s, %s
                        )
                        """,
                        (email_id, status.value, error, sent_at),
                    )
                    conn.commit()

                    logger.info(f"✅ Email #{email_id} status updated to {status.value}")
                    self.logger.info("Email status updated", email_id=email_id, status=status.value)
                    self.metrics.increment_counter("queue_updates")

        except Exception as e:
            conn.rollback()
            logger.error(
                f"❌ Failed to update email #{email_id} status: {e}",
                exc_info=True,
            )
            self.logger.exception("Email status update failed", email_id=email_id)
            self.metrics.increment_counter("queue_update_errors")
            raise EmailQueueError(f"Failed to update email status: {e}") from e
        finally:
            self._return_connection(conn)

    def retry_email(
        self, email_id: int, error: str, backoff_seconds: int = 300
    ) -> None:
        """Retry failed email with exponential backoff.

        Args:
            email_id: Email ID to retry.
            error: Error message from failed attempt.
            backoff_seconds: Initial backoff duration (default: 300s = 5min).

        Raises:
            EmailQueueError: If database operation fails.

        Example:
            queue.retry_email(
                email_id=123,
                error="SMTP timeout",
                backoff_seconds=600  # 10 minutes
            )
        """
        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_retry", tags={"email_id": str(email_id)}):
                with conn.cursor() as cur:
                    logger.debug(
                        f"🔄 Scheduling retry for email #{email_id}, "
                        f"backoff={backoff_seconds}s"
                    )
                    self.logger.debug(
                        "Scheduling email retry",
                        email_id=email_id,
                        backoff_seconds=backoff_seconds
                    )

                    cur.execute(
                        f"""
                        SELECT {self.config.SCHEMA_NAME}.retry_email(
                            %s, %s, %s
                        )
                        """,
                        (email_id, error, backoff_seconds),
                    )
                    conn.commit()

                    logger.info(f"✅ Email #{email_id} scheduled for retry")
                    self.logger.info("Email scheduled for retry", email_id=email_id, backoff_seconds=backoff_seconds)
                    self.metrics.increment_counter("queue_retries_scheduled")

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to retry email #{email_id}: {e}", exc_info=True)
            self.logger.exception("Email retry scheduling failed", email_id=email_id)
            self.metrics.increment_counter("queue_retry_errors")
            raise EmailQueueError(f"Failed to retry email: {e}") from e
        finally:
            self._return_connection(conn)

    def get_email_by_id(self, email_id: int) -> EmailRecord | None:
        """Get email record by ID.

        Args:
            email_id: Email ID to retrieve.

        Returns:
            Email record or None if not found.

        Raises:
            EmailQueueError: If database operation fails.

        Example:
            email = queue.get_email_by_id(123)
            if email:
                print(f"Email status: {email.status}")
        """
        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_query", tags={"operation": "get_by_id"}):
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT * FROM {self.config.SCHEMA_NAME}.email_queue
                        WHERE id = %s
                        """,
                        (email_id,),
                    )
                    row = cur.fetchone()

                    if not row:
                        logger.debug(f"ℹ️ Email #{email_id} not found")
                        self.logger.debug("Email not found", email_id=email_id)
                        return None

                    row_dict = dict(row)
                    template_context_raw = row_dict.get("template_context")
                    if template_context_raw and isinstance(template_context_raw, str):
                        row_dict["template_context"] = json.loads(template_context_raw)

                    self.logger.debug("Email retrieved", email_id=email_id)
                    self.metrics.increment_counter("queue_gets")
                    return EmailRecord(**row_dict)

        except Exception as e:
            logger.error(f"❌ Failed to get email #{email_id}: {e}", exc_info=True)
            self.logger.exception("Failed to get email", email_id=email_id)
            self.metrics.increment_counter("queue_get_errors")
            raise EmailQueueError(f"Failed to retrieve email: {e}") from e
        finally:
            self._return_connection(conn)

    def cleanup_old_emails(self, days_to_keep: int = 90) -> int:
        """Cleanup old sent/failed emails for maintenance.

        Deletes emails marked as sent or failed that are older than
        the specified number of days.

        Args:
            days_to_keep: Keep emails from last N days (default: 90).

        Returns:
            Number of deleted emails.

        Raises:
            EmailQueueError: If database operation fails.

        Example:
            deleted = queue.cleanup_old_emails(days_to_keep=60)
            print(f"Deleted {deleted} old emails")
        """
        conn = self._get_connection()
        try:
            with self.metrics.record_latency("queue_cleanup", tags={"days_to_keep": str(days_to_keep)}):
                with conn.cursor() as cur:
                    logger.info(f"🧹 Cleaning up emails older than {days_to_keep} days...")
                    self.logger.info("Starting email cleanup", days_to_keep=days_to_keep)

                    cur.execute(
                        f"""
                        SELECT {self.config.SCHEMA_NAME}.cleanup_old_emails(%s)
                        """,
                        (days_to_keep,),
                    )
                    deleted_count = cur.fetchone()["cleanup_old_emails"]
                    conn.commit()

                    logger.info(f"✅ Deleted {deleted_count} old emails")
                    self.logger.info("Email cleanup completed", deleted_count=deleted_count)
                    self.metrics.increment_counter("queue_cleanup_runs")
                    self.metrics.set_gauge("queue_cleanup_deleted_last_run", deleted_count)
                    return deleted_count

        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Failed to cleanup old emails: {e}", exc_info=True)
            self.logger.exception("Email cleanup failed")
            self.metrics.increment_counter("queue_cleanup_errors")
            raise EmailQueueError(f"Failed to cleanup emails: {e}") from e
        finally:
            self._return_connection(conn)

    def close(self) -> None:
        """Close all connections in pool.

        Should be called when shutting down the application to clean up
        database resources properly.
        """
        if self._pool:
            logger.info("🔌 Closing database connection pool...")
            self._pool.closeall()
            logger.info("✅ Connection pool closed")
