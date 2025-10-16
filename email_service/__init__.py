"""Email Service - Asynchronous email delivery system for bookings.

This package provides a robust email queue system with:
- SMTP email delivery (Gmail, SendGrid, AWS SES)
- Template-based email rendering (Jinja2)
- Automatic retry with exponential backoff
- Scheduled emails (reminders, delayed sends)
- Status tracking (pending → processing → sent/failed)

Architecture:
    - PostgreSQL queue table (email_queue)
    - Worker service (polls queue every 10s)
    - SMTP client wrapper
    - Jinja2 template renderer

Usage:
    # Enqueue an email
    from email_service.queue_manager import EmailQueueManager
    queue = EmailQueueManager()

    queue.enqueue_email(
        type="booking_created",
        recipient_email="customer@example.com",
        recipient_name="John Doe",
        context={"booking_id": 123, "service": "Consultation"}
    )

    # Run worker (in Docker container)
    from email_service.worker import EmailWorker
    worker = EmailWorker()
    await worker.run()

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

__version__ = "1.0.0"
__all__ = [
    "EmailWorker",
    "EmailQueueManager",
    "SMTPClient",
    "TemplateRenderer",
    "EmailConfig",
]

from email_service.config import EmailConfig
from email_service.queue_manager import EmailQueueManager
from email_service.smtp_client import SMTPClient
from email_service.template_renderer import TemplateRenderer
from email_service.worker import EmailWorker
