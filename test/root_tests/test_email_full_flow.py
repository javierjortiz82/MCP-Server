#!/usr/bin/env python3
"""Full end-to-end test of email template rendering."""

import sys

sys.path.insert(0, "/home/javort/Lab01-MCP")

from datetime import datetime, timedelta, timezone

from email_service.models import EmailType
from email_service.queue_manager import EmailQueueManager

# Test parameters
booking_id = 16
customer_email = "tvboxcr506@gmail.com"
customer_name = "Javier Ortiz Leon Test"

# Create queue manager
queue_mgr = EmailQueueManager()

# Enqueue an email

template_context = {
    "customer_name": customer_name,
    "booking_id": booking_id,
    "service_type": "Premium Consultation",
    "booking_date": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
    "booking_time": "16:00",
    "duration_minutes": 90,
    "google_calendar_link": "https://calendar.google.com/calendar/u/0/r",
}

for _key, _val in template_context.items():
    pass

email_id = queue_mgr.enqueue_email(
    email_type=EmailType.BOOKING_CREATED,
    recipient_email=customer_email,
    recipient_name=customer_name,
    subject="✅ Confirmación de Reserva Premium",
    body_html="",  # Empty - will render from template
    template_context=template_context,
    booking_id=booking_id,
    priority=1,  # High priority
)


# Retrieve it back

pending = queue_mgr.get_pending_emails(limit=10)

test_email = None
for email in pending:
    if email.id == email_id:
        test_email = email
        break

if test_email:
    if test_email.template_context:
        pass
    else:
        pass
else:
    pass
