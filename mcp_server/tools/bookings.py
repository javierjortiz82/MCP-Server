"""Booking management tools for MCP server.

Provides business logic functions for managing appointments/reservations:
- Create, cancel, reschedule bookings
- Check availability
- Fetch booking details
- Google Calendar integration

These are pure business logic functions that are wrapped by MCP handlers.
Follows SOLID principles and functional programming patterns.

References:
    - Database schema: SQL/scripts/create_bookings_schema.sql
    - Google Calendar: mcp_server/utils/google_calendar.py

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.0.0
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from config.settings import settings
from utils.db import fetchall, fetchone
from utils.logger import setup_logging

# Conditional import of Email Queue Manager
try:
    import sys
    from pathlib import Path

    # Add email_service to path
    email_service_path = Path(__file__).parent.parent.parent / "email_service"
    if email_service_path.exists():
        sys.path.insert(0, str(email_service_path.parent))
        from email_service.queue_manager import EmailQueueManager
        from email_service.models import EmailType

        EMAIL_QUEUE_AVAILABLE = True
        logger_init = logging.getLogger("bookings_init")
        logger_init.info("✅ Email queue integration enabled")
    else:
        EMAIL_QUEUE_AVAILABLE = False
        EmailQueueManager = None  # type: ignore[misc,assignment]
        EmailType = None  # type: ignore[misc,assignment]
except ImportError:
    EMAIL_QUEUE_AVAILABLE = False
    EmailQueueManager = None  # type: ignore[misc,assignment]
    EmailType = None  # type: ignore[misc,assignment]

# Conditional import of Google Calendar client
if settings.GOOGLE_CALENDAR_ENABLED:
    try:
        from mcp_server.utils.google_calendar import (
            GoogleCalendarClient,
            GoogleCalendarError,
        )
    except ImportError:
        logging.warning(
            "Google Calendar client not available - calendar integration disabled"
        )
        GoogleCalendarClient = None  # type: ignore[misc,assignment]
        GoogleCalendarError = Exception  # type: ignore[misc,assignment]
else:
    GoogleCalendarClient = None  # type: ignore[misc,assignment]
    GoogleCalendarError = Exception  # type: ignore[misc,assignment]

# Setup module logger
logger = setup_logging("bookings_tools")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_calendar_client() -> Any | None:
    """Get Google Calendar client instance if enabled.

    Returns:
        GoogleCalendarClient instance or None if disabled.
    """
    if not settings.GOOGLE_CALENDAR_ENABLED or not GoogleCalendarClient:
        return None

    try:
        return GoogleCalendarClient(
            credentials_path=settings.GOOGLE_CALENDAR_CREDENTIALS_PATH,
            calendar_id=settings.GOOGLE_CALENDAR_ID,
            timezone=settings.GOOGLE_CALENDAR_TIMEZONE,
        )
    except Exception as exc:
        logger.exception(f"Failed to initialize Google Calendar client: {exc}")
        return None


def _format_datetime_iso(booking_date: str, booking_time: str) -> str:
    """Format booking date and time to ISO 8601 string.

    Args:
        booking_date: Date in YYYY-MM-DD format.
        booking_time: Time in HH:MM format.

    Returns:
        ISO 8601 datetime string with timezone.

    Example:
        >>> _format_datetime_iso("2025-10-12", "15:00")
        "2025-10-12T15:00:00-05:00"
    """
    # Combine date and time
    dt_str = f"{booking_date}T{booking_time}:00"

    # Validate datetime format
    _ = datetime.fromisoformat(dt_str)  # Validates format, raises ValueError if invalid

    # Add timezone offset (simplified - should use timezone library in production)
    # For now, assume timezone from settings (e.g., America/New_York = UTC-5 or UTC-4)
    # In production, use pytz or zoneinfo for proper timezone handling
    return f"{dt_str}{_get_timezone_offset()}"


def _get_timezone_offset() -> str:
    """Get timezone offset string for current timezone.

    Returns:
        Timezone offset string (e.g., "-05:00", "+01:00").

    Note:
        This is a simplified implementation. In production,
        use proper timezone library (pytz, zoneinfo).
    """
    # Simplified mapping - should use pytz/zoneinfo in production
    timezone_offsets = {
        # North America
        "America/New_York": "-05:00",  # EST (UTC-5 winter, UTC-4 summer)
        "America/Chicago": "-06:00",  # CST (UTC-6 winter, UTC-5 summer)
        "America/Denver": "-07:00",  # MST (UTC-7 winter, UTC-6 summer)
        "America/Los_Angeles": "-08:00",  # PST (UTC-8 winter, UTC-7 summer)

        # Central America (no DST - always UTC-6)
        "America/Costa_Rica": "-06:00",  # CST (UTC-6 year-round)
        "America/Guatemala": "-06:00",  # CST (UTC-6 year-round)
        "America/El_Salvador": "-06:00",  # CST (UTC-6 year-round)
        "America/Tegucigalpa": "-06:00",  # Honduras CST (UTC-6 year-round)
        "America/Managua": "-06:00",  # Nicaragua CST (UTC-6 year-round)
        "America/Panama": "-05:00",  # EST (UTC-5 year-round)

        # Europe
        "Europe/Madrid": "+01:00",  # CET (UTC+1 winter, UTC+2 summer)
        "Europe/London": "+00:00",  # GMT (UTC+0 winter, UTC+1 summer)

        # Other
        "UTC": "+00:00",
    }
    return timezone_offsets.get(settings.GOOGLE_CALENDAR_TIMEZONE, "-06:00")  # Default Costa Rica


def _enqueue_email(
    email_type: str,
    booking_data: dict[str, Any],
    calendar_link: str | None = None,
    old_date: str | None = None,
    old_time: str | None = None,
) -> None:
    """Enqueue email notification for booking event.

    Args:
        email_type: Type of email (booking_created, booking_cancelled, etc.)
        booking_data: Booking details dict.
        calendar_link: Google Calendar event link (optional).
        old_date: Old date for rescheduled bookings (optional).
        old_time: Old time for rescheduled bookings (optional).

    Note:
        This is a fire-and-forget operation. Failures are logged but don't
        block booking operations.
    """
    if not EMAIL_QUEUE_AVAILABLE or not EmailQueueManager:
        logger.debug("Email queue not available - skipping email notification")
        return

    try:
        queue_manager = EmailQueueManager()

        # Build template context based on email type
        context = {
            "customer_name": booking_data.get("customer_name", "Cliente"),
            "booking_id": booking_data.get("booking_id") or booking_data.get("id"),
            "service_type": booking_data.get("service_type", "Servicio"),
            "booking_date": booking_data.get("booking_date", ""),
            "booking_time": booking_data.get("booking_time", ""),
            "duration_minutes": booking_data.get("duration_minutes", 60),
            "google_calendar_link": calendar_link,
        }

        # Add specific fields for different email types
        if email_type == "booking_cancelled":
            context["cancellation_reason"] = booking_data.get("cancellation_reason")
        elif email_type == "booking_rescheduled":
            context["old_date"] = old_date
            context["old_time"] = old_time
            context["new_date"] = booking_data.get("booking_date")
            context["new_time"] = booking_data.get("booking_time")

        # Enqueue email (rendered by worker using templates)
        email_id = queue_manager.enqueue_email(
            email_type=EmailType(email_type),
            recipient_email=booking_data["customer_email"],
            recipient_name=booking_data.get("customer_name"),
            subject=f"Confirmación: {booking_data.get('service_type', 'Servicio')}",
            body_html="",  # Will be rendered by worker from template
            template_context=context,
            booking_id=booking_data.get("booking_id") or booking_data.get("id"),
            priority=5,
        )

        logger.info(f"📧 Email queued: type={email_type}, email_id={email_id}")

    except Exception as exc:
        logger.warning(f"Failed to enqueue email notification: {exc}")
        # Don't raise - email is optional, shouldn't block booking


# ============================================================================
# CORE BOOKING FUNCTIONS
# ============================================================================


def create_booking(
    customer_name: str,
    customer_email: str,
    customer_phone: str,
    service_type: str,
    booking_date: str,  # YYYY-MM-DD
    booking_time: str,  # HH:MM
    duration_minutes: int = 60,
    notes: str = "",
) -> dict[str, Any]:
    """Create a new booking/reservation.

    Creates appointment in database and optionally in Google Calendar.

    Args:
        customer_name: Customer full name.
        customer_email: Customer email address.
        customer_phone: Customer phone number.
        service_type: Type of service being booked.
        booking_date: Booking date in YYYY-MM-DD format.
        booking_time: Booking time in HH:MM format (24-hour).
        duration_minutes: Appointment duration (default: 60).
        notes: Additional notes/comments (optional).

    Returns:
        Dict with booking details:
            {
                "booking_id": int,
                "status": "confirmed",
                "google_calendar_event_id": str | None,
                "google_calendar_link": str | None,
                "booking_date": str,
                "booking_time": str,
                "duration_minutes": int
            }

    Raises:
        ValueError: If validation fails or slot unavailable.
        RuntimeError: If database or calendar operation fails.

    Example:
        >>> booking = create_booking(
        ...     customer_name="Juan Pérez",
        ...     customer_email="juan@example.com",
        ...     customer_phone="555-1234",
        ...     service_type="consultation",
        ...     booking_date="2025-10-12",
        ...     booking_time="15:00",
        ...     duration_minutes=60
        ... )
        >>> print(booking["booking_id"])
        1234
    """
    logger.info(
        f"Creating booking for {customer_email} on {booking_date} at {booking_time}"
    )

    # Validate availability using database function
    try:
        availability_check = fetchone(
            f"SELECT {settings.SCHEMA_NAME}.is_slot_available(%s, %s, %s) as available",
            (booking_date, booking_time, duration_minutes),
        )

        if not availability_check or not availability_check["available"]:
            raise ValueError(
                f"Time slot {booking_date} at {booking_time} is not available"
            )

        logger.debug("Availability check passed")

    except Exception as exc:
        logger.exception(f"Availability check failed: {exc}")
        raise ValueError(f"Could not verify availability: {exc}") from exc

    # Create Google Calendar event if enabled
    calendar_event_id = None
    calendar_link = None

    if settings.GOOGLE_CALENDAR_ENABLED:
        try:
            calendar_client = _get_calendar_client()
            if calendar_client:
                # Format times for Google Calendar
                start_datetime = _format_datetime_iso(booking_date, booking_time)
                end_time = (
                    datetime.fromisoformat(f"{booking_date}T{booking_time}:00")
                    + timedelta(minutes=duration_minutes)
                ).strftime("%H:%M")
                end_datetime = _format_datetime_iso(booking_date, end_time)

                # Create event
                event = calendar_client.create_event(
                    summary=f"{service_type} - {customer_name}",
                    description=f"Service: {service_type}\nCustomer: {customer_name}\nNotes: {notes}",
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                    attendee_email=customer_email,
                )

                calendar_event_id = event.event_id
                calendar_link = event.html_link

                logger.info(f"Google Calendar event created: {calendar_event_id}")

        except Exception as exc:
            logger.warning(f"Failed to create Google Calendar event: {exc}")
            # Continue anyway - calendar is optional

    # Insert into database
    try:
        insert_sql = f"""
        INSERT INTO {settings.SCHEMA_NAME}.appointments
        (customer_name, customer_email, customer_phone, service_type,
         booking_date, booking_time, duration_minutes, notes,
         google_calendar_event_id, google_calendar_link, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed')
        RETURNING id, status, created_at
        """

        result = fetchone(
            insert_sql,
            (
                customer_name,
                customer_email,
                customer_phone,
                service_type,
                booking_date,
                booking_time,
                duration_minutes,
                notes,
                calendar_event_id,
                calendar_link,
            ),
            commit=True,  # INSERT requires commit
        )

        if not result:
            raise RuntimeError("Failed to create booking - no result returned")

        booking_id = result["id"]
        logger.info(f"✅ Booking created successfully: ID={booking_id}")

        booking_response = {
            "booking_id": booking_id,
            "status": result["status"],
            "google_calendar_event_id": calendar_event_id,
            "google_calendar_link": calendar_link,
            "booking_date": booking_date,
            "booking_time": booking_time,
            "duration_minutes": duration_minutes,
            "created_at": str(result["created_at"]),
        }

        # Enqueue confirmation email
        _enqueue_email(
            email_type="booking_created",
            booking_data={
                "booking_id": booking_id,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "service_type": service_type,
                "booking_date": booking_date,
                "booking_time": booking_time,
                "duration_minutes": duration_minutes,
            },
            calendar_link=calendar_link,
        )

        return booking_response

    except Exception as exc:
        logger.exception(f"Failed to create booking in database: {exc}")

        # Cleanup: Delete calendar event if it was created
        if calendar_event_id and calendar_client:
            try:
                calendar_client.delete_event(
                    calendar_event_id, send_notifications=False
                )
                logger.info("Rolled back Google Calendar event")
            except Exception as cleanup_exc:
                logger.warning(f"Failed to rollback calendar event: {cleanup_exc}")

        raise RuntimeError(f"Failed to create booking: {exc}") from exc


def cancel_booking(
    booking_id: int,
    cancellation_reason: str = "",
) -> dict[str, Any]:
    """Cancel an existing booking.

    Updates database status and deletes Google Calendar event.

    Args:
        booking_id: ID of booking to cancel.
        cancellation_reason: Reason for cancellation (optional).

    Returns:
        Dict with cancellation confirmation:
            {
                "booking_id": int,
                "status": "cancelled",
                "cancelled_at": str,
                "calendar_event_deleted": bool
            }

    Raises:
        ValueError: If booking not found or already cancelled.
        RuntimeError: If cancellation fails.

    Example:
        >>> result = cancel_booking(1234, "Customer requested")
        >>> assert result["status"] == "cancelled"
    """
    logger.info(f"Cancelling booking: {booking_id}")

    # Fetch booking details
    try:
        booking = fetchone(
            f"SELECT * FROM {settings.SCHEMA_NAME}.appointments WHERE id = %s",
            (booking_id,),
        )

        if not booking:
            raise ValueError(f"Booking {booking_id} not found")

        if booking["status"] == "cancelled":
            raise ValueError(f"Booking {booking_id} is already cancelled")

        logger.debug(
            f"Found booking: {booking['customer_name']} on {booking['booking_date']}"
        )

    except ValueError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to fetch booking: {exc}")
        raise RuntimeError(f"Could not fetch booking {booking_id}: {exc}") from exc

    # Delete Google Calendar event if exists
    calendar_deleted = False
    if booking["google_calendar_event_id"]:
        try:
            calendar_client = _get_calendar_client()
            if calendar_client:
                calendar_client.delete_event(booking["google_calendar_event_id"])
                calendar_deleted = True
                logger.info(
                    f"Google Calendar event deleted: {booking['google_calendar_event_id']}"
                )
        except Exception as exc:
            logger.warning(f"Failed to delete calendar event: {exc}")
            # Continue anyway - calendar is optional

    # Update database
    try:
        update_sql = f"""
        UPDATE {settings.SCHEMA_NAME}.appointments
        SET status = 'cancelled',
            cancellation_reason = %s,
            cancelled_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING cancelled_at
        """

        result = fetchone(update_sql, (cancellation_reason, booking_id), commit=True)  # UPDATE requires commit

        if not result:
            raise RuntimeError("Failed to cancel booking - no result returned")

        logger.info(f"✅ Booking cancelled successfully: ID={booking_id}")

        cancellation_response = {
            "booking_id": booking_id,
            "status": "cancelled",
            "cancelled_at": str(result["cancelled_at"]),
            "calendar_event_deleted": calendar_deleted,
        }

        # Enqueue cancellation email
        _enqueue_email(
            email_type="booking_cancelled",
            booking_data={
                "booking_id": booking_id,
                "customer_name": booking["customer_name"],
                "customer_email": booking["customer_email"],
                "service_type": booking["service_type"],
                "booking_date": str(booking["booking_date"]),
                "booking_time": str(booking["booking_time"]),
                "cancellation_reason": cancellation_reason,
            },
        )

        return cancellation_response

    except Exception as exc:
        logger.exception(f"Failed to cancel booking in database: {exc}")
        raise RuntimeError(f"Failed to cancel booking: {exc}") from exc


def reschedule_booking(
    booking_id: int,
    new_date: str,  # YYYY-MM-DD
    new_time: str,  # HH:MM
) -> dict[str, Any]:
    """Reschedule an existing booking to a new date/time.

    Updates database and Google Calendar event.

    Args:
        booking_id: ID of booking to reschedule.
        new_date: New booking date in YYYY-MM-DD format.
        new_time: New booking time in HH:MM format.

    Returns:
        Dict with updated booking details:
            {
                "booking_id": int,
                "status": "rescheduled",
                "new_date": str,
                "new_time": str,
                "calendar_event_updated": bool
            }

    Raises:
        ValueError: If booking not found, slot unavailable, or invalid status.
        RuntimeError: If reschedule operation fails.

    Example:
        >>> result = reschedule_booking(1234, "2025-10-15", "14:00")
        >>> assert result["new_date"] == "2025-10-15"
    """
    logger.info(f"Rescheduling booking {booking_id} to {new_date} at {new_time}")

    # Fetch booking details
    try:
        booking = fetchone(
            f"SELECT * FROM {settings.SCHEMA_NAME}.appointments WHERE id = %s",
            (booking_id,),
        )

        if not booking:
            raise ValueError(f"Booking {booking_id} not found")

        if booking["status"] in ("cancelled", "completed"):
            raise ValueError(f"Cannot reschedule {booking['status']} booking")

        logger.debug(f"Found booking: {booking['customer_name']}")

    except ValueError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to fetch booking: {exc}")
        raise RuntimeError(f"Could not fetch booking {booking_id}: {exc}") from exc

    # Check availability of new slot
    try:
        availability_check = fetchone(
            f"SELECT {settings.SCHEMA_NAME}.is_slot_available(%s, %s, %s) as available",
            (new_date, new_time, booking["duration_minutes"]),
        )

        if not availability_check or not availability_check["available"]:
            raise ValueError(f"Time slot {new_date} at {new_time} is not available")

        logger.debug("New slot is available")

    except ValueError:
        raise
    except Exception as exc:
        logger.exception(f"Availability check failed: {exc}")
        raise RuntimeError(f"Could not verify availability: {exc}") from exc

    # Update Google Calendar event if exists
    calendar_updated = False
    if booking["google_calendar_event_id"]:
        try:
            calendar_client = _get_calendar_client()
            if calendar_client:
                # Format new times
                start_datetime = _format_datetime_iso(new_date, new_time)
                end_time = (
                    datetime.fromisoformat(f"{new_date}T{new_time}:00")
                    + timedelta(minutes=booking["duration_minutes"])
                ).strftime("%H:%M")
                end_datetime = _format_datetime_iso(new_date, end_time)

                calendar_client.update_event(
                    event_id=booking["google_calendar_event_id"],
                    start_datetime=start_datetime,
                    end_datetime=end_datetime,
                )

                calendar_updated = True
                logger.info(
                    f"Google Calendar event updated: {booking['google_calendar_event_id']}"
                )

        except Exception as exc:
            logger.warning(f"Failed to update calendar event: {exc}")
            # Continue anyway - calendar is optional

    # Update database
    try:
        update_sql = f"""
        UPDATE {settings.SCHEMA_NAME}.appointments
        SET booking_date = %s,
            booking_time = %s,
            status = 'rescheduled'
        WHERE id = %s
        RETURNING booking_date, booking_time, status
        """

        result = fetchone(update_sql, (new_date, new_time, booking_id), commit=True)  # UPDATE requires commit

        if not result:
            raise RuntimeError("Failed to reschedule booking - no result returned")

        logger.info(f"✅ Booking rescheduled successfully: ID={booking_id}")

        reschedule_response = {
            "booking_id": booking_id,
            "status": result["status"],
            "new_date": str(result["booking_date"]),
            "new_time": str(result["booking_time"]),
            "calendar_event_updated": calendar_updated,
        }

        # Enqueue rescheduled email
        _enqueue_email(
            email_type="booking_rescheduled",
            booking_data={
                "booking_id": booking_id,
                "customer_name": booking["customer_name"],
                "customer_email": booking["customer_email"],
                "service_type": booking["service_type"],
                "booking_date": new_date,
                "booking_time": new_time,
            },
            calendar_link=booking.get("google_calendar_link"),
            old_date=str(booking["booking_date"]),
            old_time=str(booking["booking_time"]),
        )

        return reschedule_response

    except Exception as exc:
        logger.exception(f"Failed to reschedule booking in database: {exc}")
        raise RuntimeError(f"Failed to reschedule booking: {exc}") from exc


def get_available_slots(
    service_type: str,
    date: str,  # YYYY-MM-DD
    duration_minutes: int = 60,
) -> dict[str, Any]:
    """Get available time slots for a specific date and service.

    Checks business hours, existing bookings, and blocked times.

    Args:
        service_type: Type of service (used for duration lookup).
        date: Date to check in YYYY-MM-DD format.
        duration_minutes: Required appointment duration (default: 60).

    Returns:
        Dict with available slots and metadata:
        {
            "date": str,
            "service_type": str,
            "available_slots": [
                {"time": "09:00", "available": true},
                {"time": "09:30", "available": true},
                ...
            ],
            "count": int,
            "business_hours": {
                "open_time": str,
                "close_time": str
            }
        }

    Example:
        >>> result = get_available_slots("consultation", "2025-10-12", 60)
        >>> available = [s for s in result["available_slots"] if s["available"]]
        >>> print(f"Found {len(available)} available slots")
    """
    logger.info(f"Getting available slots for {service_type} on {date}")

    # Get day of week (0=Monday, 6=Sunday)
    try:
        dt = datetime.fromisoformat(date)
        day_of_week = dt.weekday()  # Python: 0=Monday, 6=Sunday
        logger.debug(f"Date {date} is day {day_of_week} of week")

    except ValueError as exc:
        logger.exception(f"Invalid date format: {date}")
        raise ValueError(f"Invalid date format: {date}") from exc

    # Get business hours for this day
    try:
        business_hours = fetchone(
            f"""
            SELECT open_time, close_time
            FROM {settings.SCHEMA_NAME}.business_hours
            WHERE day_of_week = %s AND active = true
            """,
            (day_of_week,),
        )

        if not business_hours:
            logger.info(f"No business hours for day {day_of_week} - closed")
            return {
                "date": date,
                "service_type": service_type,
                "available_slots": [],
                "count": 0,
                "business_hours": None,
            }

        open_time = business_hours["open_time"]
        close_time = business_hours["close_time"]

        logger.debug(f"Business hours: {open_time} - {close_time}")

    except Exception as exc:
        logger.exception(f"Failed to fetch business hours: {exc}")
        raise RuntimeError(f"Could not fetch business hours: {exc}") from exc

    # Generate time slots based on interval
    slots = []
    current_time = datetime.combine(dt, open_time)
    end_time = datetime.combine(dt, close_time)
    interval = timedelta(minutes=settings.BOOKING_SLOT_INTERVAL_MINUTES)

    while current_time < end_time:
        time_str = current_time.strftime("%H:%M")

        # Check if slot is available using database function
        try:
            availability = fetchone(
                f"SELECT {settings.SCHEMA_NAME}.is_slot_available(%s, %s, %s) as available",
                (date, time_str, duration_minutes),
            )

            is_available = availability["available"] if availability else False

            slots.append({"time": time_str, "available": is_available})

        except Exception as exc:
            logger.warning(f"Failed to check availability for {time_str}: {exc}")
            slots.append({"time": time_str, "available": False})

        current_time += interval

    available_count = sum(1 for s in slots if s["available"])
    logger.info(f"Generated {len(slots)} time slots for {date} ({available_count} available)")

    return {
        "date": date,
        "service_type": service_type,
        "available_slots": slots,
        "count": available_count,
        "business_hours": {
            "open_time": str(open_time),
            "close_time": str(close_time),
        },
    }


def get_booking_by_id(booking_id: int) -> dict[str, Any] | None:
    """Get booking details by ID.

    Args:
        booking_id: Booking ID to fetch.

    Returns:
        Booking details dict or None if not found:
            {
                "id": int,
                "customer_name": str,
                "customer_email": str,
                "service_type": str,
                "booking_date": str,
                "booking_time": str,
                "duration_minutes": int,
                "status": str,
                ...
            }

    Example:
        >>> booking = get_booking_by_id(1234)
        >>> if booking:
        ...     print(f"{booking['customer_name']} on {booking['booking_date']}")
    """
    logger.debug(f"Fetching booking by ID: {booking_id}")

    try:
        booking = fetchone(
            f"""
            SELECT id, customer_name, customer_email, customer_phone,
                   service_type, booking_date, booking_time, duration_minutes,
                   status, notes, google_calendar_link,
                   created_at, updated_at
            FROM {settings.SCHEMA_NAME}.appointments
            WHERE id = %s
            """,
            (booking_id,),
        )

        if booking:
            # Convert date/time to strings
            booking["booking_date"] = str(booking["booking_date"])
            booking["booking_time"] = str(booking["booking_time"])
            booking["created_at"] = str(booking["created_at"])
            booking["updated_at"] = str(booking["updated_at"])

            logger.debug(f"Found booking: {booking['customer_name']}")
        else:
            logger.debug(f"Booking {booking_id} not found")

        return booking

    except Exception as exc:
        logger.exception(f"Failed to fetch booking: {exc}")
        raise RuntimeError(f"Could not fetch booking {booking_id}: {exc}") from exc


def list_customer_bookings(
    customer_email: str,
    include_cancelled: bool = False,
) -> dict[str, Any]:
    """List all bookings for a customer.

    Args:
        customer_email: Customer email address.
        include_cancelled: Include cancelled bookings (default: False).

    Returns:
        Dict with booking list, total count, and active count:
        {
            "customer_email": str,
            "bookings": list[dict],
            "count": int,
            "active_count": int,
            "future_count": int (bookings not yet passed)
        }

    Example:
        >>> result = list_customer_bookings("juan@example.com")
        >>> print(f"Found {result['count']} bookings ({result['active_count']} active)")
        >>> for booking in result['bookings']:
        ...     print(f"{booking['service_type']} on {booking['booking_date']}")
    """
    logger.info(f"Listing bookings for customer: {customer_email}")

    try:
        # Build status filter
        status_filter = "" if include_cancelled else "AND status != 'cancelled'"

        query = f"""
        SELECT id, customer_name, customer_email, service_type,
               booking_date, booking_time, duration_minutes,
               status, google_calendar_link, created_at
        FROM {settings.SCHEMA_NAME}.appointments
        WHERE customer_email = %s
        {status_filter}
        ORDER BY booking_date DESC, booking_time DESC
        """

        bookings = fetchall(query, (customer_email,))

        # Get current datetime for past/future filtering
        from datetime import datetime, date as date_type, time as time_type
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()

        # Convert dates to strings and add is_past flag
        for booking in bookings:
            booking["booking_date"] = str(booking["booking_date"])
            booking["booking_time"] = str(booking["booking_time"])
            booking["created_at"] = str(booking["created_at"])

            # Parse booking date and time
            try:
                booking_date = datetime.fromisoformat(str(booking["booking_date"])).date()
                booking_time = datetime.fromisoformat(f"1970-01-01T{booking['booking_time']}").time()

                # Determine if booking is in the past
                is_past = (
                    booking_date < current_date or
                    (booking_date == current_date and booking_time < current_time)
                )
                booking["is_past"] = is_past

            except (ValueError, AttributeError) as exc:
                logger.warning(f"Could not parse booking datetime: {exc}")
                booking["is_past"] = False  # Default to not past if parsing fails

        # Count active bookings
        active_count = sum(1 for b in bookings if b.get("status") != "cancelled")

        # Count future bookings (not yet passed)
        future_count = sum(1 for b in bookings if not b.get("is_past", False) and b.get("status") != "cancelled")

        logger.info(
            f"Found {len(bookings)} bookings for {customer_email} "
            f"({active_count} active, {future_count} future)"
        )

        return {
            "customer_email": customer_email,
            "bookings": bookings,
            "count": len(bookings),
            "active_count": active_count,
            "future_count": future_count,
        }

    except Exception as exc:
        logger.exception(f"Failed to list bookings: {exc}")
        raise RuntimeError(
            f"Could not list bookings for {customer_email}: {exc}"
        ) from exc


# ============================================================================
# DATA RETRIEVAL FUNCTIONS (MCP Tools)
# ============================================================================


def get_services(active_only: bool = True) -> dict[str, Any]:
    """Get available booking services from database.

    Retrieves service types from test.service_types table.
    Used by BookingAgent to display current services dynamically via MCP tool.

    Args:
        active_only: Only return active services (default: True).

    Returns:
        Dict with services list:
        {
            "services": [
                {
                    "name": "consultation",
                    "display_name": "Consulta General",
                    "description": "...",
                    "duration_minutes": 30,
                    "price": 50.00,
                    "color": "#4A90E2",
                    "icon": "chat"
                },
                ...
            ],
            "total": 5
        }

    Example:
        >>> services = get_services(active_only=True)
        >>> print(f"Found {services['total']} services")
        # Found 5 services
    """
    logger.info("Fetching services from database")

    try:
        query = f"""
        SELECT
            name,
            display_name,
            description,
            duration_minutes,
            price,
            color,
            icon
        FROM {settings.SCHEMA_NAME}.service_types
        WHERE active = %s
        ORDER BY display_name
        """

        rows = fetchall(query, (active_only,))

        services = [
            {
                "name": row["name"],
                "display_name": row["display_name"],
                "description": row["description"],
                "duration_minutes": row["duration_minutes"],
                "price": float(row["price"]),
                "color": row["color"],
                "icon": row["icon"],
            }
            for row in rows
        ]

        logger.info(f"✅ Loaded {len(services)} services from database")

        return {"services": services, "total": len(services)}

    except Exception as exc:
        logger.exception(f"Failed to fetch services: {exc}")
        raise RuntimeError(f"Could not fetch services: {exc}") from exc


def get_business_hours() -> dict[str, Any]:
    """Get business operating hours from database.

    Retrieves hours from test.business_hours table.
    Used by GeneralAgent to display current hours dynamically via MCP tool.

    Returns:
        Dict with hours by day:
        {
            "hours": {
                "Monday": {"open": "09:00", "close": "18:00"},
                "Tuesday": {"open": "09:00", "close": "18:00"},
                ...
            },
            "timezone": "America/New_York",
            "days_count": 6
        }

    Example:
        >>> hours = get_business_hours()
        >>> print(hours["hours"]["Monday"])
        # {"open": "09:00", "close": "18:00"}
    """
    logger.info("Fetching business hours from database")

    try:
        query = f"""
        SELECT
            day_of_week,
            open_time,
            close_time
        FROM {settings.SCHEMA_NAME}.business_hours
        WHERE active = true
        ORDER BY day_of_week
        """

        rows = fetchall(query)

        days_map = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        hours = {}

        for row in rows:
            day_index = row["day_of_week"]
            if 0 <= day_index < len(days_map):
                day_name = days_map[day_index]
                hours[day_name] = {
                    "open": str(row["open_time"]),
                    "close": str(row["close_time"]),
                }

        logger.info(f"✅ Loaded business hours for {len(hours)} days")

        return {
            "hours": hours,
            "timezone": settings.GOOGLE_CALENDAR_TIMEZONE,
            "days_count": len(hours),
        }

    except Exception as exc:
        logger.exception(f"Failed to fetch business hours: {exc}")
        raise RuntimeError(f"Could not fetch business hours: {exc}") from exc
