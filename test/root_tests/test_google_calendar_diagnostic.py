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

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add mcp_server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp_server"))
sys.path.insert(0, str(Path(__file__).parent))

from mcp_server.config.settings import settings
from mcp_server.utils.logger import setup_logging

logger = setup_logging("google_calendar_diagnostic")


def print_header(text: str, char: str = "="):
    """Print fancy header."""


def test_configuration():
    """Test 1: Verify Google Calendar configuration."""
    print_header("TEST 1: Configuration Loading", "=")

    if not settings.GOOGLE_CALENDAR_ENABLED:
        return False

    return settings.GOOGLE_CALENDAR_ID


def test_credentials_file():
    """Test 2: Verify service account credentials file."""
    print_header("TEST 2: Service Account Credentials File", "=")

    credentials_path = Path(settings.GOOGLE_CALENDAR_CREDENTIALS_PATH)

    if not credentials_path.exists():
        return False

    # Try to parse JSON
    try:
        with open(credentials_path) as f:
            creds_data = json.load(f)

        required_fields = ["type", "project_id", "private_key_id", "private_key", "client_email"]
        for field in required_fields:
            if field in creds_data:
                value = creds_data[field]
                if field == "private_key":
                    # Show only first 50 chars of private key
                    value = value[:50] + "..." if len(value) > 50 else value
            else:
                return False

        return True

    except json.JSONDecodeError:
        return False
    except Exception:
        return False


def test_calendar_client_initialization():
    """Test 3: Test GoogleCalendarClient initialization."""
    print_header("TEST 3: GoogleCalendarClient Initialization", "=")

    try:
        from mcp_server.utils.google_calendar import GoogleCalendarClient

        client = GoogleCalendarClient(
            credentials_path=str(settings.google_calendar_credentials_path),
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            timezone=settings.GOOGLE_CALENDAR_TIMEZONE,
        )

        return True, client

    except Exception:
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

        event = client.create_event(
            summary="Test Event - Google Calendar Integration",
            description="This is a test event created by diagnostic script.",
            start_datetime=start_str,
            end_datetime=end_str,
            attendee_email="test@example.com",
        )

        return True, event

    except Exception:
        import traceback

        traceback.print_exc()
        return False, None


def test_booking_integration():
    """Test 5: Test booking system integration with calendar."""
    print_header("TEST 5: Booking System Integration", "=")

    try:
        # Import booking tools
        from mcp_server.tools.bookings import create_booking

        # Create a test booking for tomorrow at 14:00
        tomorrow = datetime.now() + timedelta(days=1)
        booking_date = tomorrow.strftime("%Y-%m-%d")
        booking_time = "14:00"

        result = create_booking(
            customer_name="Test User",
            customer_email="test@example.com",
            customer_phone="555-1234",
            service_type="consultation",
            booking_date=booking_date,
            booking_time=booking_time,
            duration_minutes=60,
            notes="Test booking for calendar integration",
        )

        return bool(result.get("google_calendar_event_id"))

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all diagnostic tests."""
    results = []

    # Test 1: Configuration
    config_ok = test_configuration()
    results.append(("Configuration", config_ok))

    if not config_ok:
        return 1

    # Test 2: Credentials file
    creds_ok = test_credentials_file()
    results.append(("Credentials File", creds_ok))

    if not creds_ok:
        return 1

    # Test 3: GoogleCalendarClient initialization
    client_ok, client = test_calendar_client_initialization()
    results.append(("GoogleCalendarClient", client_ok))

    if not client_ok:
        return 1

    # Test 4: Event creation
    event_ok, _event = test_event_creation(client)
    results.append(("Event Creation", event_ok))

    # Test 5: Booking integration (only if calendar is working)
    if event_ok:
        booking_ok = test_booking_integration()
        results.append(("Booking Integration", booking_ok))

    # Summary
    print_header("SUMMARY", "=")
    for _test_name, _passed in results:
        pass

    all_passed = all(passed for _, passed in results)

    if all_passed:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit(main())
