"""Booking MCP Tool Handlers.

Async wrappers for booking MCP tools with Context support.
Separates MCP protocol handling from business logic.

This module provides MCP tool decorators for booking/reservation functionality:
- Create new bookings with Google Calendar integration
- Cancel existing bookings
- Reschedule appointments
- Check available time slots
- Retrieve booking details
- List customer booking history

═══════════════════════════════════════════════════════════════════════════════
🔒 SCOPE ENFORCEMENT (Gemini 2.5 Best Practice)
═══════════════════════════════════════════════════════════════════════════════

CRITICAL: All tools in this module are BOOKING-ONLY.

✅ ALLOWED uses:
   - Creating reservations
   - Checking availability
   - Modifying/canceling bookings
   - Service/schedule information
   - Booking history queries

❌ FORBIDDEN uses (redirect to appropriate agent/team):
   - Pricing/cost questions → sales team
   - Technical troubleshooting → support team
   - Company information → general info
   - Billing/payments → accounting team

Each tool returns ONLY verified data from database.
NO HALLUCINATIONS. NO INVENTED DATA.

═══════════════════════════════════════════════════════════════════════════════

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.1.0 (Gemini 2.5 Scope Enforcement)
"""

# NOTE: Do NOT add "from __future__ import annotations" here!
# It breaks FastMCP's Context parameter detection (Context becomes a string at runtime)

from datetime import datetime
from typing import Any

from mcp.server.fastmcp import Context

from tools import bookings as booking_tool
from utils.logger import setup_logging
from utils.language_context import get_current_language
from utils.mcp_i18n import mcp_info, mcp_debug, mcp_progress

# Setup logger for booking handlers
logger = setup_logging("mcp_booking_handlers")

# Global mcp instance - will be injected from server.py
mcp = None


def init_booking_handlers(mcp_instance):
    """Initialize booking handlers with MCP instance.

    Args:
        mcp_instance: FastMCP server instance to register tools with.
    """
    global mcp
    mcp = mcp_instance
    register_booking_tools()
    logger.info("✅ Booking handlers initialized successfully")


def get_booking_tool_names() -> list[str]:
    """
    Return list of registered booking tool names.

    This function provides dynamic tool discovery without hardcoding tool lists
    in client code. Tools are defined here in the handler module and exposed
    via MCP resources for client-side filtering.

    Returns:
        List of booking tool names registered in this module
    """
    return [
        "create_booking",
        "cancel_booking",
        "reschedule_booking",
        "get_available_slots",
        "get_booking_by_id",
        "list_customer_bookings",
        "get_services",
        "get_business_hours",
        # User Management Tools (v2.9 - Authentication & Registration)
        "check_user_exists",
        "create_user",
        "request_otp",
        "verify_otp",
        "update_user",
    ]


