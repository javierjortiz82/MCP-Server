#!/usr/bin/env python3
"""Seed initial data for bookings system.

Populates:
- service_types: Available services for booking
- business_hours: Default operating hours (Mon-Fri 9am-6pm, Sat 10am-2pm)
- blocked_times: Sample holiday/break entries

Prerequisites:
    - Bookings schema created by init_bookings.py
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/seed_booking_data.py

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.0.0
"""

from __future__ import annotations

import logging
import os
from datetime import date, time
from typing import Any

import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("seed_bookings")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


# ============================================================================
# SEED DATA DEFINITIONS
# ============================================================================

SERVICE_TYPES: list[dict[str, Any]] = [
    {
        "name": "consultation",
        "display_name": "Consulta General",
        "description": "Consulta general de servicios disponibles",
        "duration_minutes": 30,
        "price": 50.00,
        "active": True,
        "color": "#4A90E2",  # Blue
        "icon": "chat",
    },
    {
        "name": "technical_support",
        "display_name": "Soporte Técnico",
        "description": "Soporte técnico especializado para productos",
        "duration_minutes": 60,
        "price": 80.00,
        "active": True,
        "color": "#E67E22",  # Orange
        "icon": "wrench",
    },
    {
        "name": "product_demo",
        "display_name": "Demostración de Producto",
        "description": "Demostración personalizada de productos seleccionados",
        "duration_minutes": 45,
        "price": 0.00,  # Free demo
        "active": True,
        "color": "#50C878",  # Green
        "icon": "presentation",
    },
    {
        "name": "training_session",
        "display_name": "Sesión de Capacitación",
        "description": "Capacitación en uso de productos y sistemas",
        "duration_minutes": 90,
        "price": 120.00,
        "active": True,
        "color": "#9B59B6",  # Purple
        "icon": "graduation-cap",
    },
    {
        "name": "installation",
        "display_name": "Instalación de Producto",
        "description": "Instalación y configuración de productos",
        "duration_minutes": 120,
        "price": 150.00,
        "active": True,
        "color": "#E74C3C",  # Red
        "icon": "tools",
    },
]

# Business hours: Monday (0) to Saturday (5)
# Sunday (6) is not included - business is closed
# Format: (day_of_week, open_time, close_time, active)
BUSINESS_HOURS: list[tuple[int, time, time, bool]] = [
    (0, time(9, 0), time(18, 0), True),  # Monday
    (1, time(9, 0), time(18, 0), True),  # Tuesday
    (2, time(9, 0), time(18, 0), True),  # Wednesday
    (3, time(9, 0), time(18, 0), True),  # Thursday
    (4, time(9, 0), time(18, 0), True),  # Friday
    (5, time(10, 0), time(14, 0), True),  # Saturday (half day)
    # Note: Sunday (6) is omitted - no business hours (closed)
]

# Sample blocked times (holidays, breaks)
# Format: (block_date, start_time, end_time, reason, is_full_day)
BLOCKED_TIMES: list[tuple[date, time | None, time | None, str, bool]] = [
    # Full day blocks (holidays)
    (date(2025, 12, 25), None, None, "Christmas Day", True),
    (date(2026, 1, 1), None, None, "New Year's Day", True),
    (date(2026, 7, 4), None, None, "Independence Day", True),

    # Partial day blocks (lunch breaks, maintenance)
    (date(2026, 1, 15), time(12, 0), time(13, 0), "System Maintenance", False),
    (date(2026, 2, 14), time(14, 0), time(15, 30), "Team Meeting", False),
]


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def validate_environment() -> None:
    """Validate required environment variables.

    Raises:
        SystemExit: If DATABASE_URL is not set.
    """
    if not DATABASE_URL:
        logger.error("Missing DATABASE_URL environment variable")
        raise SystemExit(1)

    logger.info(f"Using schema: {SCHEMA_NAME}")


def get_connection() -> psycopg2.extensions.connection:
    """Get database connection.

    Returns:
        PostgreSQL connection object.

    Raises:
        psycopg2.Error: If connection fails.
    """
    return psycopg2.connect(DATABASE_URL)


