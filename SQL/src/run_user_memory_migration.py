#!/usr/bin/env python3
"""Run User Memory Profile migration (003).

Creates user-level memory tables for cross-session context management:
- user_memory_profiles: User metadata across sessions
- user_memory_blocks: Cross-session semantic memory

Prerequisites:
    - PostgreSQL 14+ running with uuid-ossp extension
    - Existing agent memory system (migration 002)
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/run_user_memory_migration.py

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0 (Fase 6 - Cross-Session Memory)
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
logger = logging.getLogger("run_user_memory_migration")

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
    migration_path = project_root / "mcp_server" / "migrations" / "003_add_user_memory_profile.sql"

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
            logger.info("Executing user memory profile migration...")
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
            # Check if schema exists
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = %s)",
                (SCHEMA_NAME,),
            )
            schema_exists = cur.fetchone()[0]

            if not schema_exists:
                logger.error(f"Schema '{SCHEMA_NAME}' does not exist!")
                raise RuntimeError(f"Schema '{SCHEMA_NAME}' not found")

            # Check if new tables exist
            tables = [
                "user_memory_profiles",
                "user_memory_blocks",
            ]

            all_tables_exist = True
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
                    all_tables_exist = False

            if not all_tables_exist:
                raise RuntimeError("Some tables were not created successfully")

            # Verify new utility functions
            functions = [
                "get_or_create_user_profile",
                "get_user_memory_blocks",
                "sync_session_to_user_memory",
                "cleanup_expired_user_memory_blocks",
            ]

            logger.info("")
            logger.info("Verifying utility functions...")
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

    except Exception as exc:
        logger.exception(f"Error verifying migration: {exc}")
        raise
    finally:
        if conn:
            conn.close()


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("USER MEMORY PROFILE SYSTEM INITIALIZATION (Migration 003)")
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
        logger.info("✅ USER MEMORY PROFILE SYSTEM INITIALIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Schema: {SCHEMA_NAME}")
        logger.info("")
        logger.info("📊 Tables created:")
        logger.info("  - user_memory_profiles (user metadata across sessions)")
        logger.info("  - user_memory_blocks (cross-session semantic memory)")
        logger.info("")
        logger.info("🔧 Utility functions available:")
        logger.info("  - get_or_create_user_profile() for user profile management")
        logger.info("  - get_user_memory_blocks() for cross-session memory retrieval")
        logger.info("  - sync_session_to_user_memory() for automatic promotion")
        logger.info("  - cleanup_expired_user_memory_blocks() for TTL maintenance")
        logger.info("")
        logger.info("📖 Features:")
        logger.info("  ✅ User-level memory aggregation")
        logger.info("  ✅ Automatic session-to-user sync (priority >= 7)")
        logger.info("  ✅ Memory deduplication (merge similar blocks)")
        logger.info("  ✅ Extended TTL (180 days user-level vs 90 session-level)")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update MemoryManager with user memory methods")
        logger.info("  2. Integrate with BaseAgent.resume_session()")
        logger.info("  3. Test with: python3 test_cross_session_memory.py")
        logger.info("")

    except Exception as exc:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ USER MEMORY PROFILE SYSTEM INITIALIZATION FAILED")
        logger.error("=" * 80)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
