#!/usr/bin/env python3
"""Initialize bookings schema and tables in PostgreSQL.

Creates tables for booking/reservation management system:
- appointments: Main booking records with Google Calendar integration
- service_types: Catalog of available services
- business_hours: Operating hours configuration
- blocked_times: Holidays and unavailable slots

Prerequisites:
    - PostgreSQL 14+ running
    - Existing schema created by init-db.py
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/init_bookings.py

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.0.0
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import NoReturn

import psycopg2
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("init_bookings")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


def validate_environment() -> None:
    """Validate required environment variables are set.

    Raises:
        SystemExit: If DATABASE_URL is not set.
    """
    if not DATABASE_URL:
        logger.error(
            "Missing DATABASE_URL environment variable. "
            "Example: postgresql://user:pass@localhost:5432/db"
        )
        raise SystemExit(1)

    logger.info(f"Using schema: {SCHEMA_NAME}")
    logger.info(f"Database URL configured (host: {DATABASE_URL.split('@')[1].split('/')[0]})")


def load_sql_template() -> str:
    """Load SQL template from file.

    Returns:
        SQL template string with {SCHEMA_NAME} placeholders.

    Raises:
        FileNotFoundError: If SQL template file not found.
    """
    script_path = Path(__file__).parent.parent / "scripts" / "create_bookings_schema.sql"

    if not script_path.exists():
        logger.error(f"SQL template not found: {script_path}")
        raise FileNotFoundError(f"Missing SQL template: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        return f.read()


def run_sql(sql: str) -> None:
    """Execute SQL statement with proper connection handling.

    Args:
        sql: SQL statement to execute.

    Raises:
        Exception: If SQL execution fails.
    """
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True

        with conn.cursor() as cur:
            logger.info("Executing bookings schema creation...")
            cur.execute(sql)
            logger.info("SQL executed successfully")

    except psycopg2.Error as exc:
        logger.exception(f"PostgreSQL error: {exc}")
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error executing SQL: {exc}")
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


def verify_schema() -> None:
    """Verify that schema and tables were created successfully."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Check if schema exists
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
                (SCHEMA_NAME,),
            )
            schema_exists = cur.fetchone()[0]

            if not schema_exists:
                logger.error(f"Schema '{SCHEMA_NAME}' does not exist!")
                raise RuntimeError(f"Schema '{SCHEMA_NAME}' not found")

            # Check if booking tables exist
            tables = ["appointments", "service_types", "business_hours", "blocked_times"]
            for table in tables:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = %s AND table_name = %s)",
                    (SCHEMA_NAME, table),
                )
                exists = cur.fetchone()[0]
                if exists:
                    logger.info(f"✅ Table {SCHEMA_NAME}.{table} verified")
                else:
                    logger.warning(f"⚠️  Table {SCHEMA_NAME}.{table} not found")

    except Exception as exc:
        logger.exception(f"Error verifying schema: {exc}")
        raise
    finally:
        if conn:
            conn.close()


def main() -> None:
    """Main execution function."""
    logger.info("=" * 70)
    logger.info("BOOKINGS SCHEMA INITIALIZATION")
    logger.info("=" * 70)

    try:
        # Step 1: Validate environment
        logger.info("Step 1/4: Validating environment...")
        validate_environment()

        # Step 2: Load SQL template
        logger.info("Step 2/4: Loading SQL template...")
        sql_template = load_sql_template()

        # Step 3: Substitute schema name
        logger.info(f"Step 3/4: Substituting SCHEMA_NAME with '{SCHEMA_NAME}'...")
        sql = sql_template.replace("{SCHEMA_NAME}", SCHEMA_NAME)

        # Step 4: Execute SQL
        logger.info("Step 4/4: Executing SQL...")
        run_sql(sql)

        # Verification
        logger.info("Verifying schema creation...")
        verify_schema()

        logger.info("=" * 70)
        logger.info("✅ BOOKINGS SCHEMA INITIALIZATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Schema: {SCHEMA_NAME}")
        logger.info("Tables created:")
        logger.info("  - appointments (with Google Calendar integration)")
        logger.info("  - service_types (booking service catalog)")
        logger.info("  - business_hours (operating hours configuration)")
        logger.info("  - blocked_times (holidays and unavailable slots)")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Run seed data: python3 SQL/src/seed_booking_data.py")
        logger.info("  2. Test availability: python3 -c 'from mcp_server.tools import bookings'")
        logger.info("")

    except Exception as exc:
        logger.error("=" * 70)
        logger.error("❌ BOOKINGS SCHEMA INITIALIZATION FAILED")
        logger.error("=" * 70)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
