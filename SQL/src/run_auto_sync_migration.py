#!/usr/bin/env python3
"""Run Auto-Sync Trigger migration (004).

Adds automatic synchronization of session memory to user-level memory.
Sessions are auto-synced when they resume after 30+ minutes of inactivity.

Prerequisites:
    - PostgreSQL 14+ running
    - Migration 003 applied (user memory tables)
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/run_auto_sync_migration.py

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 1.0.0 (Fase 6.1 - Auto-Sync Enhancement)
"""

import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables
project_root = Path(__file__).parent.parent.parent
mcp_server_env = project_root / "mcp_server" / ".env"
root_env = project_root / ".env"

if mcp_server_env.exists():
    load_dotenv(mcp_server_env)
elif root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_auto_sync_migration")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


def validate_environment():
    """Validate required environment variables are set."""
    if not DATABASE_URL:
        logger.error(
            "Missing DATABASE_URL environment variable. "
            "Example: postgresql://user:pass@localhost:5432/db"
        )
        raise SystemExit(1)

    logger.info(f"Using schema: {SCHEMA_NAME}")
    logger.info(f"Database URL configured (host: {DATABASE_URL.split('@')[1].split('/')[0]})")


def load_migration_template():
    """Load migration SQL template from file."""
    migration_path = project_root / "mcp_server" / "migrations" / "004_add_auto_sync_trigger.sql"

    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        raise FileNotFoundError(f"Missing migration: {migration_path}")

    logger.debug(f"Loading migration from: {migration_path}")
    with open(migration_path, "r", encoding="utf-8") as f:
        return f.read()


def run_migration(sql):
    """Execute migration SQL with proper connection handling."""
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True

        with conn.cursor() as cur:
            logger.info("Executing auto-sync trigger migration...")
            cur.execute(sql)
            logger.info("Migration executed successfully")

    except psycopg2.Error as exc:
        logger.exception(f"PostgreSQL error: {exc}")
        raise
    except Exception as exc:
        logger.exception(f"Unexpected error executing migration: {exc}")
        raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


def verify_migration():
    """Verify that migration was successful."""
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        with conn.cursor() as cur:
            # Check if new functions exist
            functions = [
                "auto_sync_inactive_sessions",
                "trigger_auto_sync_on_activity_update",
            ]

            logger.info("")
            logger.info("Verifying functions...")
            all_functions_exist = True
            for func in functions:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM pg_proc p "
                    "JOIN pg_namespace n ON p.pronamespace = n.oid "
                    "WHERE n.nspname = %s AND p.proname = %s)",
                    (SCHEMA_NAME, func),
                )
                exists = cur.fetchone()[0]
                if exists:
                    logger.info(f"✅ Function {SCHEMA_NAME}.{func}() verified")
                else:
                    logger.warning(f"⚠️  Function {SCHEMA_NAME}.{func}() not found")
                    all_functions_exist = False

            if not all_functions_exist:
                raise RuntimeError("Some functions were not created successfully")

            # Check if trigger exists
            logger.info("")
            logger.info("Verifying trigger...")
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_trigger t "
                "JOIN pg_class c ON t.tgrelid = c.oid "
                "JOIN pg_namespace n ON c.relnamespace = n.oid "
                "WHERE n.nspname = %s AND t.tgname = %s)",
                (SCHEMA_NAME, "trg_auto_sync_on_activity_resume"),
            )
            trigger_exists = cur.fetchone()[0]
            if trigger_exists:
                logger.info(f"✅ Trigger trg_auto_sync_on_activity_resume verified")
            else:
                logger.warning(f"⚠️  Trigger trg_auto_sync_on_activity_resume not found")

    except Exception as exc:
        logger.exception(f"Error verifying migration: {exc}")
        raise
    finally:
        if conn:
            conn.close()


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("AUTO-SYNC TRIGGER SYSTEM INITIALIZATION (Migration 004)")
    logger.info("=" * 80)

    try:
        # Step 1: Validate environment
        logger.info("Step 1/4: Validating environment...")
        validate_environment()

        # Step 2: Load migration template
        logger.info("Step 2/4: Loading migration template...")
        sql_template = load_migration_template()

        # Step 3: Substitute schema name
        logger.info(f"Step 3/4: Substituting SCHEMA_NAME with '{SCHEMA_NAME}'...")
        sql = sql_template.replace("{SCHEMA_NAME}", SCHEMA_NAME)

        # Step 4: Execute migration
        logger.info("Step 4/4: Executing migration...")
        run_migration(sql)

        # Verification
        logger.info("")
        logger.info("Verifying migration...")
        verify_migration()

        logger.info("")
        logger.info("=" * 80)
        logger.info("✅ AUTO-SYNC TRIGGER SYSTEM INITIALIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Schema: {SCHEMA_NAME}")
        logger.info("")
        logger.info("🔧 Functions created:")
        logger.info("  - auto_sync_inactive_sessions() - Batch sync inactive sessions")
        logger.info("  - trigger_auto_sync_on_activity_update() - Trigger on activity resume")
        logger.info("")
        logger.info("⚡ Trigger configured:")
        logger.info("  - trg_auto_sync_on_activity_resume - Auto-sync when session resumes")
        logger.info("")
        logger.info("📖 How it works:")
        logger.info("  1. User stops activity → session becomes inactive")
        logger.info("  2. After 30 minutes → eligible for auto-sync")
        logger.info("  3. User returns → trigger auto-syncs previous high-priority blocks")
        logger.info("  4. New activity continues → process repeats")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Set up cron job for batch sync: python3 scripts/auto_sync_cron.py")
        logger.info("  2. Monitor auto-sync operations in logs")
        logger.info("  3. Adjust inactivity threshold if needed (default: 30 minutes)")
        logger.info("")

    except Exception as exc:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ AUTO-SYNC TRIGGER SYSTEM INITIALIZATION FAILED")
        logger.error("=" * 80)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
