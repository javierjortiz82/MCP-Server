#!/usr/bin/env python3
"""Initialize agent memory system in PostgreSQL.

Creates tables for multi-agent persistent memory:
- conversation_sessions: User session tracking
- conversation_messages: Individual messages with metadata
- agent_memory_blocks: Semantic memory (Memory Blocks pattern)
- agent_context_transfers: Agent handoff tracking

Prerequisites:
    - PostgreSQL 14+ running with uuid-ossp extension
    - Existing schema created by init-db.py
    - Variables in .env: DATABASE_URL, SCHEMA_NAME

Usage:
    python3 SQL/src/init_memory_system.py

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0
"""

import logging
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Load environment variables from mcp_server/.env (consistent with other SQL scripts)
project_root = Path(__file__).parent.parent.parent
mcp_server_env = project_root / "mcp_server" / ".env"
root_env = project_root / ".env"

# Try mcp_server/.env first (has DATABASE_URL), then root .env
if mcp_server_env.exists():
    load_dotenv(mcp_server_env)
elif root_env.exists():
    load_dotenv(root_env)
else:
    # Last resort: load from current directory
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("init_memory_system")

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL")
SCHEMA_NAME = os.getenv("SCHEMA_NAME", "test")


def validate_environment():
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


def load_migration_template():
    """Load migration SQL template from file.

    Returns:
        str: SQL template string with {SCHEMA_NAME} placeholders.

    Raises:
        FileNotFoundError: If migration file not found.
    """
    # Calculate path correctly: SQL/src -> SQL -> Lab01-MCP -> mcp_server/migrations
    migration_path = project_root / "mcp_server" / "migrations" / "002_add_agent_memory.sql"

    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        raise FileNotFoundError(f"Missing migration: {migration_path}")

    logger.debug(f"Loading migration from: {migration_path}")
    with open(migration_path, "r", encoding="utf-8") as f:
        return f.read()


def run_migration(sql):
    """Execute migration SQL with proper connection handling.

    Args:
        sql (str): SQL migration to execute.

    Raises:
        Exception: If SQL execution fails.
    """
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True

        with conn.cursor() as cur:
            logger.info("Executing agent memory system migration...")
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

            # Check if memory tables exist
            tables = [
                "conversation_sessions",
                "conversation_messages",
                "agent_memory_blocks",
                "agent_context_transfers",
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

            # Verify utility functions
            functions = [
                "get_recent_messages",
                "get_active_memory_blocks",
                "cleanup_expired_memory_blocks",
                "get_session_statistics",
                "update_memory_timestamp",
                "calculate_memory_expiration",
                "update_session_activity",
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
    logger.info("AGENT MEMORY SYSTEM INITIALIZATION")
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
        logger.info("✅ AGENT MEMORY SYSTEM INITIALIZATION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Schema: {SCHEMA_NAME}")
        logger.info("")
        logger.info("📊 Tables created:")
        logger.info("  - conversation_sessions (user session tracking)")
        logger.info("  - conversation_messages (individual messages with metadata)")
        logger.info("  - agent_memory_blocks (semantic memory - Memory Blocks pattern)")
        logger.info("  - agent_context_transfers (agent handoff tracking)")
        logger.info("")
        logger.info("🔧 Utility functions available:")
        logger.info("  - get_recent_messages() for history retrieval")
        logger.info("  - get_active_memory_blocks() for semantic memory")
        logger.info("  - cleanup_expired_memory_blocks() for TTL maintenance")
        logger.info("  - get_session_statistics() for analytics")
        logger.info("")
        logger.info("📖 Best Practices Implemented:")
        logger.info("  ✅ Memory Blocks Pattern (Letta)")
        logger.info("  ✅ Hybrid Memory (Short-term + Long-term)")
        logger.info("  ✅ Context Transfer Tracking")
        logger.info("  ✅ Priority Scoring")
        logger.info("  ✅ TTL Management")
        logger.info("  ✅ Multi-Agent Scope Support")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update mcp_server/config/settings.py with memory config")
        logger.info("  2. Implement agent/src/multi_agent/memory_manager.py")
        logger.info("  3. Integrate MemoryManager with BaseAgent")
        logger.info("  4. Test with: python3 -m pytest test/unit/test_memory_manager.py")
        logger.info("")

    except Exception as exc:
        logger.error("")
        logger.error("=" * 80)
        logger.error("❌ AGENT MEMORY SYSTEM INITIALIZATION FAILED")
        logger.error("=" * 80)
        logger.exception(f"Error: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()