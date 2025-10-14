#!/usr/bin/env python3
"""Run Session Lifecycle Migration (005).

This script executes migration 005_add_session_lifecycle.sql which adds:
- archived column to conversation_sessions
- Session lifecycle functions (archive, cleanup, stats)
- Optimized indexes for performance

After running the migration, it performs an initial archive of old sessions
and generates a report.

USAGE:
    python3 SQL/src/run_session_lifecycle_migration.py

REQUIREMENTS:
    - PostgreSQL connection configured in .env
    - Migration 002 (conversation_sessions table) must be already applied

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 1.0.0
"""

import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "mcp_server"))

import psycopg2

from config.settings import settings
from utils.db import execute, fetchall, fetchone
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("migration_005")


def verify_prerequisites() -> bool:
    """Verify that required tables exist before running migration.

    Returns:
        bool: True if all prerequisites met
    """
    schema = settings.SCHEMA_NAME

    logger.info("Verifying prerequisites...")

    # Check conversation_sessions table exists
    query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = %s
        AND table_name = 'conversation_sessions'
    )
    """

    try:
        result = fetchone(query, (schema,))
        if not result or not result["exists"]:
            logger.error("❌ conversation_sessions table not found")
            logger.error("   Please run migration 002 first")
            return False

        logger.info("✅ Prerequisites met")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to verify prerequisites: {e}")
        return False


def run_migration() -> bool:
    """Execute migration 005 SQL file.

    Returns:
        bool: True if migration successful
    """
    schema = settings.SCHEMA_NAME
    migration_file = project_root / "mcp_server" / "migrations" / "005_add_session_lifecycle.sql"

    logger.info(f"Running migration from: {migration_file}")

    if not migration_file.exists():
        logger.error(f"❌ Migration file not found: {migration_file}")
        return False

    try:
        # Read migration SQL
        with open(migration_file, "r", encoding="utf-8") as f:
            migration_sql = f.read()

        # Substitute schema name
        migration_sql = migration_sql.replace("{SCHEMA_NAME}", schema)

        # Execute migration using psycopg2 directly (handles multiple statements)
        import psycopg2
        from psycopg2 import sql

        conn = psycopg2.connect(settings.DATABASE_URL)
        conn.autocommit = True

        try:
            with conn.cursor() as cur:
                cur.execute(migration_sql)
            logger.info("✅ Migration 005 executed successfully")
            return True
        finally:
            conn.close()

    except psycopg2.Error as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False


def verify_migration() -> bool:
    """Verify that migration was applied correctly.

    Returns:
        bool: True if verification passed
    """
    schema = settings.SCHEMA_NAME

    logger.info("Verifying migration...")

    try:
        # 1. Check archived column exists
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.columns
            WHERE table_schema = %s
            AND table_name = 'conversation_sessions'
            AND column_name = 'archived'
        )
        """
        result = fetchone(query, (schema,))
        if not result or not result["exists"]:
            logger.error("❌ Column 'archived' not found")
            return False

        logger.info("✅ Column 'archived' created")

        # 2. Check functions exist
        functions = [
            "archive_inactive_sessions",
            "cleanup_archived_sessions",
            "cleanup_anonymous_sessions",
            "get_session_retention_stats",
        ]

        for func_name in functions:
            query = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.routines
                WHERE routine_schema = %s
                AND routine_name = %s
                AND routine_type = 'FUNCTION'
            )
            """
            result = fetchone(query, (schema, func_name))
            if not result or not result["exists"]:
                logger.error(f"❌ Function '{func_name}' not found")
                return False

        logger.info(f"✅ All {len(functions)} functions created")

        # 3. Check indexes exist
        indexes = [
            "idx_sessions_archived",
            "idx_sessions_last_activity_archived",
            "idx_sessions_email_null",
        ]

        for index_name in indexes:
            query = f"""
            SELECT EXISTS (
                SELECT FROM pg_indexes
                WHERE schemaname = %s
                AND indexname = %s
            )
            """
            result = fetchone(query, (schema, index_name))
            if not result or not result["exists"]:
                logger.error(f"❌ Index '{index_name}' not found")
                return False

        logger.info(f"✅ All {len(indexes)} indexes created")

        logger.info("✅ Migration verification passed")
        return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def initial_archive() -> dict:
    """Run initial archive of old sessions.

    Returns:
        dict: Archive statistics
    """
    schema = settings.SCHEMA_NAME

    logger.info("Running initial archive of old sessions (90+ days)...")

    try:
        # Call archive function
        query = f"SELECT * FROM {schema}.archive_inactive_sessions(90)"
        results = fetchall(query)

        archived_sessions = [
            {
                "session_id": str(row["session_id"]),
                "customer_email": row["customer_email"],
                "days_inactive": row["days_inactive"],
            }
            for row in results
        ]

        archived_count = len(archived_sessions)

        if archived_count > 0:
            logger.info(f"✅ Archived {archived_count} inactive sessions")
        else:
            logger.info("✅ No sessions eligible for archiving")

        return {
            "archived_count": archived_count,
            "sessions": archived_sessions,
        }

    except Exception as e:
        logger.error(f"❌ Initial archive failed: {e}")
        return {"archived_count": 0, "sessions": []}


def generate_report() -> None:
    """Generate migration report with session statistics."""
    schema = settings.SCHEMA_NAME

    logger.info("")
    logger.info("=" * 70)
    logger.info("MIGRATION REPORT")
    logger.info("=" * 70)

    try:
        # Get session retention stats
        query = f"SELECT * FROM {schema}.get_session_retention_stats()"
        results = fetchall(query)

        stats = {}
        for row in results:
            metric_name = row["metric"]
            stats[metric_name] = {
                "count": int(row["count"]),
                "percentage": float(row["percentage"]),
            }

        logger.info("")
        logger.info("Session Statistics:")
        logger.info(f"  Active sessions: {stats.get('active_sessions', {}).get('count', 0)}")
        logger.info(f"  Archived sessions: {stats.get('archived_sessions', {}).get('count', 0)}")
        logger.info(f"  With email: {stats.get('with_email', {}).get('count', 0)}")
        logger.info(f"  Anonymous: {stats.get('anonymous', {}).get('count', 0)}")
        logger.info("")
        logger.info("Activity:")
        logger.info(f"  Active (7 days): {stats.get('active_7d', {}).get('count', 0)}")
        logger.info(f"  Active (30 days): {stats.get('active_30d', {}).get('count', 0)}")
        logger.info("")
        logger.info("Lifecycle Management:")
        logger.info(f"  Eligible for archive: {stats.get('eligible_archive', {}).get('count', 0)}")
        logger.info(f"  Eligible for delete: {stats.get('eligible_delete', {}).get('count', 0)}")
        logger.info("")
        logger.info("Configuration:")
        logger.info(f"  Archive after: {settings.SESSION_SOFT_ARCHIVE_DAYS} days")
        logger.info(f"  Delete after: {settings.SESSION_HARD_DELETE_DAYS} days")
        logger.info(f"  Anonymous delete after: {settings.SESSION_ANONYMOUS_DELETE_DAYS} days")
        logger.info("")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"❌ Failed to generate report: {e}")


def main() -> int:
    """Main migration execution.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 70)
    logger.info("SESSION LIFECYCLE MIGRATION (005)")
    logger.info("=" * 70)
    logger.info("")

    try:
        # Step 1: Verify prerequisites
        if not verify_prerequisites():
            logger.error("❌ Prerequisites not met")
            return 1

        logger.info("")

        # Step 2: Run migration
        if not run_migration():
            logger.error("❌ Migration failed")
            return 1

        logger.info("")

        # Step 3: Verify migration
        if not verify_migration():
            logger.error("❌ Verification failed")
            return 1

        logger.info("")

        # Step 4: Initial archive
        archive_stats = initial_archive()
        if archive_stats["archived_count"] > 0:
            logger.info(f"   Archived {archive_stats['archived_count']} old sessions")

        logger.info("")

        # Step 5: Generate report
        generate_report()

        logger.info("")
        logger.info("✅ Migration 005 completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update cron job: scripts/cleanup_expired_memories.py")
        logger.info("  2. Review SESSION_LIFECYCLE_POLICY.md")
        logger.info("  3. Test with: python3 scripts/cleanup_expired_memories.py --dry-run")
        logger.info("")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"\n❌ Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
