#!/usr/bin/env python3
"""
Full end-to-end test of email template rendering.
"""

import sys
sys.path.insert(0, "/home/javort/Lab01-MCP")

from datetime import datetime, timezone, timedelta
from email_service.queue_manager import EmailQueueManager
from email_service.models import EmailType

# Test parameters
booking_id = 16
customer_email = "tvboxcr506@gmail.com"
customer_name = "Javier Ortiz Leon Test"

# Create queue manager
queue_mgr = EmailQueueManager()

# Enqueue an email
print("\n" + "="*80)
print("ENQUEUEING EMAIL")
print("="*80)

template_context = {
    "customer_name": customer_name,
    "booking_id": booking_id,
    "service_type": "Premium Consultation",
    "booking_date": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
    "booking_time": "16:00",
    "duration_minutes": 90,
    "google_calendar_link": "https://calendar.google.com/calendar/u/0/r",
}

print(f"📝 Template Context:")
for key, val in template_context.items():
    print(f"   {key}: {val}")

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

print(f"\n✅ Email enqueued with ID: {email_id}")

# Retrieve it back
print("\n" + "="*80)
print("RETRIEVING EMAIL FROM QUEUE")
print("="*80)

pending = queue_mgr.get_pending_emails(limit=10)
print(f"Found {len(pending)} pending emails")

test_email = None
for email in pending:
    if email.id == email_id:
        test_email = email
        break

if test_email:
    print(f"\n✅ Found email {test_email.id}")
    print(f"   Type: {test_email.type}")
    print(f"   Template Context: {type(test_email.template_context).__name__}")
    if test_email.template_context:
        print(f"   Template Context Keys: {list(test_email.template_context.keys())}")
        print(f"   Can render: YES ✅")
    else:
        print(f"   Template Context: None")
        print(f"   Can render: NO ❌")
else:
    print(f"\n❌ Email {email_id} not found in pending queue")

print("\n" + "="*80)
print("Next: Wait 10 seconds for worker to process email...")
print("="*80)
print("\nMonitor logs with: docker logs -f mcp-email-worker")
print("Expected to see:")
print("  - 📧 Processing email")
print("  - 📄 Rendering template (DEBUG)")
print("  - ✅ Email sent successfully")