def seed_service_types(conn: psycopg2.extensions.connection) -> int:
    """Seed service_types table.

    Args:
        conn: Database connection.

    Returns:
        Number of records inserted.
    """
    with conn.cursor() as cur:
        inserted = 0
        for service in SERVICE_TYPES:
            try:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA_NAME}.service_types
                    (name, display_name, description, duration_minutes, price, active, color, icon)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        description = EXCLUDED.description,
                        duration_minutes = EXCLUDED.duration_minutes,
                        price = EXCLUDED.price,
                        active = EXCLUDED.active,
                        color = EXCLUDED.color,
                        icon = EXCLUDED.icon
                    """,
                    (
                        service["name"],
                        service["display_name"],
                        service["description"],
                        service["duration_minutes"],
                        service["price"],
                        service["active"],
                        service["color"],
                        service["icon"],
                    ),
                )
                inserted += 1
                logger.debug(f"Inserted service: {service['name']}")
            except Exception as exc:
                logger.warning(f"Failed to insert service {service['name']}: {exc}")

        conn.commit()
        return inserted


def seed_business_hours(conn: psycopg2.extensions.connection) -> int:
    """Seed business_hours table.

    Args:
        conn: Database connection.

    Returns:
        Number of records inserted.
    """
    with conn.cursor() as cur:
        inserted = 0
        for day, open_time, close_time, active in BUSINESS_HOURS:
            try:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA_NAME}.business_hours
                    (day_of_week, open_time, close_time, active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (day_of_week) DO UPDATE SET
                        open_time = EXCLUDED.open_time,
                        close_time = EXCLUDED.close_time,
                        active = EXCLUDED.active
                    """,
                    (day, open_time, close_time, active),
                )
                inserted += 1
                day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day]
                logger.debug(f"Inserted business hours for {day_name}")
            except Exception as exc:
                logger.warning(f"Failed to insert business hours for day {day}: {exc}")

        conn.commit()
        return inserted


def seed_blocked_times(conn: psycopg2.extensions.connection) -> int:
    """Seed blocked_times table.

    Args:
        conn: Database connection.

    Returns:
        Number of records inserted.
    """
    with conn.cursor() as cur:
        inserted = 0
        for block_date, start_time, end_time, reason, is_full_day in BLOCKED_TIMES:
            try:
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA_NAME}.blocked_times
                    (block_date, start_time, end_time, reason, is_full_day)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (block_date, start_time, end_time, reason, is_full_day),
                )
                inserted += 1
                logger.debug(f"Inserted blocked time: {block_date} - {reason}")
            except Exception as exc:
                logger.warning(f"Failed to insert blocked time {block_date}: {exc}")

        conn.commit()
        return inserted


def verify_data(conn: psycopg2.extensions.connection) -> dict[str, int]:
    """Verify seeded data counts.

    Args:
        conn: Database connection.

    Returns:
        Dictionary with table names and record counts.
    """
    counts = {}
    with conn.cursor() as cur:
        # Count service types
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.service_types")
        counts["service_types"] = cur.fetchone()[0]

        # Count business hours
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.business_hours")
        counts["business_hours"] = cur.fetchone()[0]

        # Count blocked times
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.blocked_times")
        counts["blocked_times"] = cur.fetchone()[0]

    return counts


def main() -> None:
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("BOOKINGS DATA SEEDING")
    logger.info("=" * 70)

    try:
        # Validate environment
        validate_environment()

        # Connect to database
        logger.info("Connecting to database...")
        conn = get_connection()

        try:
            # Seed service types
            logger.info("Seeding service types...")
            service_count = seed_service_types(conn)
            logger.info(f"✅ Inserted {service_count} service types")

            # Seed business hours
            logger.info("Seeding business hours...")
            hours_count = seed_business_hours(conn)
            logger.info(f"✅ Inserted {hours_count} business hours")

            # Seed blocked times
            logger.info("Seeding blocked times...")
            blocked_count = seed_blocked_times(conn)
            logger.info(f"✅ Inserted {blocked_count} blocked times")

            # Verify
            logger.info("Verifying data...")
            counts = verify_data(conn)

            logger.info("=" * 70)
            logger.info("✅ BOOKINGS DATA SEEDING COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Schema: {SCHEMA_NAME}")
            logger.info("Records created:")
            logger.info(f"  - service_types: {counts['service_types']}")
            logger.info(f"  - business_hours: {counts['business_hours']}")
            logger.info(f"  - blocked_times: {counts['blocked_times']}")
            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Test booking availability")
            logger.info("  2. Create test appointment")
            logger.info("  3. Configure Google Calendar integration")
            logger.info("")

        finally:
            conn.close()
            logger.debug("Database connection closed")

    except Exception as exc:
        logger.error("=" * 70)
        logger.error("❌ BOOKINGS DATA SEEDING FAILED")
        logger.error("=" * 70)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
