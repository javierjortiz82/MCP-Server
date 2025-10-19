#!/usr/bin/env python3
"""Sync existing bookings to Google Calendar.

This script finds all bookings that don't have a Google Calendar event
and creates them retroactively. Useful when calendar integration was
added/fixed after bookings were already created.

Usage:
    python sync_bookings_to_calendar.py              # Sync all missing
    python sync_bookings_to_calendar.py --booking-id 12  # Sync specific
    python sync_bookings_to_calendar.py --dry-run    # Preview changes
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from argparse import ArgumentParser

# Add paths
sys.path.insert(0, str(Path.cwd() / "mcp_server"))

from mcp_server.config.settings import settings
from mcp_server.utils.db import fetchone, fetchall, execute
from mcp_server.utils.logger import setup_logging
from mcp_server.utils.google_calendar import GoogleCalendarClient
from mcp_server.tools.bookings import _format_datetime_iso, _get_timezone_offset

logger = setup_logging("sync_bookings_calendar")


def print_header(text: str, char: str = "="):
    """Print fancy header."""
    print("\n" + char * 80)
    print(f"  {text}")
    print(char * 80)


def get_bookings_without_calendar_events():
    """Get all bookings that don't have calendar events."""
    try:
        bookings = fetchall(
            f"""
            SELECT id, customer_name, customer_email, customer_phone,
                   service_type, booking_date, booking_time, duration_minutes,
                   status, notes
            FROM {settings.SCHEMA_NAME}.appointments
            WHERE google_calendar_event_id IS NULL
            AND status = 'confirmed'
            AND booking_date >= CURRENT_DATE
            ORDER BY booking_date ASC, booking_time ASC
            """
        )
        return bookings
    except Exception as e:
        logger.exception(f"Failed to fetch bookings: {e}")
        return []


def sync_booking_to_calendar(booking: dict, dry_run: bool = False):
    """Sync a single booking to Google Calendar.

    Args:
        booking: Booking dict from database
        dry_run: If True, don't actually create the event

    Returns:
        Tuple (success: bool, event_id: str | None, error: str | None)
    """
    try:
        # Initialize calendar client
        client = GoogleCalendarClient(
            credentials_path=str(settings.google_calendar_credentials_path),
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            timezone=settings.GOOGLE_CALENDAR_TIMEZONE,
        )

        # Format times for calendar
        booking_date = str(booking["booking_date"])
        # Extract HH:MM from time object (format: HH:MM:SS or similar)
        booking_time_str = str(booking["booking_time"])
        # Get only HH:MM part
        booking_time = booking_time_str.split(":")[0] + ":" + booking_time_str.split(":")[1]

        start_datetime = _format_datetime_iso(booking_date, booking_time)
        end_time = (
            datetime.fromisoformat(f"{booking_date}T{booking_time}")
            + timedelta(minutes=booking["duration_minutes"])
        ).strftime("%H:%M")
        end_datetime = _format_datetime_iso(booking_date, end_time)

        logger.info(
            f"Creating calendar event for booking #{booking['id']}: "
            f"{booking['service_type']} on {booking_date} at {booking_time}"
        )

        if dry_run:
            print(f"[DRY-RUN] Would create calendar event:")
            print(f"  Summary: {booking['service_type']} - {booking['customer_name']}")
            print(f"  Start: {start_datetime}")
            print(f"  End: {end_datetime}")
            return True, None, None

        # Create event
        event = client.create_event(
            summary=f"{booking['service_type']} - {booking['customer_name']}",
            description=f"Booking ID: {booking['id']}\nService: {booking['service_type']}\nCustomer: {booking['customer_name']}\nNotes: {booking.get('notes', '')}",
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            attendee_email=booking["customer_email"],
        )

        logger.info(f"✅ Calendar event created: {event.event_id}")

        # Update database
        update_sql = f"""
        UPDATE {settings.SCHEMA_NAME}.appointments
        SET google_calendar_event_id = %s,
            google_calendar_link = %s
        WHERE id = %s
        """

        execute(update_sql, (event.event_id, event.html_link, booking["id"]))

        logger.info(f"✅ Booking #{booking['id']} updated with calendar event")

        return True, event.event_id, None

    except Exception as e:
        logger.exception(f"Failed to sync booking #{booking['id']}: {e}")
        return False, None, str(e)


def main():
    """Main sync function."""
    parser = ArgumentParser(description="Sync bookings to Google Calendar")
    parser.add_argument(
        "--booking-id",
        type=int,
        help="Sync specific booking ID",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them",
    )
    args = parser.parse_args()

    print_header("BOOKING TO GOOGLE CALENDAR SYNC", "█")

    # Verify calendar is enabled
    if not settings.GOOGLE_CALENDAR_ENABLED:
        print("❌ ERROR: Google Calendar is not enabled")
        print("   Set GOOGLE_CALENDAR_ENABLED=true in .env")
        return 1

    print(f"Google Calendar Configuration:")
    print(f"  Enabled: {settings.GOOGLE_CALENDAR_ENABLED}")
    print(f"  Calendar ID: {settings.GOOGLE_CALENDAR_ID}")
    print(f"  Timezone: {settings.GOOGLE_CALENDAR_TIMEZONE}")

    if args.dry_run:
        print(f"\n⚠️  DRY-RUN MODE: No changes will be made\n")

    # Get bookings
    if args.booking_id:
        print(f"\nFetching booking #{args.booking_id}...")
        booking = fetchone(
            f"""
            SELECT id, customer_name, customer_email, customer_phone,
                   service_type, booking_date, booking_time, duration_minutes,
                   status, notes
            FROM {settings.SCHEMA_NAME}.appointments
            WHERE id = %s
            """,
            (args.booking_id,),
        )

        if not booking:
            print(f"❌ Booking #{args.booking_id} not found")
            return 1

        bookings = [booking]
        print(f"✅ Found 1 booking")
    else:
        bookings = get_bookings_without_calendar_events()
        print(f"\nFound {len(bookings)} bookings without calendar events")

    if not bookings:
        print("\n✅ All bookings are synced to Google Calendar!")
        return 0

    # Sync bookings
    print_header("SYNCING BOOKINGS", "=")

    synced = 0
    failed = 0

    for booking in bookings:
        print(f"\n📌 Booking #{booking['id']}")
        print(f"   Customer: {booking['customer_name']}")
        print(f"   Service: {booking['service_type']}")
        print(f"   Date: {booking['booking_date']} at {booking['booking_time']}")

        success, event_id, error = sync_booking_to_calendar(booking, dry_run=args.dry_run)

        if success:
            if not args.dry_run:
                print(f"   ✅ Synced (Event ID: {event_id})")
            synced += 1
        else:
            print(f"   ❌ Failed: {error}")
            failed += 1

    # Summary
    print_header("SUMMARY", "=")

    print(f"\nResults:")
    print(f"  Total: {len(bookings)}")
    print(f"  Synced: {synced}")
    print(f"  Failed: {failed}")

    if args.dry_run:
        print(f"\n💡 This was a dry-run. Run without --dry-run to make changes.")

    if failed == 0:
        print(f"\n✅ All bookings synced successfully!")
        return 0
    else:
        print(f"\n⚠️  {failed} bookings failed to sync")
        return 1


if __name__ == "__main__":
    exit(main())
