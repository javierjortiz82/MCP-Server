#!/usr/bin/env python3
"""Seed service-specific hours for hybrid scheduling system.

OPTIONAL: Populates service_hours table with service-specific operating hours.

This is completely optional. If you don't configure service_hours, the system
will automatically fall back to general business_hours for all services.

Example use cases:
- Installation service needs extended hours (8am-7pm) for long installations
- Training sessions only offered in mornings (9am-12pm)
- Premium support available 24/7
- Express consultations only during specific hours

Prerequisites:
    - service_hours table created by init_service_hours.py
    - service_types already populated with at least one active service
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/seed_service_hours.py

Author: Lab01-MCP Team
Created: 2025-10-17
Version: 1.0.0
"""

from __future__ import annotations

import logging
import os
from datetime import time
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
logger = logging.getLogger("seed_service_hours")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


# ============================================================================
# SERVICE HOURS SEED DATA (OPTIONAL)
# ============================================================================
#
# This is completely optional. Modify or extend as needed for your business.
#
# Format: (service_name, day_of_week, open_time, close_time, priority)
# - service_name: Must match a name in service_types table
# - day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
# - open_time, close_time: datetime.time objects
# - priority: 0=highest (default), 1=medium, etc. Allows multiple ranges/day

SERVICE_HOURS_DATA: list[tuple[str, int, time, time, int]] = [
    # Example 1: Extended hours for installation service
    # Installation requires more time, so offer extended hours
    ("installation", 0, time(8, 0), time(19, 0), 0),    # Monday 8am-7pm
    ("installation", 1, time(8, 0), time(19, 0), 0),    # Tuesday 8am-7pm
    ("installation", 2, time(8, 0), time(19, 0), 0),    # Wednesday 8am-7pm
    ("installation", 3, time(8, 0), time(19, 0), 0),    # Thursday 8am-7pm
    ("installation", 4, time(8, 0), time(19, 0), 0),    # Friday 8am-7pm

    # Example 2: Morning-only hours for training sessions
    # Training sessions are intensive, only offered in mornings
    ("training_session", 0, time(9, 0), time(12, 0), 0),  # Monday 9am-12pm
    ("training_session", 1, time(9, 0), time(12, 0), 0),  # Tuesday 9am-12pm
    ("training_session", 2, time(9, 0), time(12, 0), 0),  # Wednesday 9am-12pm
    ("training_session", 3, time(9, 0), time(12, 0), 0),  # Thursday 9am-12pm
    ("training_session", 4, time(9, 0), time(12, 0), 0),  # Friday 9am-12pm

    # Example 3: Afternoon slots for product demo
    # Demos preferred in afternoon hours for better audience availability
    ("product_demo", 0, time(14, 0), time(17, 0), 0),     # Monday 2pm-5pm
    ("product_demo", 1, time(14, 0), time(17, 0), 0),     # Tuesday 2pm-5pm
    ("product_demo", 2, time(14, 0), time(17, 0), 0),     # Wednesday 2pm-5pm
    ("product_demo", 3, time(14, 0), time(17, 0), 0),     # Thursday 2pm-5pm
    ("product_demo", 4, time(14, 0), time(17, 0), 0),     # Friday 2pm-5pm

    # NOTE: Services NOT listed here (e.g., "consultation", "technical_support")
    # will automatically use the general business_hours when scheduled.
]


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


def seed_service_hours(conn: psycopg2.extensions.connection) -> int:
    """Seed service_hours table with optional service-specific hours.

    Args:
        conn: Database connection.

    Returns:
        Number of records inserted.
    """
    with conn.cursor() as cur:
        inserted = 0
        for service_name, day, open_t, close_t, priority in SERVICE_HOURS_DATA:
            try:
                # Get service ID from service_types table
                cur.execute(
                    f"""
                    SELECT id FROM {SCHEMA_NAME}.service_types
                    WHERE name = %s AND active = true
                    """,
                    (service_name,),
                )
                result = cur.fetchone()

                if not result:
                    logger.warning(
                        f"⚠️  Service '{service_name}' not found or inactive - skipping"
                    )
                    continue

                service_type_id = result[0]

                # Insert service-specific hours
                cur.execute(
                    f"""
                    INSERT INTO {SCHEMA_NAME}.service_hours
                    (service_type_id, day_of_week, open_time, close_time, priority, active)
                    VALUES (%s, %s, %s, %s, %s, true)
                    ON CONFLICT (service_type_id, day_of_week, priority)
                    DO UPDATE SET
                        open_time = EXCLUDED.open_time,
                        close_time = EXCLUDED.close_time,
                        active = true
                    """,
                    (service_type_id, day, open_t, close_t, priority),
                )
                inserted += 1

                day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                logger.debug(
                    f"✅ {service_name} - {day_names[day]}: {open_t.strftime('%H:%M')}-{close_t.strftime('%H:%M')}"
                )

            except Exception as exc:
                logger.error(f"❌ Failed to insert hours for {service_name}: {exc}")

        conn.commit()
        return inserted


def verify_data(conn: psycopg2.extensions.connection) -> dict[str, Any]:
    """Verify seeded data.

    Args:
        conn: Database connection.

    Returns:
        Dictionary with verification stats.
    """
    stats = {}
    with conn.cursor() as cur:
        # Count total service hours
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.service_hours")
        stats["total_rows"] = cur.fetchone()[0]

        # Count services with custom hours
        cur.execute(
            f"""
            SELECT COUNT(DISTINCT service_type_id)
            FROM {SCHEMA_NAME}.service_hours
            """
        )
        stats["services_with_custom_hours"] = cur.fetchone()[0]

        # Get service names
        cur.execute(
            f"""
            SELECT DISTINCT st.display_name, COUNT(*) as hour_count
            FROM {SCHEMA_NAME}.service_hours sh
            JOIN {SCHEMA_NAME}.service_types st ON sh.service_type_id = st.id
            GROUP BY st.id, st.display_name
            ORDER BY st.display_name
            """
        )
        stats["services"] = cur.fetchall()

    return stats


def main() -> None:
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("SERVICE-SPECIFIC HOURS SEEDING (OPTIONAL)")
    logger.info("=" * 70)

    try:
        # Validate environment
        validate_environment()

        # Connect to database
        logger.info("Connecting to database...")
        conn = get_connection()

        try:
            # Seed service hours
            logger.info("Seeding service-specific hours...")
            inserted = seed_service_hours(conn)
            logger.info(f"✅ Inserted {inserted} service-specific hour entries")

            # Verify
            logger.info("Verifying data...")
            stats = verify_data(conn)

            logger.info("=" * 70)
            logger.info("✅ SERVICE HOURS SEEDING COMPLETE")
            logger.info("=" * 70)
            logger.info(f"Total service hour entries: {stats['total_rows']}")
            logger.info(f"Services with custom hours: {stats['services_with_custom_hours']}")
            logger.info("")
            logger.info("Custom hours configured for:")
            for service_name, count in stats["services"]:
                logger.info(f"  ✅ {service_name} ({count} day entries)")
            logger.info("")
            logger.info("💡 Services NOT listed above will use general business_hours")
            logger.info("")
            logger.info("🚀 Hybrid scheduling system ready!")

        finally:
            conn.close()
            logger.debug("Database connection closed")

    except Exception as exc:
        logger.error("=" * 70)
        logger.error("❌ SERVICE HOURS SEEDING FAILED")
        logger.error("=" * 70)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
