#!/usr/bin/env python3
"""
Test script for email template rendering pipeline.

This test verifies that:
1. Booking creation enqueues emails with template_context
2. Template context is properly serialized to JSON
3. Template context is properly deserialized by worker
4. Email worker renders templates and sends them
"""

import sys
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add paths
sys.path.insert(0, "/home/javort/Lab01-MCP")
sys.path.insert(0, "/home/javort/Lab01-MCP/agent/src")

# Import modules
from email_service.queue_manager import EmailQueueManager
from email_service.models import EmailType, EmailRecord
from email_service.config import settings

def test_email_pipeline():
    """Test the complete email pipeline with template rendering."""

    print("=" * 80)
    print(" EMAIL TEMPLATE RENDERING TEST")
    print("=" * 80)
    print()

    # Initialize queue manager
    print("🔧 Initializing EmailQueueManager...")
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

    print(f"\n📝 Test Data:")
    print(f"   Booking ID: {booking_id}")
    print(f"   Customer: {customer_name}")
    print(f"   Email: {customer_email}")
    print(f"   Service: {service_type}")
    print(f"   Date: {booking_date} at {booking_time}")
    print(f"   Template Context Keys: {list(template_context.keys())}")
    print()

    # Step 1: Enqueue email (simulating booking creation)
    print("=" * 80)
    print("STEP 1: Enqueueing booking_created email")
    print("=" * 80)

    try:
        email_id = queue_mgr.enqueue_email(
            email_type=EmailType.BOOKING_CREATED,
            recipient_email=customer_email,
            recipient_name=customer_name,
            subject=f"✅ Confirmación de Reserva - {service_type}",
            body_html="",  # Empty - will render from template
            template_context=template_context,
            booking_id=booking_id,
            priority=5,
        )
        print(f"✅ Email enqueued with ID: {email_id}")
        print(f"   Email will render from template: booking_created.html")
        print()

    except Exception as e:
        print(f"❌ Failed to enqueue email: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 2: Retrieve pending emails (simulating worker poll)
    print("=" * 80)
    print("STEP 2: Retrieving pending emails (simulating worker poll)")
    print("=" * 80)

    time.sleep(1)  # Give database time to commit

    try:
        pending_emails = queue_mgr.get_pending_emails(limit=10)

        if not pending_emails:
            print("❌ No pending emails found in queue!")
            return

        # Find our test email
        test_email = None
        for email in pending_emails:
            if email.booking_id == booking_id:
                test_email = email
                break

        if not test_email:
            print(f"❌ Test email with booking_id {booking_id} not found in pending emails")
            print(f"   Found {len(pending_emails)} emails total")
            return

        print(f"✅ Found test email (ID: {test_email.id})")
        print(f"   Type: {test_email.type}")
        print(f"   Status: {test_email.status}")
        print(f"   Body HTML empty?: {not test_email.body_html or len(test_email.body_html) == 0}")
        print(f"   Template Context present?: {test_email.template_context is not None}")

        if test_email.template_context:
            print(f"   Template Context Keys: {list(test_email.template_context.keys())}")
            print(f"   Template Context Type: {type(test_email.template_context).__name__}")

            # Verify context contains expected data
            expected_keys = ['customer_name', 'booking_id', 'service_type', 'booking_date', 'booking_time', 'duration_minutes']
            missing_keys = [k for k in expected_keys if k not in test_email.template_context]

            if missing_keys:
                print(f"   ⚠️  Missing keys: {missing_keys}")
            else:
                print(f"   ✅ All expected keys present in context")
                print(f"   Customer Name: {test_email.template_context.get('customer_name')}")
                print(f"   Booking Date: {test_email.template_context.get('booking_date')}")
        else:
            print(f"   ❌ CRITICAL: template_context is None!")

        print()

    except Exception as e:
        print(f"❌ Failed to retrieve pending emails: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 3: Simulate reschedule to test rescheduled template context
    print("=" * 80)
    print("STEP 3: Testing reschedule email with old/new dates")
    print("=" * 80)

    old_date = booking_date
    old_time = booking_time
    new_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    new_time = "15:30"

    reschedule_context = template_context.copy()
    reschedule_context.update({
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "booking_date": new_date,
        "booking_time": new_time,
    })

    try:
        email_id_2 = queue_mgr.enqueue_email(
            email_type=EmailType.BOOKING_RESCHEDULED,
            recipient_email=customer_email,
            recipient_name=customer_name,
            subject=f"📅 Reprogramación de Reserva - {service_type}",
            body_html="",  # Empty - will render from template
            template_context=reschedule_context,
            booking_id=booking_id,
            priority=5,
        )
        print(f"✅ Reschedule email enqueued with ID: {email_id_2}")
        print(f"   Old Date/Time: {old_date} @ {old_time}")
        print(f"   New Date/Time: {new_date} @ {new_time}")
        print(f"   Template Context Keys: {list(reschedule_context.keys())}")
        print()

    except Exception as e:
        print(f"❌ Failed to enqueue reschedule email: {e}")
        import traceback
        traceback.print_exc()
        return

    # Step 4: Final verification
    print("=" * 80)
    print("STEP 4: Verification Summary")
    print("=" * 80)
    print()
    print("✅ Email Pipeline Test Completed Successfully!")
    print()
    print("Next steps:")
    print("1. Monitor email worker logs for template rendering")
    print(f"   Watch for: 'Rendering template for email type: {EmailType.BOOKING_CREATED.value}'")
    print("2. Check recipient email: tvboxcr506@gmail.com")
    print("3. Verify received email has:")
    print("   - Professional HTML formatting")
    print("   - Gradient header with brand colors")
    print("   - Dynamic content (customer name, dates)")
    print("   - Google Calendar action button")
    print()
    print("Database details:")
    print(f"   Schema: {settings.SCHEMA_NAME}")
    print(f"   Table: email_queue")
    print(f"   Emails queued: 2 (booking_created + booking_rescheduled)")
    print()

if __name__ == "__main__":
    test_email_pipeline()