def register_booking_tools():
    """Register all booking MCP tools.

    Creates MCP tool decorators for all booking-related functionality.
    Each tool is an async wrapper around pure business logic functions.

    Implements Gemini 2.5 Scope Boundaries:
    - All tools in this module are BOOKING-ONLY (no sales, support, general queries)
    - All tools enforce language context from agents
    - All tools use MCP Context for logging/progress reporting
    - All tools return structured responses (never hallucinated data)

    Available Tools (8 total):
    ✅ create_booking: New reservations
    ✅ cancel_booking: Cancellations
    ✅ reschedule_booking: Date/time changes
    ✅ get_available_slots: Availability checking
    ✅ get_booking_by_id: Booking details
    ✅ list_customer_bookings: Customer's reservations
    ✅ get_services: Service catalog
    ✅ get_business_hours: Operating hours
    """

    @mcp.tool()  # type: ignore[union-attr]
    async def create_booking(
        ctx: Context,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        service_type: str,
        booking_date: str,
        booking_time: str,
        notes: str,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Create a new booking/reservation appointment.

        Scope: BOOKING ONLY - This tool is for creating reservations.
        Never use for sales questions, pricing inquiries, or technical support.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer wants to schedule an appointment or reservation
        ✅ Customer provides date, time, and contact information
        ✅ Customer requests specific service type (consultation, support, demo, etc.)
        ✅ Customer wants to book a time slot

        ** EXAMPLES OF VALID USE **:
        - "Quiero reservar una consulta para mañana a las 3pm"
        - "Necesito agendar soporte técnico para el lunes 15"
        - "Me gustaría una demo del producto el viernes"
        - "Puedo hacer una cita para instalación la próxima semana"

        ** DON'T USE WHEN **:
        ❌ Customer is just checking availability (use get_available_slots)
        ❌ Customer wants to modify existing booking (use reschedule_booking)
        ❌ Customer wants to cancel booking (use cancel_booking)
        ❌ Missing required information (name, email, phone, service, date, time, notes)
        ❌ Customer asks: "¿Cuánto cuesta?" or "¿Hay descuento?" → NOT booking scope

        ** WHAT IT DOES **:
        1. Validates customer information and service type
        2. Checks time slot availability
        3. Creates booking record in PostgreSQL database
        4. (Optional) Creates Google Calendar event if enabled
        5. Returns booking confirmation with ID and details

        ** GOOGLE CALENDAR INTEGRATION **:
        - If GOOGLE_CALENDAR_ENABLED=true: Creates calendar event with reminders
        - If disabled: Only creates database record (calendar event ID will be null)
        - Calendar events include: title, description, attendee email, reminders

        ** PERFORMANCE **: ~150-300ms (depending on calendar integration)

        Args:
            ctx: MCP context for logging and progress reporting.
            customer_name: Customer full name (e.g., "Juan Pérez").
            customer_email: Customer email for notifications (e.g., "juan@example.com").
            customer_phone: Customer phone number (e.g., "+1-555-0100").
            service_type: Service type identifier.
                         Valid values: consultation, technical_support, product_demo,
                         training_session, installation, custom.
            booking_date: Appointment date in YYYY-MM-DD format (e.g., "2025-10-15").
            booking_time: Appointment time in HH:MM format 24-hour (e.g., "15:00" for 3pm).
            notes: REQUIRED. Notes, reason, or purpose of the appointment.
                  This field is mandatory to understand the customer's needs.
                  Examples: "Primera consulta", "Problema con el producto X",
                  "Quiero conocer las funcionalidades".
            duration_minutes: Appointment duration in minutes (default: 60).
                             Typical values: 30, 60, 90, 120.

        Returns:
            Booking confirmation dict with:
            {
                "booking_id": int,
                "status": "confirmed",
                "customer_name": str,
                "service_type": str,
                "booking_datetime": str (ISO 8601),
                "duration_minutes": int,
                "google_calendar_event_id": str | None,
                "google_calendar_link": str | None,
                "message": str (confirmation message)
            }

        Raises:
            ValueError: If required fields are missing or invalid.
            Exception: If database or calendar operations fail.

        Example:
            >>> result = await create_booking(
            ...     ctx=ctx,
            ...     customer_name="María García",
            ...     customer_email="maria@example.com",
            ...     customer_phone="+1-555-0200",
            ...     service_type="consultation",
            ...     booking_date="2025-10-15",
            ...     booking_time="14:00",
            ...     duration_minutes=60,
            ...     notes="Primera consulta"
            ... )
            >>> print(result["booking_id"])  # 123
        """
        try:
            await mcp_info(
                ctx,
                "booking.create.info_start",
                customer_name=customer_name,
                booking_date=booking_date,
                booking_time=booking_time,
            )
            await mcp_progress(ctx, 0, 3, "booking.create.progress_validate")

            logger.info(
                f"create_booking called: customer={customer_name}, "
                f"service={service_type}, date={booking_date}, time={booking_time}"
            )

            # Call business logic
            await mcp_progress(ctx, 1, 3, "booking.create.progress_create")
            result = booking_tool.create_booking(
                customer_name=customer_name,
                customer_email=customer_email,
                customer_phone=customer_phone,
                service_type=service_type,
                booking_date=booking_date,
                booking_time=booking_time,
                duration_minutes=duration_minutes,
                notes=notes,
            )

            await mcp_progress(ctx, 2, 3, "booking.create.progress_success")

            if result.get("google_calendar_event_id"):
                await mcp_info(
                    ctx,
                    "booking.create.info_with_calendar",
                    booking_id=result['booking_id'],
                )
            else:
                await mcp_info(
                    ctx,
                    "booking.create.info_without_calendar",
                    booking_id=result['booking_id'],
                )

            await mcp_progress(ctx, 3, 3, "booking.create.progress_ready")
            logger.info(f"Booking created successfully: ID={result.get('booking_id')}")

            return result

        except ValueError as e:
            await mcp_debug(
                ctx,
                "booking.create.error_validation",
                error=str(e),
            )
            logger.error(f"Validation error in create_booking: {str(e)}")
            raise

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.create.error_general",
                error=str(e),
            )
            logger.exception(f"Error in create_booking: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def cancel_booking(
        ctx: Context,
        booking_id: int,
        cancellation_reason: str = "",
    ) -> dict[str, Any]:
        """Cancel an existing booking/reservation.

        Scope: BOOKING ONLY - Use only for canceling confirmed reservations.
        If customer needs help with something else, redirect appropriately.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer wants to cancel their appointment
        ✅ Customer provides booking ID or you retrieved it from list_customer_bookings
        ✅ Customer says "cancelar mi cita", "no puedo asistir", "eliminar reserva"

        ** EXAMPLES OF VALID USE **:
        - "Necesito cancelar mi cita del viernes"
        - "No podré asistir a la consulta"
        - "Quiero cancelar la reserva #123"
        - "Elimina mi appointment por favor"

        ** DON'T USE WHEN **:
        ❌ Customer wants to change date/time (use reschedule_booking instead)
        ❌ Booking ID is unknown (use list_customer_bookings first)
        ❌ Customer is just asking about cancellation policy
        ❌ Customer asks: "¿Hay penalidad por cancelación?" → NOT a cancellation action

        ** WHAT IT DOES **:
        1. Marks booking as cancelled in database (soft delete)
        2. Deletes Google Calendar event if it exists
        3. Records cancellation timestamp and reason
        4. Returns cancellation confirmation

        ** PERFORMANCE **: ~100-200ms (depending on calendar integration)

        Args:
            ctx: MCP context for logging and progress reporting.
            booking_id: The booking ID to cancel (obtained from create_booking or list_customer_bookings).
            cancellation_reason: Optional reason for cancellation (default: "").
                                Useful for analytics and customer service.

        Returns:
            Cancellation confirmation dict with:
            {
                "booking_id": int,
                "status": "cancelled",
                "cancelled_at": str (ISO 8601 timestamp),
                "cancellation_reason": str,
                "message": str (confirmation message)
            }

        Raises:
            ValueError: If booking not found or already cancelled.
            Exception: If database or calendar operations fail.

        Example:
            >>> result = await cancel_booking(
            ...     ctx=ctx,
            ...     booking_id=123,
            ...     cancellation_reason="Cliente tuvo emergencia familiar"
            ... )
            >>> print(result["status"])  # "cancelled"
        """
        try:
            await mcp_info(ctx, "booking.cancel.info_start", booking_id=booking_id)
            await mcp_progress(ctx, 0, 2, "booking.cancel.progress_validate")

            logger.info(
                f"cancel_booking called: booking_id={booking_id}, reason={cancellation_reason}"
            )

            # Call business logic
            await mcp_progress(ctx, 1, 2, "booking.cancel.progress_process")
            result = booking_tool.cancel_booking(
                booking_id=booking_id,
                cancellation_reason=cancellation_reason,
            )

            await mcp_info(ctx, "booking.cancel.info_success", booking_id=booking_id)
            await mcp_progress(ctx, 2, 2, "booking.cancel.progress_complete")
            logger.info(f"Booking cancelled successfully: ID={booking_id}")

            return result

        except ValueError as e:
            await mcp_debug(
                ctx,
                "booking.cancel.error_validation",
                error=str(e),
            )
            logger.error(f"Validation error in cancel_booking: {str(e)}")
            raise

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.cancel.error_general",
                booking_id=booking_id,
                error=str(e),
            )
            logger.exception(f"Error in cancel_booking: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def reschedule_booking(
        ctx: Context,
        booking_id: int,
        new_date: str,
        new_time: str,
    ) -> dict[str, Any]:
        """Reschedule an existing booking to a new date/time.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer wants to change appointment date or time
        ✅ Customer provides new date and time
        ✅ Customer says "cambiar mi cita", "mover la reserva", "otro horario"

        ** EXAMPLES OF VALID USE **:
        - "Puedo mover mi cita del lunes al miércoles?"
        - "Necesito cambiar la hora a las 4pm"
        - "Me gustaría reprogramar para la próxima semana"
        - "Cambiar mi reserva al día 20 a las 10am"

        ** DON'T USE WHEN **:
        ❌ Customer wants to cancel (use cancel_booking)
        ❌ Customer is checking availability first (use get_available_slots)
        ❌ New time slot is not available
        ❌ Booking ID is unknown (use list_customer_bookings first)
        ❌ Booking is already cancelled (cannot reschedule cancelled appointments)

        ** WHAT IT DOES **:
        1. Validates booking exists and is not cancelled/completed
        2. Validates new time slot availability
        3. Updates booking record in database with new date/time
        4. Updates Google Calendar event if it exists
        5. Returns reschedule confirmation

        ** PERFORMANCE **: ~150-300ms (depending on calendar integration)

        Args:
            ctx: MCP context for logging and progress reporting.
            booking_id: The booking ID to reschedule (obtained from list_customer_bookings).
            new_date: New appointment date in YYYY-MM-DD format (e.g., "2025-10-20").
            new_time: New appointment time in HH:MM format 24-hour (e.g., "16:00" for 4pm).

        Returns:
            Reschedule confirmation dict with:
            {
                "booking_id": int,
                "status": "confirmed",
                "old_datetime": str (ISO 8601),
                "new_datetime": str (ISO 8601),
                "google_calendar_event_id": str | None,
                "message": str (confirmation message)
            }

        Raises:
            ValueError: If booking not found, already cancelled, or new slot unavailable.
            Exception: If database or calendar operations fail.

        Example:
            >>> result = await reschedule_booking(
            ...     ctx=ctx,
            ...     booking_id=123,
            ...     new_date="2025-10-20",
            ...     new_time="16:00"
            ... )
            >>> print(result["new_datetime"])  # "2025-10-20T16:00:00-05:00"
        """
        try:
            await mcp_info(
                ctx,
                "booking.reschedule.info_start",
                booking_id=booking_id,
                new_date=new_date,
                new_time=new_time,
            )
            await mcp_progress(ctx, 0, 4, "booking.reschedule.progress_validate_status")

            logger.info(
                f"reschedule_booking called: booking_id={booking_id}, new_date={new_date}, new_time={new_time}"
            )

            # First, fetch booking to check status (defensive validation)
            await mcp_progress(ctx, 1, 4, "booking.reschedule.progress_fetch")
            booking = booking_tool.get_booking_by_id(booking_id)

            if not booking:
                await mcp_debug(
                    ctx,
                    "booking.reschedule.error_not_found",
                    booking_id=booking_id,
                )
                logger.error(f"Booking {booking_id} not found")
                raise ValueError(f"Booking {booking_id} not found")

            # Check if booking is in a valid state for rescheduling
            current_status = booking.get("status")
            if current_status in ("cancelled", "completed", "no_show"):
                error_msg = f"Cannot reschedule {current_status} booking (ID: {booking_id})"
                await mcp_debug(ctx, "booking.reschedule.error_not_found", booking_id=booking_id)
                logger.error(error_msg)
                raise ValueError(error_msg)

            await mcp_info(
                ctx,
                "booking.reschedule.info_status_validated",
                status=current_status,
                customer_name=booking.get('customer_name', 'Unknown'),
            )

            # Call business logic
            await mcp_progress(ctx, 2, 4, "booking.reschedule.progress_check_availability")
            result = booking_tool.reschedule_booking(
                booking_id=booking_id,
                new_date=new_date,
                new_time=new_time,
            )

            await mcp_progress(ctx, 3, 4, "booking.reschedule.progress_update")
            await mcp_info(
                ctx,
                "booking.reschedule.info_success",
                booking_id=booking_id,
                new_date=new_date,
                new_time=new_time,
            )
            await mcp_progress(ctx, 4, 4, "booking.reschedule.progress_complete")
            logger.info(f"Booking rescheduled successfully: ID={booking_id}")

            return result

        except ValueError as e:
            await mcp_debug(
                ctx,
                "booking.reschedule.error_validation",
                error=str(e),
            )
            logger.error(f"Validation error in reschedule_booking: {str(e)}")
            raise

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.reschedule.error_general",
                booking_id=booking_id,
                error=str(e),
            )
            logger.exception(f"Error in reschedule_booking: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def get_available_slots(
        ctx: Context,
        service_type: str,
        date: str,
        duration_minutes: int = 60,
    ) -> dict[str, Any]:
        """Get available time slots for booking on a specific date.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer asks about availability for a date
        ✅ Customer wants to see open time slots
        ✅ Before creating/rescheduling a booking to check availability
        ✅ Customer says "qué horarios hay", "está disponible el...", "cuándo puedo"

        ** EXAMPLES OF VALID USE **:
        - "Qué horarios tienen disponibles el lunes?"
        - "Está libre el viernes a las 2pm?"
        - "Cuándo puedo agendar una consulta esta semana?"
        - "Hay espacio el día 15?"

        ** DON'T USE WHEN **:
        ❌ Customer already decided on a time (use create_booking directly)
        ❌ Customer wants to list their existing bookings (use list_customer_bookings)

        ** WHAT IT DOES **:
        1. Checks business hours for the requested date
        2. Finds all existing bookings for that day
        3. Calculates available time slots based on:
           - Business operating hours
           - Existing appointments
           - Blocked times (holidays, maintenance)
           - Service duration
        4. Returns list of available slots with start/end times

        ** PERFORMANCE **: ~50-100ms (database query only)

        Args:
            ctx: MCP context for logging and progress reporting.
            service_type: Service type to check availability for.
                         Valid values: consultation, technical_support, product_demo,
                         training_session, installation, custom.
            date: Date to check in YYYY-MM-DD format (e.g., "2025-10-15").
            duration_minutes: Required duration in minutes (default: 60).
                             Used to calculate if slot is long enough.

        Returns:
            Available slots dict with:
            {
                "date": str (YYYY-MM-DD),
                "service_type": str,
                "available_slots": [
                    {
                        "start_time": str (HH:MM),
                        "end_time": str (HH:MM),
                        "duration_minutes": int
                    },
                    ...
                ],
                "count": int,
                "business_hours": {
                    "open_time": str (HH:MM),
                    "close_time": str (HH:MM)
                }
            }

        Raises:
            ValueError: If date is invalid or in the past.
            Exception: If database query fails.

        Example:
            >>> result = await get_available_slots(
            ...     ctx=ctx,
            ...     service_type="consultation",
            ...     date="2025-10-15",
            ...     duration_minutes=60
            ... )
            >>> for slot in result["available_slots"]:
            ...     print(f"{slot['start_time']} - {slot['end_time']}")
            # 09:00 - 10:00
            # 10:00 - 11:00
            # 14:00 - 15:00
        """
        try:
            await mcp_info(
                ctx,
                "booking.availability.info_start",
                service_type=service_type,
                date=date,
            )
            await mcp_progress(ctx, 0, 2, "booking.availability.progress_query")

            # Get current language from context (set by AgentOrchestrator)
            user_lang = get_current_language()
            logger.info(
                f"get_available_slots called: service={service_type}, date={date}, duration={duration_minutes}, lang={user_lang}"
            )

            # Call business logic with language parameter
            result = booking_tool.get_available_slots(
                service_type=service_type,
                date=date,
                duration_minutes=duration_minutes,
                user_lang=user_lang,
            )

            await mcp_progress(ctx, 1, 2, "booking.availability.progress_calculate")

            # Filter available slots with spacing logic (UX improvement)
            # This prevents showing overlapping slots (e.g., 09:00, 09:30 for 120-min service)
            all_slots = result.get("available_slots", [])

            # Step 1: Filter only available=true slots
            available_slots = [s for s in all_slots if s.get("available", False)]

            # Step 2: Apply spacing based on service duration
            # For 120-min service: show 09:00, then next at 11:00 (not 09:30, 10:00, 10:30)
            spaced_slots = []
            last_shown_time = None

            for slot in available_slots:
                try:
                    current_time = datetime.strptime(slot["time"], "%H:%M")

                    if last_shown_time is None:
                        # First slot: always show
                        spaced_slots.append({"time": slot["time"]})
                        last_shown_time = current_time
                    else:
                        # Calculate time difference from last shown slot
                        diff_minutes = (current_time - last_shown_time).total_seconds() / 60

                        if diff_minutes >= duration_minutes:
                            # Enough space from last shown slot: show this one
                            spaced_slots.append({"time": slot["time"]})
                            last_shown_time = current_time
                        # else: skip (would overlap with previously shown slot)

                except ValueError:
                    # Skip invalid time format
                    logger.warning(f"Invalid time format in slot: {slot.get('time')}")
                    continue

            result["available_slots"] = spaced_slots
            result["count"] = len(spaced_slots)

            slot_count = len(spaced_slots)
            await mcp_info(
                ctx,
                "booking.availability.info_success",
                slot_count=slot_count,
                date=date,
            )
            await mcp_progress(
                ctx,
                2,
                2,
                "booking.availability.progress_slots",
                slot_count=slot_count,
            )
            logger.info(
                f"Available slots: {slot_count} spaced slots on {date} "
                f"(from {len(available_slots)} available, {len(all_slots)} total)"
            )

            return result

        except ValueError as e:
            await mcp_debug(
                ctx,
                "booking.availability.error_validation",
                error=str(e),
            )
            logger.error(f"Validation error in get_available_slots: {str(e)}")
            raise

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.availability.error_general",
                date=date,
                error=str(e),
            )
            logger.exception(f"Error in get_available_slots: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def get_booking_by_id(
        ctx: Context,
        booking_id: int,
    ) -> dict[str, Any] | None:
        """Get detailed information about a specific booking by ID.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer asks about a specific booking using ID
        ✅ Need to verify booking details before modification
        ✅ Customer says "mi reserva número...", "booking ID...", "cita #..."

        ** EXAMPLES OF VALID USE **:
        - "Cuál es el estado de mi reserva #123?"
        - "Dame los detalles de booking 456"
        - "Información de mi cita número 789"

        ** DON'T USE WHEN **:
        ❌ Customer doesn't know booking ID (use list_customer_bookings)
        ❌ Customer wants to see all their bookings

        ** WHAT IT DOES **:
        1. Queries database for booking with given ID
        2. Returns complete booking details including:
           - Customer information
           - Service type and duration
           - Date and time
           - Status (confirmed, cancelled)
           - Google Calendar link if available

        ** PERFORMANCE **: ~20-30ms (simple database query)

        Args:
            ctx: MCP context for logging and progress reporting.
            booking_id: The booking ID to retrieve.

        Returns:
            Booking details dict if found, None if not found:
            {
                "booking_id": int,
                "customer_name": str,
                "customer_email": str,
                "customer_phone": str,
                "service_type": str,
                "booking_date": str (YYYY-MM-DD),
                "booking_time": str (HH:MM),
                "duration_minutes": int,
                "status": str ("confirmed" | "cancelled"),
                "notes": str,
                "google_calendar_event_id": str | None,
                "google_calendar_link": str | None,
                "created_at": str (ISO 8601),
                "cancelled_at": str | None (ISO 8601)
            }

        Example:
            >>> booking = await get_booking_by_id(ctx=ctx, booking_id=123)
            >>> if booking:
            ...     print(f"{booking['customer_name']} - {booking['booking_date']} at {booking['booking_time']}")
            # María García - 2025-10-15 at 14:00
        """
        try:
            await mcp_info(
                ctx,
                "booking.get_by_id.info_start",
                booking_id=booking_id,
            )
            logger.debug(f"get_booking_by_id called with booking_id={booking_id}")

            # Call business logic
            result = booking_tool.get_booking_by_id(booking_id=booking_id)

            if result:
                await mcp_info(
                    ctx,
                    "booking.get_by_id.info_found",
                    customer_name=result.get('customer_name', 'Unknown'),
                    booking_date=result.get('booking_date'),
                    booking_time=result.get('booking_time'),
                )
                logger.info(f"Booking found: ID={booking_id}")
            else:
                await mcp_info(
                    ctx,
                    "booking.get_by_id.info_not_found",
                    booking_id=booking_id,
                )
                logger.warning(f"No booking found for ID: {booking_id}")

            return result

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.get_by_id.error_general",
                booking_id=booking_id,
                error=str(e),
            )
            logger.exception(f"Error in get_booking_by_id: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def list_customer_bookings(
        ctx: Context,
        customer_email: str,
        include_cancelled: bool = False,
    ) -> dict[str, Any]:
        """List all bookings for a customer by email.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer wants to see their booking history
        ✅ Customer asks "mis citas", "mis reservas", "qué tengo agendado"
        ✅ Customer doesn't remember booking ID
        ✅ Before cancelling/rescheduling to find booking ID

        ** EXAMPLES OF VALID USE **:
        - "Cuáles son mis citas?"
        - "Muéstrame mis reservas"
        - "Qué tengo agendado esta semana?"
        - "Cuáles son mis appointments?"

        ** DON'T USE WHEN **:
        ❌ Customer wants to check general availability (use get_available_slots)
        ❌ Customer already knows booking ID (use get_booking_by_id)

        ** WHAT IT DOES **:
        1. Queries all bookings for the given email address
        2. Returns list sorted by date (newest first)
        3. Optionally includes cancelled bookings
        4. Returns booking count and summary

        ** PERFORMANCE **: ~30-50ms (indexed email query)

        Args:
            ctx: MCP context for logging and progress reporting.
            customer_email: Customer email address to search for (e.g., "maria@example.com").
            include_cancelled: Whether to include cancelled bookings (default: False).
                              Set to True to show full history including cancellations.

        Returns:
            Customer bookings dict with:
            {
                "customer_email": str,
                "bookings": [
                    {
                        "booking_id": int,
                        "service_type": str,
                        "booking_date": str (YYYY-MM-DD),
                        "booking_time": str (HH:MM),
                        "duration_minutes": int,
                        "status": str,
                        "notes": str,
                        "google_calendar_link": str | None,
                        "created_at": str (ISO 8601),
                        "is_past": bool (true if booking date/time has already passed)
                    },
                    ...
                ],
                "count": int,
                "active_count": int (non-cancelled bookings),
                "future_count": int (bookings not yet passed)
            }

            CRITICAL FOR AGENT LOGIC:
            - Use "is_past" flag to decide whether to show reschedule/cancel options
            - If is_past=true: Show booking as reference only, NO action buttons
            - If is_past=false: Show cancel/reschedule options
            - Use "future_count" to decide what message to show ("próximas citas" vs "citas pasadas")

        Example:
            >>> result = await list_customer_bookings(
            ...     ctx=ctx,
            ...     customer_email="maria@example.com",
            ...     include_cancelled=False
            ... )
            >>> print(f"Found {result['count']} bookings")
            >>> for booking in result["bookings"]:
            ...     print(f"ID: {booking['booking_id']} - {booking['booking_date']}")
            # Found 3 bookings
            # ID: 123 - 2025-10-15
            # ID: 124 - 2025-10-20
            # ID: 125 - 2025-10-25
        """
        try:
            await mcp_info(
                ctx,
                "booking.list_bookings.info_start",
                customer_email=customer_email,
            )
            logger.debug(
                f"list_customer_bookings called with email={customer_email}, include_cancelled={include_cancelled}"
            )

            # Call business logic
            result = booking_tool.list_customer_bookings(
                customer_email=customer_email,
                include_cancelled=include_cancelled,
            )

            booking_count = result.get("count", 0)
            active_count = result.get("active_count", 0)

            await mcp_info(
                ctx,
                "booking.list_bookings.info_found",
                booking_count=booking_count,
                active_count=active_count,
                customer_email=customer_email,
            )
            logger.info(
                f"Bookings listed: {booking_count} total, {active_count} active for {customer_email}"
            )

            return result

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.list_bookings.error_general",
                customer_email=customer_email,
                error=str(e),
            )
            logger.exception(f"Error in list_customer_bookings: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def get_services(
        ctx: Context,
        active_only: bool = True,
    ) -> dict[str, Any]:
        """Get available booking services from database.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer asks about available services or appointments types
        ✅ Need to display service options to customer
        ✅ Before creating a booking to show service choices
        ✅ Customer says "qué servicios tienen", "qué tipos de citas hay", "qué puedo reservar"

        ** EXAMPLES OF VALID USE **:
        - "Qué servicios ofrecen?"
        - "Qué tipos de consultas tienen?"
        - "Cuáles son las opciones de citas?"
        - "Qué puedo agendar?"

        ** DON'T USE WHEN **:
        ❌ Customer already knows which service they want (use create_booking)
        ❌ Customer is asking about pricing (services include price info)

        ** WHAT IT DOES **:
        1. Queries test.service_types table in database
        2. Returns list of all available services with:
           - Service name and display name
           - Description
           - Duration and price
           - Visual styling (color, icon)
        3. Optionally filters to only active services

        ** PERFORMANCE **: ~20-30ms (simple database query)

        Args:
            ctx: MCP context for logging and progress reporting.
            active_only: Whether to return only active services (default: True).
                        Set to False to include inactive services.

        Returns:
            Services dict with:
            {
                "services": [
                    {
                        "name": str (identifier),
                        "display_name": str (user-friendly name),
                        "description": str,
                        "duration_minutes": int,
                        "price": float,
                        "color": str (hex color),
                        "icon": str (icon name)
                    },
                    ...
                ],
                "total": int (count of services)
            }

        Example:
            >>> result = await get_services(ctx=ctx, active_only=True)
            >>> print(f"Found {result['total']} services")
            >>> for service in result["services"]:
            ...     print(f"{service['display_name']}: {service['duration_minutes']}min - ${service['price']}")
            # Found 6 services
            # Consulta General: 30min - $50.00
            # Soporte Técnico: 60min - $80.00
            # Demo de Producto: 45min - $0.00
        """
        try:
            await mcp_info(ctx, "booking.get_services.info_start")
            logger.info(f"get_services called with active_only={active_only}")

            # Call business logic
            result = booking_tool.get_services(active_only=active_only)

            service_count = result.get("total", 0)
            await mcp_info(
                ctx,
                "booking.get_services.info_success",
                service_count=service_count,
            )
            logger.info(f"Services loaded: {service_count} services")

            return result

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.get_services.error_general",
                error=str(e),
            )
            logger.exception(f"Error in get_services: {str(e)}")
            raise

    @mcp.tool()  # type: ignore[union-attr]
    async def get_business_hours(
        ctx: Context,
    ) -> dict[str, Any]:
        """Get business operating hours from database.

        ** WHEN TO USE THIS TOOL **:
        ✅ Customer asks about business hours or operating schedule
        ✅ Customer wants to know when business is open
        ✅ Before suggesting booking times to show availability window
        ✅ Customer says "cuál es su horario", "a qué hora abren", "están abiertos"

        ** EXAMPLES OF VALID USE **:
        - "Cuál es su horario de atención?"
        - "A qué hora abren?"
        - "Están abiertos los sábados?"
        - "Qué días atienden?"

        ** DON'T USE WHEN **:
        ❌ Customer is checking specific date availability (use get_available_slots)
        ❌ Customer wants general company info (handled by GeneralAgent)

        ** WHAT IT DOES **:
        1. Queries test.business_hours table in database
        2. Returns operating hours for each day of the week
        3. Includes timezone information
        4. Only returns active business hours

        ** PERFORMANCE **: ~20-30ms (simple database query)

        Args:
            ctx: MCP context for logging and progress reporting.

        Returns:
            Business hours dict with:
            {
                "hours": {
                    "Monday": {"open": "09:00", "close": "18:00"},
                    "Tuesday": {"open": "09:00", "close": "18:00"},
                    ...
                },
                "timezone": str (e.g., "America/New_York"),
                "days_count": int (number of days with hours)
            }

        Example:
            >>> result = await get_business_hours(ctx=ctx)
            >>> print(f"Operating {result['days_count']} days per week")
            >>> for day, hours in result["hours"].items():
            ...     print(f"{day}: {hours['open']} - {hours['close']}")
            # Operating 6 days per week
            # Monday: 09:00 - 18:00
            # Tuesday: 09:00 - 18:00
            # ...
        """
        try:
            await mcp_info(ctx, "booking.get_hours.info_start")
            logger.info("get_business_hours called")

            # Call business logic
            result = booking_tool.get_business_hours()

            days_count = result.get("days_count", 0)
            await mcp_info(
                ctx,
                "booking.get_hours.info_success",
                days_count=days_count,
            )
            logger.info(f"Business hours loaded: {days_count} days")

            return result

        except Exception as e:
            await mcp_debug(
                ctx,
                "booking.get_hours.error_general",
                error=str(e),
            )
            logger.exception(f"Error in get_business_hours: {str(e)}")
            raise
