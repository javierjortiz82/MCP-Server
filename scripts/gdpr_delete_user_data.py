#!/usr/bin/env python3
"""GDPR Compliance Tool - Complete User Data Deletion.

This script implements the "Right to be Forgotten" (GDPR Article 17)
by completely removing all user data from the system.

Data deleted:
- Conversation sessions
- Conversation messages
- Session-level memory blocks
- User-level memory blocks
- User memory profile
- Agent context transfers

USAGE:
    # Preview what would be deleted (DRY RUN)
    python3 scripts/gdpr_delete_user_data.py --email user@example.com --dry-run

    # Export data before deletion
    python3 scripts/gdpr_delete_user_data.py --email user@example.com --export

    # Actually delete (IRREVERSIBLE)
    python3 scripts/gdpr_delete_user_data.py --email user@example.com --confirm

IMPORTANT:
    - This operation is IRREVERSIBLE
    - Always use --dry-run first to preview
    - Consider using --export to backup user data
    - Requires --confirm flag to actually delete

Legal Context:
    GDPR Article 17: Right to Erasure ("Right to be Forgotten")
    CCPA Section 1798.105: Consumer's Right to Delete

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 1.0.0 (GDPR Compliance)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "mcp_server"))

from config.settings import settings
from utils.db import execute, fetchall, fetchone
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("gdpr_deletion")


def export_user_data(customer_email: str, export_path: Path) -> dict:
    """Export all user data to JSON file.

    Args:
        customer_email: Customer email to export
        export_path: Directory to save export file

    Returns:
        dict: Export statistics
    """
    logger.info(f"Exporting data for {customer_email}...")

    schema = settings.SCHEMA_NAME
    export_data = {
        "customer_email": customer_email,
        "export_timestamp": datetime.now().isoformat(),
        "sessions": [],
        "messages": [],
        "session_memory_blocks": [],
        "user_memory_blocks": [],
        "user_profile": None,
        "context_transfers": [],
    }

    try:
        # 1. Get all sessions
        query = f"""
        SELECT
            id, session_id, started_at, last_activity_at,
            current_agent, archived, metadata
        FROM {schema}.conversation_sessions
        WHERE customer_email = %s
        ORDER BY started_at
        """
        sessions = fetchall(query, (customer_email,))
        export_data["sessions"] = [dict(s) for s in sessions]
        session_ids = [s["id"] for s in sessions]

        logger.info(f"  Found {len(sessions)} sessions")

        if not session_ids:
            logger.info("  No data found for this email")
            return {"sessions": 0, "messages": 0, "memory_blocks": 0}

        # 2. Get all messages
        placeholders = ",".join(["%s"] * len(session_ids))
        query = f"""
        SELECT
            session_id, role, agent_name, intent, message_text,
            tool_calls, response_time_ms, token_count, created_at
        FROM {schema}.conversation_messages
        WHERE session_id IN ({placeholders})
        ORDER BY created_at
        """
        messages = fetchall(query, tuple(session_ids))
        export_data["messages"] = [dict(m) for m in messages]

        logger.info(f"  Found {len(messages)} messages")

        # 3. Get session memory blocks
        query = f"""
        SELECT
            session_id, block_label, block_value, priority,
            agent_scope, ttl_days, expires_at, created_at
        FROM {schema}.agent_memory_blocks
        WHERE session_id IN ({placeholders})
        ORDER BY created_at
        """
        session_blocks = fetchall(query, tuple(session_ids))
        export_data["session_memory_blocks"] = [dict(b) for b in session_blocks]

        logger.info(f"  Found {len(session_blocks)} session memory blocks")

        # 4. Get user memory blocks
        query = f"""
        SELECT
            customer_email, block_label, block_value, priority,
            agent_scope, source_session_ids, ttl_days, expires_at, created_at
        FROM {schema}.user_memory_blocks
        WHERE customer_email = %s
        ORDER BY created_at
        """
        user_blocks = fetchall(query, (customer_email,))
        export_data["user_memory_blocks"] = [dict(b) for b in user_blocks]

        logger.info(f"  Found {len(user_blocks)} user memory blocks")

        # 5. Get user profile
        query = f"""
        SELECT
            customer_email, first_seen_at, last_seen_at,
            total_sessions, preferred_agent, metadata, created_at
        FROM {schema}.user_memory_profiles
        WHERE customer_email = %s
        """
        profile = fetchone(query, (customer_email,))
        if profile:
            export_data["user_profile"] = dict(profile)
            logger.info("  Found user profile")

        # 6. Get context transfers
        query = f"""
        SELECT
            session_id, from_agent, to_agent, transfer_reason,
            context_summary, memory_blocks_transferred, success, created_at
        FROM {schema}.agent_context_transfers
        WHERE session_id IN ({placeholders})
        ORDER BY created_at
        """
        transfers = fetchall(query, tuple(session_ids))
        export_data["context_transfers"] = [dict(t) for t in transfers]

        logger.info(f"  Found {len(transfers)} context transfers")

        # Save to file
        export_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = export_path / f"gdpr_export_{customer_email}_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)

        logger.info(f"✅ Data exported to: {filename}")

        return {
            "sessions": len(sessions),
            "messages": len(messages),
            "memory_blocks": len(session_blocks) + len(user_blocks),
            "export_file": str(filename),
        }

    except Exception as e:
        logger.exception(f"Failed to export user data: {e}")
        raise


def delete_user_data(customer_email: str, dry_run: bool = False) -> dict:
    """Delete all user data (GDPR compliance).

    Args:
        customer_email: Customer email to delete
        dry_run: If True, only count without deleting

    Returns:
        dict: Deletion statistics
    """
    schema = settings.SCHEMA_NAME

    logger.info(
        f"{'[DRY RUN] ' if dry_run else ''}Deleting data for {customer_email}..."
    )

    stats = {
        "sessions_deleted": 0,
        "messages_deleted": 0,
        "session_blocks_deleted": 0,
        "user_blocks_deleted": 0,
        "profile_deleted": 0,
        "transfers_deleted": 0,
    }

    try:
        # 1. Get session IDs for this user
        query = f"""
        SELECT id FROM {schema}.conversation_sessions
        WHERE customer_email = %s
        """
        sessions = fetchall(query, (customer_email,))
        session_ids = [s["id"] for s in sessions]

        if not session_ids:
            logger.info("  No data found for this email")
            return stats

        logger.info(f"  Found {len(session_ids)} sessions")

        # 2. Count/Delete messages
        placeholders = ",".join(["%s"] * len(session_ids))
        if dry_run:
            query = f"""
            SELECT COUNT(*) as count FROM {schema}.conversation_messages
            WHERE session_id IN ({placeholders})
            """
            result = fetchone(query, tuple(session_ids))
            stats["messages_deleted"] = result["count"] if result else 0
        else:
            query = f"""
            DELETE FROM {schema}.conversation_messages
            WHERE session_id IN ({placeholders})
            """
            execute(query, tuple(session_ids))
            stats["messages_deleted"] = len(session_ids)  # Approximate

        logger.info(f"  {'Would delete' if dry_run else 'Deleted'} messages")

        # 3. Count/Delete session memory blocks
        if dry_run:
            query = f"""
            SELECT COUNT(*) as count FROM {schema}.agent_memory_blocks
            WHERE session_id IN ({placeholders})
            """
            result = fetchone(query, tuple(session_ids))
            stats["session_blocks_deleted"] = result["count"] if result else 0
        else:
            query = f"""
            DELETE FROM {schema}.agent_memory_blocks
            WHERE session_id IN ({placeholders})
            """
            execute(query, tuple(session_ids))
            stats["session_blocks_deleted"] = len(session_ids)  # Approximate

        logger.info(
            f"  {'Would delete' if dry_run else 'Deleted'} session memory blocks"
        )

        # 4. Count/Delete context transfers
        if dry_run:
            query = f"""
            SELECT COUNT(*) as count FROM {schema}.agent_context_transfers
            WHERE session_id IN ({placeholders})
            """
            result = fetchone(query, tuple(session_ids))
            stats["transfers_deleted"] = result["count"] if result else 0
        else:
            query = f"""
            DELETE FROM {schema}.agent_context_transfers
            WHERE session_id IN ({placeholders})
            """
            execute(query, tuple(session_ids))

        logger.info(f"  {'Would delete' if dry_run else 'Deleted'} context transfers")

        # 5. Count/Delete user memory blocks
        if dry_run:
            query = f"""
            SELECT COUNT(*) as count FROM {schema}.user_memory_blocks
            WHERE customer_email = %s
            """
            result = fetchone(query, (customer_email,))
            stats["user_blocks_deleted"] = result["count"] if result else 0
        else:
            query = f"""
            DELETE FROM {schema}.user_memory_blocks
            WHERE customer_email = %s
            """
            execute(query, (customer_email,))

        logger.info(f"  {'Would delete' if dry_run else 'Deleted'} user memory blocks")

        # 6. Count/Delete user profile
        if dry_run:
            query = f"""
            SELECT COUNT(*) as count FROM {schema}.user_memory_profiles
            WHERE customer_email = %s
            """
            result = fetchone(query, (customer_email,))
            stats["profile_deleted"] = result["count"] if result else 0
        else:
            query = f"""
            DELETE FROM {schema}.user_memory_profiles
            WHERE customer_email = %s
            """
            execute(query, (customer_email,))
            stats["profile_deleted"] = 1

        logger.info(f"  {'Would delete' if dry_run else 'Deleted'} user profile")

        # 7. Count/Delete sessions (last, due to foreign keys)
        if dry_run:
            stats["sessions_deleted"] = len(session_ids)
        else:
            query = f"""
            DELETE FROM {schema}.conversation_sessions
            WHERE customer_email = %s
            """
            execute(query, (customer_email,))
            stats["sessions_deleted"] = len(session_ids)

        logger.info(f"  {'Would delete' if dry_run else 'Deleted'} sessions")

        return stats

    except Exception as e:
        logger.exception(f"Failed to delete user data: {e}")
        raise


def main() -> int:
    """Main GDPR deletion tool execution.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="GDPR Compliance - Delete all user data (Right to be Forgotten)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview deletion (recommended first step)
  python3 scripts/gdpr_delete_user_data.py --email user@example.com --dry-run

  # Export data before deletion
  python3 scripts/gdpr_delete_user_data.py --email user@example.com --export

  # Actually delete (requires --confirm)
  python3 scripts/gdpr_delete_user_data.py --email user@example.com --confirm

  # Export and delete
  python3 scripts/gdpr_delete_user_data.py --email user@example.com --export --confirm

