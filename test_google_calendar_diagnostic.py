#!/usr/bin/env python3
"""Diagnostic test for Google Calendar integration.

Tests:
1. Configuration loading
2. Service account credentials file existence and validity
3. GoogleCalendarClient initialization
4. Calendar event creation
5. Booking system integration with calendar

Usage:
    python test_google_calendar_diagnostic.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add mcp_server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.config.settings import settings
from mcp_server.utils.logger import setup_logging

logger = setup_logging("google_calendar_diagnostic")


def print_header(text: str, char: str = "="):
    """Print fancy header."""
    print("\n" + char * 80)
    print(f"  {text}")
    print(char * 80)


def test_configuration():
    """Test 1: Verify Google Calendar configuration."""
    print_header("TEST 1: Configuration Loading", "=")

    print("\nGoogle Calendar Settings:")
    print(f"  Enabled: {settings.GOOGLE_CALENDAR_ENABLED}")
    print(f"  Calendar ID: {settings.GOOGLE_CALENDAR_ID}")
    print(f"  Timezone: {settings.GOOGLE_CALENDAR_TIMEZONE}")
    print(f"  Credentials Path: {settings.GOOGLE_CALENDAR_CREDENTIALS_PATH}")

    if not settings.GOOGLE_CALENDAR_ENABLED:
        print("\n⚠️  WARNING: Google Calendar is DISABLED in configuration")
        print("   To enable: Set GOOGLE_CALENDAR_ENABLED=true in .env")
        return False

    if not settings.GOOGLE_CALENDAR_ID:
        print("\n❌ FAIL: Calendar ID is not configured")
        return False

    print("\n✅ PASS: Configuration looks correct")
    return True


def test_credentials_file():
    """Test 2: Verify service account credentials file."""
    print_header("TEST 2: Service Account Credentials File", "=")

    credentials_path = Path(settings.GOOGLE_CALENDAR_CREDENTIALS_PATH)

    print(f"\nChecking credentials file: {credentials_path}")

    if not credentials_path.exists():
        print(f"❌ FAIL: Credentials file not found")
        print(f"   Expected: {credentials_path}")
        return False

    print(f"✅ File exists: {credentials_path}")
    print(f"   Size: {credentials_path.stat().st_size} bytes")

    # Try to parse JSON
    try:
        with open(credentials_path) as f:
            creds_data = json.load(f)

        print("\n✅ Credentials file is valid JSON")
        print(f"\n  Required fields:")
        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        for field in required_fields:
            if field in creds_data:
                value = creds_data[field]
                if field == "private_key":
                    # Show only first 50 chars of private key
                    value = value[:50] + "..." if len(value) > 50 else value
                print(f"    ✅ {field}: {value}")
            else:
                print(f"    ❌ MISSING: {field}")
                return False

        print("\n✅ PASS: Credentials file is properly formatted")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ FAIL: Credentials file is not valid JSON: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Error reading credentials file: {e}")
        return False


def test_calendar_client_initialization():
    """Test 3: Test GoogleCalendarClient initialization."""
    print_header("TEST 3: GoogleCalendarClient Initialization", "=")

    try:
        from mcp_server.utils.google_calendar import GoogleCalendarClient

        print(f"\nInitializing GoogleCalendarClient...")
        print(f"  Calendar ID: {settings.GOOGLE_CALENDAR_ID}")
        print(f"  Timezone: {settings.GOOGLE_CALENDAR_TIMEZONE}")
        print(f"  Credentials Path: {settings.google_calendar_credentials_path}")

        client = GoogleCalendarClient(
            credentials_path=str(settings.google_calendar_credentials_path),
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            timezone=settings.GOOGLE_CALENDAR_TIMEZONE,
        )

        print(f"\n✅ PASS: GoogleCalendarClient initialized successfully")
        print(f"   Client: {client}")
        return True, client

    except Exception as e:
        print(f"\n❌ FAIL: GoogleCalendarClient initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_event_creation(client):
    """Test 4: Test creating a calendar event."""
    print_header("TEST 4: Calendar Event Creation", "=")

    try:
        # Create event for tomorrow at 15:00
        tomorrow = datetime.now() + timedelta(days=1)
        start_time = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        # Format times with timezone offset
        start_str = start_time.strftime("%Y-%m-%dT%H:%M:%S") + "-06:00"
        end_str = end_time.strftime("%Y-%m-%dT%H:%M:%S") + "-06:00"

        print(f"\nCreating test event...")
        print(f"  Summary: Test Event - Google Calendar Integration")
        print(f"  Start: {start_str}")
        print(f"  End: {end_str}")
        print(f"  Calendar: {settings.GOOGLE_CALENDAR_ID}")

        event = client.create_event(
            summary="Test Event - Google Calendar Integration",
            description="This is a test event created by diagnostic script.",
            start_datetime=start_str,
            end_datetime=end_str,
            attendee_email="test@example.com",
        )

        print(f"\n✅ PASS: Event created successfully!")
        print(f"  Event ID: {event.event_id}")
        print(f"  Title: {event.summary}")
        print(f"  Link: {event.html_link}")

        return True, event

    except Exception as e:
        print(f"\n❌ FAIL: Event creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_booking_integration():
    """Test 5: Test booking system integration with calendar."""
    print_header("TEST 5: Booking System Integration", "=")

    try:
        # Import booking tools
        from mcp_server.tools.bookings import create_booking

        print(f"\nTesting booking creation with calendar integration...")

        # Create a test booking for tomorrow at 14:00
        tomorrow = datetime.now() + timedelta(days=1)
        booking_date = tomorrow.strftime("%Y-%m-%d")
        booking_time = "14:00"

        print(f"  Customer: Test User")
        print(f"  Service: Consultation")
        print(f"  Date: {booking_date}")
        print(f"  Time: {booking_time}")

        result = create_booking(
            customer_name="Test User",
            customer_email="test@example.com",
            customer_phone="555-1234",
            service_type="consultation",
            booking_date=booking_date,
            booking_time=booking_time,
            duration_minutes=60,
            notes="Test booking for calendar integration"
        )

        print(f"\n✅ PASS: Booking created successfully!")
        print(f"  Booking ID: {result.get('booking_id')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Google Calendar Event ID: {result.get('google_calendar_event_id')}")
        print(f"  Google Calendar Link: {result.get('google_calendar_link')}")

        if result.get('google_calendar_event_id'):
            print("\n✅ SUCCESS: Booking was synced to Google Calendar!")
            return True
        else:
            print("\n⚠️  WARNING: Booking created but NOT synced to Google Calendar")
            print("    Check logs for calendar errors")
            return False

    except Exception as e:
        print(f"\n❌ FAIL: Booking creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  GOOGLE CALENDAR INTEGRATION DIAGNOSTIC TEST".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    results = []

    # Test 1: Configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))

    if not config_ok:
        print("\n❌ Cannot proceed - Google Calendar is not configured")
        return 1

    # Test 2: Credentials file
    creds_ok = test_credentials_file()
    results.append(("Credentials File", creds_ok))

    if not creds_ok:
        print("\n❌ Cannot proceed - Credentials file is not valid")
        return 1

    # Test 3: GoogleCalendarClient initialization
    client_ok, client = test_calendar_client_initialization()
    results.append(("GoogleCalendarClient", client_ok))

    if not client_ok:
        print("\n❌ Cannot proceed - GoogleCalendarClient failed to initialize")
        return 1

    # Test 4: Event creation
    event_ok, event = test_event_creation(client)
    results.append(("Event Creation", event_ok))

    # Test 5: Booking integration (only if calendar is working)
    if event_ok:
        booking_ok = test_booking_integration()
        results.append(("Booking Integration", booking_ok))

    # Summary
    print_header("SUMMARY", "=")
    print("\nTest Results:")
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n" + "=" * 80)
        print("  ✅ ALL TESTS PASSED - Google Calendar integration is working!")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("  ❌ SOME TESTS FAILED - Check logs above for details")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    exit(main())
