"""Email Worker - Queue processor and email delivery daemon.

Polls the email queue and sends emails via SMTP:
- Polls every N seconds (configurable)
- Processes emails in batches
- Renders templates with Jinja2
- Sends via SMTP with retry logic
- Updates status in database

Designed to run as a Docker container service.

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Any

from email_service.config import settings
from email_service.models import EmailRecord, EmailStatus, EmailType
from email_service.queue_manager import EmailQueueManager
from email_service.smtp_client import SMTPClient
from email_service.template_renderer import TemplateRenderer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("email_worker")


class EmailWorker:
    """Email queue processor daemon.

    Continuously polls the queue and delivers emails.
    Handles graceful shutdown on SIGTERM/SIGINT.
    """

    def __init__(self) -> None:
        """Initialize email worker components."""
        logger.info("🚀 Initializing Email Worker...")

        self.queue_manager = EmailQueueManager()
        self.smtp_client = SMTPClient()
        self.template_renderer = TemplateRenderer()

        self.running = True
        self.processed_count = 0
        self.failed_count = 0

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("✅ Email Worker initialized successfully")

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals gracefully.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        logger.info(f"🛑 Received shutdown signal ({signum}). Stopping gracefully...")
        self.running = False

    async def run(self) -> None:
        """Main worker loop - polls queue and processes emails.

        Runs indefinitely until shutdown signal received.
        """
        logger.info("🔄 Starting email worker loop...")
        logger.info(
            f"📊 Configuration: Poll interval={settings.EMAIL_WORKER_POLL_INTERVAL}s, "
            f"Batch size={settings.EMAIL_WORKER_BATCH_SIZE}"
        )

        while self.running:
            try:
                await self._process_batch()
            except Exception as e:
                logger.error(f"❌ Unexpected error in worker loop: {e}", exc_info=True)

            # Sleep before next poll
            await asyncio.sleep(settings.EMAIL_WORKER_POLL_INTERVAL)

        logger.info("👋 Email worker stopped")
        self._print_stats()
        self.queue_manager.close()

    async def _process_batch(self) -> None:
        """Process a batch of pending emails."""
        # Get pending emails from queue
        pending_emails = self.queue_manager.get_pending_emails(
            limit=settings.EMAIL_WORKER_BATCH_SIZE
        )

        if not pending_emails:
            logger.debug("📭 No pending emails in queue")
            return

        logger.info(f"📬 Processing {len(pending_emails)} pending emails...")

        # Process each email
        for email in pending_emails:
            try:
                await self._process_email(email)
                self.processed_count += 1
            except Exception as e:
                logger.error(
                    f"❌ Failed to process email {email.id}: {e}", exc_info=True
                )
                self.failed_count += 1

    async def _process_email(self, email: EmailRecord) -> None:
        """Process a single email.

        Args:
            email: Email record to process.

        Raises:
            Exception: If email processing fails.
        """
        logger.info(
            f"📧 Processing email #{email.id} - Type: {email.type}, "
            f"To: {email.recipient_email}"
        )

        try:
            # Mark as processing
            self.queue_manager.update_email_status(
                email.id, EmailStatus.PROCESSING
            )

            # Render template if template_context provided
            if email.template_context:
                logger.debug(
                    f"📄 Rendering template for email type: {email.type}, "
                    f"context keys: {list(email.template_context.keys())}"
                )
                body_html = self.template_renderer.render_html(
                    EmailType(email.type), email.template_context
                )
                body_text = self.template_renderer.render_text(
                    EmailType(email.type), email.template_context
                )
                logger.debug(
                    f"✅ Template rendered successfully - "
                    f"HTML size: {len(body_html)} bytes, "
                    f"Text size: {len(body_text) if body_text else 0} bytes"
                )
            else:
                # Use pre-rendered content from queue
                logger.debug(
                    f"Using pre-rendered content from queue - "
                    f"HTML size: {len(email.body_html)} bytes, "
                    f"Text size: {len(email.body_text) if email.body_text else 0} bytes"
                )
                body_html = email.body_html
                body_text = email.body_text

                # Warn if body_html is empty and no template_context
                if not body_html.strip():
                    logger.warning(
                        f"⚠️ Email #{email.id} has empty body_html and no template_context! "
                        f"Recipient will receive empty email."
                    )

            # Send email via SMTP
            self.smtp_client.send_email(
                recipient_email=email.recipient_email,
                recipient_name=email.recipient_name,
                subject=email.subject,
                body_html=body_html,
                body_text=body_text,
            )

            # Mark as sent
            self.queue_manager.update_email_status(
                email.id, EmailStatus.SENT, sent_at=datetime.now()
            )

            logger.info(f"✅ Email #{email.id} sent successfully")

        except Exception as e:
            logger.error(f"❌ Failed to send email #{email.id}: {e}")

            # Handle retry logic
            if email.retry_count < email.max_retries:
                # Retry with exponential backoff
                self.queue_manager.retry_email(
                    email.id,
                    error=str(e),
                    backoff_seconds=settings.EMAIL_RETRY_BACKOFF_SECONDS,
                )
                logger.warning(
                    f"🔄 Email #{email.id} scheduled for retry "
                    f"({email.retry_count + 1}/{email.max_retries})"
                )
            else:
                # Max retries exceeded - mark as failed
                self.queue_manager.update_email_status(
                    email.id, EmailStatus.FAILED, error=str(e)
                )
                logger.error(
                    f"💀 Email #{email.id} permanently failed after "
                    f"{email.max_retries} retries"
                )

            raise  # Re-raise for outer error handler

    def _print_stats(self) -> None:
        """Print worker statistics on shutdown."""
        total = self.processed_count + self.failed_count
        success_rate = (
            (self.processed_count / total * 100) if total > 0 else 0
        )

        logger.info("📊 Email Worker Statistics:")
        logger.info(f"   Total processed: {total}")
        logger.info(f"   Successfully sent: {self.processed_count}")
        logger.info(f"   Failed: {self.failed_count}")
        logger.info(f"   Success rate: {success_rate:.1f}%")


async def main() -> None:
    """Main entry point for worker process."""
    # Validate SMTP configuration before starting
    try:
        settings.validate_smtp_config()
    except ValueError as e:
        logger.error(f"❌ Invalid SMTP configuration: {e}")
        logger.error(
            "💡 Set SMTP_USER and SMTP_PASSWORD environment variables"
        )
        sys.exit(1)

    # Create and run worker
    worker = EmailWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