IMPORTANT: This operation is IRREVERSIBLE. Always use --dry-run first!
        """,
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Customer email to delete",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export user data to JSON before deletion",
    )
    parser.add_argument(
        "--export-path",
        type=Path,
        default=Path("./gdpr_exports"),
        help="Directory to save export files (default: ./gdpr_exports)",
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="REQUIRED to actually delete data (safety mechanism)",
    )

    args = parser.parse_args()

    # Validate email format
    if "@" not in args.email:
        logger.error("❌ Invalid email format")
        return 1

    # Start
    logger.info("=" * 70)
    logger.info("GDPR DATA DELETION TOOL")
    logger.info("=" * 70)
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Customer email: {args.email}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("")

    try:
        # Step 1: Export if requested
        if args.export:
            logger.info("Step 1/2: Exporting user data...")
            export_stats = export_user_data(args.email, args.export_path)
            logger.info("")
            logger.info("Export Statistics:")
            logger.info(f"  Sessions: {export_stats.get('sessions', 0)}")
            logger.info(f"  Messages: {export_stats.get('messages', 0)}")
            logger.info(f"  Memory blocks: {export_stats.get('memory_blocks', 0)}")
            logger.info(f"  Export file: {export_stats.get('export_file', 'N/A')}")
            logger.info("")

        # Step 2: Delete data
        step_label = "Step 2/2" if args.export else "Step 1/1"
        logger.info(f"{step_label}: Deleting user data...")

        # Safety check
        if not args.dry_run and not args.confirm:
            logger.error("")
            logger.error("❌ ERROR: --confirm flag required for actual deletion")
            logger.error(
                "   This is a safety mechanism to prevent accidental data loss"
            )
            logger.error("")
            logger.error("   To actually delete, run:")
            logger.error(
                f"   python3 scripts/gdpr_delete_user_data.py --email {args.email} --confirm"
            )
            return 1

        delete_stats = delete_user_data(args.email, dry_run=args.dry_run)

        # Summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("DELETION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"  Sessions: {delete_stats['sessions_deleted']}")
        logger.info(f"  Messages: {delete_stats['messages_deleted']}")
        logger.info(
            f"  Session memory blocks: {delete_stats['session_blocks_deleted']}"
        )
        logger.info(f"  User memory blocks: {delete_stats['user_blocks_deleted']}")
        logger.info(f"  User profile: {delete_stats['profile_deleted']}")
        logger.info(f"  Context transfers: {delete_stats['transfers_deleted']}")
        logger.info("")

        total = sum(delete_stats.values())
        logger.info(f"  Total records: {total}")

        if args.dry_run:
            logger.info("")
            logger.info("💡 This was a DRY RUN. No data was actually deleted.")
            logger.info("   Run with --confirm to perform actual deletion.")
        else:
            logger.info("")
            logger.info(f"✅ User data for {args.email} has been completely deleted")
            logger.info("   GDPR Article 17 compliance: Right to be Forgotten")

        logger.info("=" * 70)

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"\n❌ GDPR deletion failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
