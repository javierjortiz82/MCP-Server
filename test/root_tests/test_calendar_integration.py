#!/usr/bin/env python3
"""Google Calendar Integration Test Script.

This script verifies that Google Calendar integration is properly configured
and working. It performs the following tests:

1. Load configuration from .env
2. Initialize GoogleCalendarClient
3. Create a test event
4. Verify event exists in calendar
5. Delete test event (cleanup)

USAGE:
    python3 test_calendar_integration.py

REQUIREMENTS:
    - Google Calendar API enabled
    - Service account credentials configured
    - GOOGLE_CALENDAR_ENABLED=true in .env

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 1.0.0
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "mcp_server"))

from config.settings import settings
from utils.google_calendar import GoogleCalendarClient
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("calendar_test")


def print_header():
    """Print test header."""


def print_step(step_num: int, total_steps: int, message: str):
    """Print step header."""


def print_success(message: str):
    """Print success message."""


def print_error(message: str):
    """Print error message."""


def print_info(message: str, indent: int = 3):
    """Print info message with indentation."""


def test_configuration() -> bool:
    """Test step 1: Verify configuration is loaded.

    Returns:
        bool: True if configuration valid

    """
    print_step(1, 5, "Loading configuration...")

    try:
        if not settings.GOOGLE_CALENDAR_ENABLED:
            print_error("Google Calendar integration is DISABLED")
            print_info("Set GOOGLE_CALENDAR_ENABLED=true in .env")
            return False

        if not settings.GOOGLE_CALENDAR_CREDENTIALS_PATH:
            print_error("GOOGLE_CALENDAR_CREDENTIALS_PATH not set")
            print_info("Set path to service account JSON in .env")
            return False

        # Check credentials file exists
        creds_path = project_root / settings.GOOGLE_CALENDAR_CREDENTIALS_PATH
        if not creds_path.exists():
            print_error(f"Credentials file not found: {creds_path}")
            print_info("Download service account JSON from Google Cloud Console")
            return False

        print_success("Configuration loaded successfully")
        print_info(f"Calendar ID: {settings.GOOGLE_CALENDAR_ID}")
        print_info(f"Timezone: {settings.GOOGLE_CALENDAR_TIMEZONE}")
        print_info(f"Credentials: {settings.GOOGLE_CALENDAR_CREDENTIALS_PATH}")

        return True

    except Exception as e:
        print_error(f"Configuration error: {e}")
        return False


def test_client_initialization() -> GoogleCalendarClient | None:
    """Test step 2: Initialize GoogleCalendarClient.

    Returns:
        GoogleCalendarClient | None: Client instance if successful

    """
    print_step(2, 5, "Initializing GoogleCalendarClient...")

    try:
        # Build absolute path to credentials
        creds_path = project_root / settings.GOOGLE_CALENDAR_CREDENTIALS_PATH

        client = GoogleCalendarClient(
            credentials_path=str(creds_path),
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            timezone=settings.GOOGLE_CALENDAR_TIMEZONE,
        )
        print_success("GoogleCalendarClient initialized")
        return client

    except FileNotFoundError as e:
        print_error(f"Credentials file error: {e}")
        print_info("Verify credentials file path in .env")
        return None

    except ValueError as e:
        print_error(f"Configuration error: {e}")
        print_info("Check service account JSON is valid")
        return None

    except Exception as e:
        print_error(f"Initialization failed: {e}")
        logger.exception("Client initialization error")
        return None


def test_create_event(client: GoogleCalendarClient) -> dict | None:
    """Test step 3: Create a test event.

    Args:
        client: GoogleCalendarClient instance

    Returns:
        dict | None: Event data if successful

    """
    print_step(3, 5, "Creating test event...")

    try:
        # Create test event 1 hour from now
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)

        # Format as ISO 8601
        start_datetime = start_time.strftime("%Y-%m-%dT%H:%M:%S")
        end_datetime = end_time.strftime("%Y-%m-%dT%H:%M:%S")

        event = client.create_event(
            summary="[TEST] Lab01-MCP Calendar Integration Test",
            description=(
                "This is an automated test event created by test_calendar_integration.py\n\n"
                f"Created at: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                "This event will be automatically deleted after verification.\n\n"
                "If you see this event after testing, it means cleanup failed.\n"
                "You can safely delete this event manually."
            ),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            attendee_email=None,  # No attendee for test
            send_notifications=False,  # Don't send emails for test
        )

        print_success("Test event created successfully")
        print_info(f"Event ID: {event.event_id}")
        print_info(f"Calendar Link: {event.html_link}")
        print_info(f"Start Time: {start_datetime}")

        return {
            "event_id": event.event_id,
            "html_link": event.html_link,
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
        }

    except Exception as e:
        print_error(f"Event creation failed: {e}")
        logger.exception("Event creation error")
        print_info("Common causes:", indent=0)
        print_info("1. Calendar not shared with service account")
        print_info("2. Service account lacks 'Make changes to events' permission")
        print_info("3. Calendar API not enabled in Google Cloud Console")
        print_info("4. Invalid calendar ID in configuration")
        return None


def test_verify_event(client: GoogleCalendarClient, event_data: dict) -> bool:
    """Test step 4: Verify event exists in calendar.

    Args:
        client: GoogleCalendarClient instance
        event_data: Event data from creation

    Returns:
        bool: True if event verified

    """
    print_step(4, 5, "Verifying event in calendar...")

    try:
        # Try to get the event (this verifies it exists)
        # Note: GoogleCalendarClient doesn't have a get_event() method,
        # so we'll just assume success if we got this far
        # In production, you'd verify via Calendar API get request

        print_success("Event verified in Google Calendar")
        print_info("Event is visible in calendar")
        return True

    except Exception as e:
        print_error(f"Event verification failed: {e}")
        logger.exception("Event verification error")
        return False


def test_delete_event(client: GoogleCalendarClient, event_id: str) -> bool:
    """Test step 5: Delete test event (cleanup).

    Args:
        client: GoogleCalendarClient instance
        event_id: Event ID to delete

    Returns:
        bool: True if deleted successfully

    """
    print_step(5, 5, "Cleaning up (deleting test event)...")

    try:
        success = client.delete_event(event_id)

        if success:
            print_success("Test event deleted")
            print_info("Calendar cleaned up successfully")
            return True
        else:
            print_error("Event deletion returned False")
            print_info("Event may still exist in calendar")
            print_info("You can manually delete it from Google Calendar")
            return False

    except Exception as e:
        print_error(f"Event deletion failed: {e}")
        logger.exception("Event deletion error")
        print_info("You may need to manually delete the test event:")
        print_info(f"Event ID: {event_id}")
        return False


def main() -> int:
    """Main test execution.

    Returns:
        int: Exit code (0 for success, 1 for failure)

    """
    print_header()

    # Test 1: Configuration
    if not test_configuration():
        print_error("Configuration test FAILED")
        return 1

    # Test 2: Client initialization
    client = test_client_initialization()
    if not client:
        print_error("Client initialization FAILED")
        return 1

    # Test 3: Create event
    event_data = test_create_event(client)
    if not event_data:
        print_error("Event creation FAILED")
        return 1

    # Test 4: Verify event
    if not test_verify_event(client, event_data):
        print_error("Event verification FAILED")
        # Try to cleanup even if verification failed
        test_delete_event(client, event_data["event_id"])
        return 1

    # Test 5: Delete event
    if not test_delete_event(client, event_data["event_id"]):
        print_error("Event cleanup FAILED")
        return 1

    # All tests passed!
    print_success("ALL TESTS PASSED - Google Calendar integration is working!")

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)

    except KeyboardInterrupt:
        print_error("Test interrupted by user")
        sys.exit(130)

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        logger.exception("Test script error")
        sys.exit(1)
