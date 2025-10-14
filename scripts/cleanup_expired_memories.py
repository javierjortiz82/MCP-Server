#!/usr/bin/env python3
"""Scheduled Cleanup Job - Memory and Session Lifecycle Management.

This script should be run periodically (e.g., daily via cron) to maintain
database health and GDPR compliance.

Cleanup tasks performed:
1. Auto-sync inactive sessions (>30 min) to user memory
2. Cleanup expired session-level memory blocks (TTL: 90 days)
3. Cleanup expired user-level memory blocks (TTL: 180 days)
4. Archive inactive sessions (>90 days) - Soft delete
5. Delete archived sessions (>365 days) - Hard delete
6. Delete anonymous sessions (>30 days) - No email

USAGE:
    python3 scripts/cleanup_expired_memories.py [--dry-run]

CRON SETUP:
    # Run daily at 3:00 AM (recommended)
    0 3 * * * /usr/bin/python3 /path/to/scripts/cleanup_expired_memories.py

    # Run twice daily at 3 AM and 3 PM
    0 3,15 * * * /usr/bin/python3 /path/to/scripts/cleanup_expired_memories.py

MONITORING:
    - Logs are written to stdout (redirect to file in cron)
    - Exit code 0: Success
    - Exit code 1: Error

Example with logging:
    0 3 * * * /usr/bin/python3 /path/to/scripts/cleanup_expired_memories.py >> /var/log/memory_cleanup.log 2>&1

GDPR Compliance:
    This job ensures data retention policies are enforced:
    - Sessions archived after 90 days inactivity
    - Archived sessions deleted after 365 days
    - Anonymous sessions deleted after 30 days

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 2.0.0 (Fase 7 - Session Lifecycle Management)
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("cleanup_job")


def cleanup_session_memories(memory: MemoryManager, dry_run: bool = False) -> int:
    """Cleanup expired session-level memory blocks.

    Args:
        memory: MemoryManager instance
        dry_run: If True, only count without deleting

    Returns:
        Number of blocks that would be/were deleted
    """
    try:
        logger.info("Cleaning up expired session-level memory blocks...")

        if dry_run:
            # Count expired blocks
            from utils.db import fetchone

            query = f"""
            SELECT COUNT(*) as count
            FROM {memory.schema}.agent_memory_blocks
            WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """
            result = fetchone(query)
            count = result["count"] if result else 0

            logger.info(f"Would delete {count} expired session memory blocks (dry-run)")
            return count
        else:
            # Actually delete
            deleted_count = memory.cleanup_expired_memory_blocks()
            logger.info(f"✅ Deleted {deleted_count} expired session memory blocks")
            return deleted_count

    except Exception as e:
        logger.exception(f"Failed to cleanup session memories: {e}")
        raise


def cleanup_user_memories(memory: MemoryManager, dry_run: bool = False) -> int:
    """Cleanup expired user-level memory blocks.

    Args:
        memory: MemoryManager instance
        dry_run: If True, only count without deleting

    Returns:
        Number of blocks that would be/were deleted
    """
    try:
        logger.info("Cleaning up expired user-level memory blocks...")

        if dry_run:
            # Count expired blocks
            from utils.db import fetchone

            query = f"""
            SELECT COUNT(*) as count
            FROM {memory.schema}.user_memory_blocks
            WHERE expires_at IS NOT NULL AND expires_at < NOW()
            """
            result = fetchone(query)
            count = result["count"] if result else 0

            logger.info(f"Would delete {count} expired user memory blocks (dry-run)")
            return count
        else:
            # Actually delete
            deleted_count = memory.cleanup_expired_user_memory_blocks()
            logger.info(f"✅ Deleted {deleted_count} expired user memory blocks")
            return deleted_count

    except Exception as e:
        logger.exception(f"Failed to cleanup user memories: {e}")
        raise


def auto_sync_inactive_sessions(memory: MemoryManager, dry_run: bool = False) -> int:
    """Auto-sync inactive sessions to user-level memory.

    Args:
        memory: MemoryManager instance
        dry_run: If True, only report what would be synced

    Returns:
        Number of sessions synced
    """
    try:
        logger.info("Auto-syncing inactive sessions (>30 min)...")

        from utils.db import fetchall

        # Call PostgreSQL function
        query = f"SELECT * FROM {memory.schema}.auto_sync_inactive_sessions(30)"

        if dry_run:
            # Just count eligible sessions
            count_query = f"""
            SELECT COUNT(DISTINCT cs.id) as count
            FROM {memory.schema}.conversation_sessions cs
            WHERE cs.customer_email IS NOT NULL
              AND cs.last_activity_at < CURRENT_TIMESTAMP - INTERVAL '30 minutes'
              AND EXISTS (
                  SELECT 1
                  FROM {memory.schema}.agent_memory_blocks amb
                  WHERE amb.session_id = cs.id
                    AND amb.priority >= 7
                    AND amb.agent_scope = 'shared'
                    AND (amb.expires_at IS NULL OR amb.expires_at > CURRENT_TIMESTAMP)
              )
            """
            from utils.db import fetchone

            result = fetchone(count_query)
            count = result["count"] if result else 0

            logger.info(f"Would auto-sync {count} inactive sessions (dry-run)")
            return count
        else:
            results = fetchall(query)

            if results:
                logger.info(f"✅ Auto-synced {len(results)} inactive sessions:")
                for row in results:
                    session_id = row.get("session_id")
                    synced = row.get("synced_blocks", 0)
                    updated = row.get("updated_blocks", 0)
                    logger.info(
                        f"   - {session_id}: {synced} new, {updated} updated blocks"
                    )
            else:
                logger.info("No inactive sessions needed auto-sync")

            return len(results) if results else 0

    except Exception as e:
        logger.exception(f"Failed to auto-sync inactive sessions: {e}")
        raise


def get_memory_statistics(memory: MemoryManager) -> dict:
    """Get memory statistics for reporting.

    Args:
        memory: MemoryManager instance

    Returns:
        Dictionary with memory statistics
    """
    try:
        from utils.db import fetchone

        stats = {}

        # Session memory blocks
        query = f"""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE expires_at IS NULL OR expires_at > NOW()) as active,
            COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at < NOW()) as expired
        FROM {memory.schema}.agent_memory_blocks
        """
        result = fetchone(query)
        stats["session_blocks"] = (
            result if result else {"total": 0, "active": 0, "expired": 0}
        )

        # User memory blocks
        query = f"""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE expires_at IS NULL OR expires_at > NOW()) as active,
            COUNT(*) FILTER (WHERE expires_at IS NOT NULL AND expires_at < NOW()) as expired
        FROM {memory.schema}.user_memory_blocks
        """
        result = fetchone(query)
        stats["user_blocks"] = (
            result if result else {"total": 0, "active": 0, "expired": 0}
        )

        # User profiles
        query = f"SELECT COUNT(*) as count FROM {memory.schema}.user_memory_profiles"
        result = fetchone(query)
        stats["user_profiles"] = result["count"] if result else 0

        # Active sessions (last 24 hours)
        query = f"""
        SELECT COUNT(*) as count
        FROM {memory.schema}.conversation_sessions
        WHERE last_activity_at >= CURRENT_TIMESTAMP - INTERVAL '24 hours'
        """
        result = fetchone(query)
        stats["active_sessions_24h"] = result["count"] if result else 0

        return stats

    except Exception as e:
        logger.exception(f"Failed to get statistics: {e}")
        return {}


def main() -> int:
    """Main cleanup job execution.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Cleanup expired memory blocks and auto-sync inactive sessions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be cleaned without actually deleting",
    )

    args = parser.parse_args()

    # Start
    logger.info("=" * 70)
    logger.info("MEMORY CLEANUP JOB")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("")

    # Check prerequisites
    if not MEMORY_AVAILABLE:
        logger.error("❌ ERROR: MemoryManager not available")
        logger.error("   Please check your configuration and database connection")
        return 1

    try:
        # Initialize MemoryManager
        memory = MemoryManager()

        # Get initial statistics
        logger.info("Initial Statistics:")
        stats_before = get_memory_statistics(memory)
        logger.info(
            f"  Session Blocks: {stats_before.get('session_blocks', {}).get('active', 0)} active, "
            f"{stats_before.get('session_blocks', {}).get('expired', 0)} expired"
        )
        logger.info(
            f"  User Blocks: {stats_before.get('user_blocks', {}).get('active', 0)} active, "
            f"{stats_before.get('user_blocks', {}).get('expired', 0)} expired"
        )
        logger.info(f"  User Profiles: {stats_before.get('user_profiles', 0)}")
        logger.info(
            f"  Active Sessions (24h): {stats_before.get('active_sessions_24h', 0)}"
        )
        logger.info("")

        # Task 1: Auto-sync inactive sessions
        logger.info("Task 1/6: Auto-syncing inactive sessions...")
        synced_count = auto_sync_inactive_sessions(memory, dry_run=args.dry_run)

        # Task 2: Cleanup session-level memories
        logger.info("")
        logger.info("Task 2/6: Cleaning up session-level memories...")
        session_deleted = cleanup_session_memories(memory, dry_run=args.dry_run)

        # Task 3: Cleanup user-level memories
        logger.info("")
        logger.info("Task 3/6: Cleaning up user-level memories...")
        user_deleted = cleanup_user_memories(memory, dry_run=args.dry_run)

        # Task 4: Archive inactive sessions (90 days)
        logger.info("")
        logger.info("Task 4/6: Archiving inactive sessions (90+ days)...")
        if args.dry_run:
            # Count eligible sessions for archiving
            from utils.db import fetchone

            query = f"""
            SELECT COUNT(*) as count
            FROM {memory.schema}.conversation_sessions
            WHERE archived = FALSE
              AND last_activity_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
            """
            result = fetchone(query)
            sessions_archived = result["count"] if result else 0
            logger.info(
                f"Would archive {sessions_archived} inactive sessions (dry-run)"
            )
        else:
            archive_result = memory.archive_inactive_sessions()
            sessions_archived = archive_result["archived_count"]
            logger.info(f"✅ Archived {sessions_archived} inactive sessions")

        # Task 5: Delete archived sessions (365 days)
        logger.info("")
        logger.info("Task 5/6: Deleting old archived sessions (365+ days)...")
        if args.dry_run:
            # Count eligible sessions for deletion
            from utils.db import fetchone

            query = f"""
            SELECT COUNT(*) as count
            FROM {memory.schema}.conversation_sessions
            WHERE archived = TRUE
              AND updated_at < CURRENT_TIMESTAMP - INTERVAL '365 days'
            """
            result = fetchone(query)
            sessions_deleted = result["count"] if result else 0
            logger.info(f"Would delete {sessions_deleted} archived sessions (dry-run)")
        else:
            sessions_deleted = memory.cleanup_archived_sessions()
            logger.info(f"✅ Deleted {sessions_deleted} archived sessions")

        # Task 6: Delete anonymous sessions (30 days)
        logger.info("")
        logger.info("Task 6/6: Deleting anonymous sessions (30+ days)...")
        if args.dry_run:
            # Count eligible anonymous sessions
            from utils.db import fetchone

            query = f"""
            SELECT COUNT(*) as count
            FROM {memory.schema}.conversation_sessions
            WHERE customer_email IS NULL
              AND last_activity_at < CURRENT_TIMESTAMP - INTERVAL '30 days'
            """
            result = fetchone(query)
            anonymous_deleted = result["count"] if result else 0
            logger.info(
                f"Would delete {anonymous_deleted} anonymous sessions (dry-run)"
            )
        else:
            anonymous_deleted = memory.cleanup_anonymous_sessions()
            logger.info(f"✅ Deleted {anonymous_deleted} anonymous sessions")

        # Final statistics
        logger.info("")
        logger.info("Final Statistics:")
        stats_after = get_memory_statistics(memory)
        logger.info(
            f"  Session Blocks: {stats_after.get('session_blocks', {}).get('active', 0)} active, "
            f"{stats_after.get('session_blocks', {}).get('expired', 0)} expired"
        )
        logger.info(
            f"  User Blocks: {stats_after.get('user_blocks', {}).get('active', 0)} active, "
            f"{stats_after.get('user_blocks', {}).get('expired', 0)} expired"
        )

        # Get session retention stats
        logger.info("")
        logger.info("Session Retention:")
        retention_stats = memory.get_session_retention_stats()
        if retention_stats:
            logger.info(
                f"  Active sessions: {retention_stats.get('active_sessions', {}).get('count', 0)}"
            )
            logger.info(
                f"  Archived sessions: {retention_stats.get('archived_sessions', {}).get('count', 0)}"
            )
            logger.info(
                f"  Anonymous sessions: {retention_stats.get('anonymous', {}).get('count', 0)}"
            )
            logger.info(
                f"  With email: {retention_stats.get('with_email', {}).get('count', 0)}"
            )
            logger.info(
                f"  Active (7 days): {retention_stats.get('active_7d', {}).get('count', 0)}"
            )
            logger.info(
                f"  Active (30 days): {retention_stats.get('active_30d', {}).get('count', 0)}"
            )

        # Summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("CLEANUP JOB SUMMARY")
        logger.info("=" * 70)
        logger.info("Memory Blocks:")
        logger.info(f"  Auto-synced sessions: {synced_count}")
        logger.info(f"  Session blocks deleted: {session_deleted}")
        logger.info(f"  User blocks deleted: {user_deleted}")
        logger.info("")
        logger.info("Session Lifecycle:")
        logger.info(f"  Sessions archived: {sessions_archived}")
        logger.info(f"  Archived sessions deleted: {sessions_deleted}")
        logger.info(f"  Anonymous sessions deleted: {anonymous_deleted}")
        logger.info("")
        total_ops = (
            synced_count
            + session_deleted
            + user_deleted
            + sessions_archived
            + sessions_deleted
            + anonymous_deleted
        )
        logger.info(f"  Total operations: {total_ops}")

        if args.dry_run:
            logger.info("")
            logger.info("💡 This was a DRY RUN. No data was actually deleted.")
            logger.info("   Run without --dry-run to perform actual cleanup.")
        else:
            logger.info("")
            logger.info("✅ Cleanup job completed successfully")

        logger.info("=" * 70)

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"\n❌ Cleanup job failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
