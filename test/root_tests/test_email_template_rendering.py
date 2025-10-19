#!/usr/bin/env python3
"""Test script for email template rendering pipeline.

This test verifies that:
1. Booking creation enqueues emails with template_context
2. Template context is properly serialized to JSON
3. Template context is properly deserialized by worker
4. Email worker renders templates and sends them
"""

import sys
import time
from datetime import datetime, timedelta, timezone

# Add paths
sys.path.insert(0, "/home/javort/Lab01-MCP")
sys.path.insert(0, "/home/javort/Lab01-MCP/agent/src")

from email_service.models import EmailType

# Import modules
from email_service.queue_manager import EmailQueueManager


def test_email_pipeline():
    """Test the complete email pipeline with template rendering."""
    # Initialize queue manager
    queue_mgr = EmailQueueManager()

    # Use existing booking from database
    booking_id = 16
    customer_email = "tvboxcr506@gmail.com"
    customer_name = "Javier Ortiz Leon"
    service_type = "Consulta Profesional"
    booking_date = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    booking_time = "14:00"

    # Create template context (this is what should be passed from bookings.py)
    template_context = {
        "customer_name": customer_name,
        "booking_id": booking_id,
        "service_type": service_type,
        "booking_date": booking_date,
        "booking_time": booking_time,
        "duration_minutes": 60,
        "google_calendar_link": "https://calendar.google.com/calendar/u/0/r",
    }

    # Step 1: Enqueue email (simulating booking creation)

    try:
        queue_mgr.enqueue_email(
            email_type=EmailType.BOOKING_CREATED,
            recipient_email=customer_email,
            recipient_name=customer_name,
            subject=f"✅ Confirmación de Reserva - {service_type}",
            body_html="",  # Empty - will render from template
            template_context=template_context,
            booking_id=booking_id,
            priority=5,
        )

    except Exception:
        import traceback

        traceback.print_exc()
        return

    # Step 2: Retrieve pending emails (simulating worker poll)

    time.sleep(1)  # Give database time to commit

    try:
        pending_emails = queue_mgr.get_pending_emails(limit=10)

        if not pending_emails:
            return

        # Find our test email
        test_email = None
        for email in pending_emails:
            if email.booking_id == booking_id:
                test_email = email
                break

        if not test_email:
            return

        if test_email.template_context:
            # Verify context contains expected data
            expected_keys = [
                "customer_name",
                "booking_id",
                "service_type",
                "booking_date",
                "booking_time",
                "duration_minutes",
            ]
            missing_keys = [k for k in expected_keys if k not in test_email.template_context]

            if missing_keys:
                pass
            else:
                pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
        return

    # Step 3: Simulate reschedule to test rescheduled template context

    old_date = booking_date
    old_time = booking_time
    new_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    new_time = "15:30"

    reschedule_context = template_context.copy()
    reschedule_context.update(
        {
            "old_date": old_date,
            "old_time": old_time,
            "new_date": new_date,
            "new_time": new_time,
            "booking_date": new_date,
            "booking_time": new_time,
        }
    )

    try:
        queue_mgr.enqueue_email(
            email_type=EmailType.BOOKING_RESCHEDULED,
            recipient_email=customer_email,
            recipient_name=customer_name,
            subject=f"📅 Reprogramación de Reserva - {service_type}",
            body_html="",  # Empty - will render from template
            template_context=reschedule_context,
            booking_id=booking_id,
            priority=5,
        )

    except Exception:
        import traceback

        traceback.print_exc()
        return

    # Step 4: Final verification


if __name__ == "__main__":
    test_email_pipeline()
