"""Booking System Constants and Enumerations.

This module consolidates all booking-related constants, enums, and status
values that were previously hardcoded in various modules. Centralizing these
improves maintainability and allows for configuration-driven customization.

References:
    - SQL/scripts/create_bookings_schema.sql (database schema)
    - mcp_server/tools/bookings.py (business logic)
    - mcp_server/mcp_handlers/booking_handlers.py (MCP handlers)

Author: Lab01-MCP Team
Created: 2025-10-16
Version: 1.0.0
"""

from enum import Enum


class BookingStatus(str, Enum):
    """Booking status enumeration.

    Represents the lifecycle states of a booking/appointment.
    Maps to database `status` column in appointments table.
    """

    CONFIRMED = "confirmed"
    """Booking is confirmed and active."""

    CANCELLED = "cancelled"
    """Booking has been cancelled by customer or system."""

    RESCHEDULED = "rescheduled"
    """Booking has been rescheduled to a different date/time."""

    COMPLETED = "completed"
    """Booking has been completed (appointment occurred)."""

    NO_SHOW = "no_show"
    """Customer did not show up for booking."""

    @classmethod
    def active_statuses(cls) -> set["BookingStatus"]:
        """Get all active booking statuses (not cancelled/completed)."""
        return {cls.CONFIRMED, cls.RESCHEDULED}

    @classmethod
    def non_reschedulable(cls) -> set["BookingStatus"]:
        """Get statuses that cannot be rescheduled."""
        return {cls.CANCELLED, cls.COMPLETED}


class EmailNotificationType(str, Enum):
    """Email notification types for booking events.

    Maps to email queue system notification types.
    """

    BOOKING_CREATED = "booking_created"
    """Notification for new booking creation."""

    BOOKING_CANCELLED = "booking_cancelled"
    """Notification for booking cancellation."""

    BOOKING_RESCHEDULED = "booking_rescheduled"
    """Notification for booking reschedule."""


class ServiceType(str, Enum):
    """Available booking service types.

    Maps to test.service_types table in database.
    Keep in sync with database schema.
    """

    CONSULTATION = "consultation"
    """General consultation service."""

    TECHNICAL_SUPPORT = "technical_support"
    """Technical support/troubleshooting service."""

    PRODUCT_DEMO = "product_demo"
    """Product demonstration service."""

    TRAINING_SESSION = "training_session"
    """Training or educational session."""

    INSTALLATION = "installation"
    """Product installation service."""

    CUSTOM = "custom"
    """Custom/other service type."""


class MemoryContextHeader(str, Enum):
    """Memory context section headers for agent prompts.

    These strings appear in the system prompt to delineate memory sections.
    Extracted to allow for localization and theme customization.
    """

    SESSION = "[MEMORIA DE LA SESIÓN ACTUAL]:"
    """Current session memory header."""

    USER_HISTORY = "[MEMORIA HISTÓRICA DEL USUARIO]:"
    """User historical memory header."""

    LAST_INTENT = "[CONTEXTO] Intención previa:"
    """Last intent context header."""

    LAST_MESSAGE = "[CONTEXTO] Última respuesta del bot:"
    """Last bot message context header."""


# Intent classification keywords
# Maps intent types to keyword triggers
INTENT_KEYWORDS = {
    "sales": ["sales", "venta", "producto", "compra"],
    "booking": ["booking", "reserva", "cita", "agendar", "horario"],
    "general": ["general", "faq", "ayuda", "información", "info"],
}


# Booking choice options for reschedule/cancel decisions
# Used in booking input parser for user intent detection
BOOKING_CHOICE_OPTIONS = {
    # Option A: Reschedule
    "option_a": ["a", "1", "opcion a", "opcion 1", "opción a", "opción 1"],
    # Option B: Cancel
    "option_b": ["b", "2", "opcion b", "opcion b", "opción b", "opción b"],
}


# Timezone mappings (simplified - production should use pytz/zoneinfo)
TIMEZONE_OFFSETS = {
    # North America
    "America/New_York": "-05:00",       # EST (UTC-5 winter, UTC-4 summer)
    "America/Chicago": "-06:00",        # CST (UTC-6 winter, UTC-5 summer)
    "America/Denver": "-07:00",         # MST (UTC-7 winter, UTC-6 summer)
    "America/Los_Angeles": "-08:00",    # PST (UTC-8 winter, UTC-7 summer)

    # Central America (no DST - always UTC-6)
    "America/Costa_Rica": "-06:00",     # CST (UTC-6 year-round)
    "America/Guatemala": "-06:00",      # CST (UTC-6 year-round)
    "America/El_Salvador": "-06:00",    # CST (UTC-6 year-round)
    "America/Tegucigalpa": "-06:00",    # Honduras CST (UTC-6 year-round)
    "America/Managua": "-06:00",        # Nicaragua CST (UTC-6 year-round)
    "America/Panama": "-05:00",         # EST (UTC-5 year-round)

    # Europe
    "Europe/Madrid": "+01:00",          # CET (UTC+1 winter, UTC+2 summer)
    "Europe/London": "+00:00",          # GMT (UTC+0 winter, UTC+1 summer)

    # Other
    "UTC": "+00:00",
}


def get_timezone_offset(timezone: str) -> str:
    """Get timezone offset string for given timezone.

    Args:
        timezone: IANA timezone identifier (e.g., "America/New_York")

    Returns:
        Timezone offset string (e.g., "-05:00")

    Note:
        This is a simplified implementation. In production, use pytz/zoneinfo
        to properly handle daylight saving time transitions.
    """
    return TIMEZONE_OFFSETS.get(timezone, "-06:00")  # Default to Costa Rica


# Default values for booking system
BOOKING_DEFAULTS = {
    "default_status": BookingStatus.CONFIRMED,
    "default_duration_minutes": 60,
    "default_email_priority": 5,
    "email_queue_priority": 5,
}


# Status transition rules
VALID_STATUS_TRANSITIONS = {
    BookingStatus.CONFIRMED: {BookingStatus.RESCHEDULED, BookingStatus.CANCELLED, BookingStatus.COMPLETED},
    BookingStatus.RESCHEDULED: {BookingStatus.CANCELLED, BookingStatus.COMPLETED},
    BookingStatus.CANCELLED: set(),  # Terminal state
    BookingStatus.COMPLETED: set(),  # Terminal state
    BookingStatus.NO_SHOW: set(),  # Terminal state
}


__all__ = [
    # Enums
    "BookingStatus",
    "EmailNotificationType",
    "ServiceType",
    "MemoryContextHeader",

    # Keyword mappings
    "INTENT_KEYWORDS",
    "BOOKING_CHOICE_OPTIONS",
    "TIMEZONE_OFFSETS",

    # Functions
    "get_timezone_offset",

    # Constants
    "BOOKING_DEFAULTS",
    "VALID_STATUS_TRANSITIONS",
]
