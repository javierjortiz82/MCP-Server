#!/usr/bin/env python3
"""Odiseo Memory Management CLI Tool.

Command-line interface for managing conversation sessions, memory blocks,
and context transfers in the Lab01-MCP memory system.

USAGE:
    python3 scripts/odiseo_memory.py sessions                    # List active sessions
    python3 scripts/odiseo_memory.py inspect <session_id>       # View session details
    python3 scripts/odiseo_memory.py user-profile <email>       # View user memory profile
    python3 scripts/odiseo_memory.py cleanup [--dry-run]        # Clean expired memories
    python3 scripts/odiseo_memory.py stats                       # Global statistics

EXAMPLES:
    # List all active sessions from last 7 days
    python3 scripts/odiseo_memory.py sessions

    # Inspect specific session
    python3 scripts/odiseo_memory.py inspect abc123...

    # View user cross-session memory profile
    python3 scripts/odiseo_memory.py user-profile user@example.com

    # Preview what would be cleaned (dry run)
    python3 scripts/odiseo_memory.py cleanup --dry-run

    # Actually clean expired memories
    python3 scripts/odiseo_memory.py cleanup

    # Show global statistics
    python3 scripts/odiseo_memory.py stats

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Add paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager
from utils.logger import setup_logging

# Setup logger
logger = setup_logging("odiseo_memory_cli")


# ============================================================================
# Helper Functions
# ============================================================================


def format_timestamp(timestamp: Any) -> str:
    """Format timestamp for display.

    Args:
        timestamp: datetime or string timestamp

    Returns:
        Formatted string like "2025-10-12 14:30:00"
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            return timestamp

    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    return str(timestamp)


def format_time_ago(timestamp: Any) -> str:
    """Format timestamp as "X hours/days ago".

    Args:
        timestamp: datetime or string timestamp

    Returns:
        Human-readable string like "2 hours ago" or "3 days ago"
    """
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except Exception:
            return "unknown"

    if not isinstance(timestamp, datetime):
        return "unknown"

    # Make timestamp timezone-aware if naive
    if timestamp.tzinfo is None:
        from datetime import timezone

        timestamp = timestamp.replace(tzinfo=timezone.utc)

    # Calculate delta
    from datetime import timezone

    now = datetime.now(timezone.utc)
    delta = now - timestamp

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif delta < timedelta(days=7):
        days = int(delta.total_seconds() / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return format_timestamp(timestamp)


def print_header(title: str) -> None:
    """Print formatted header.

    Args:
        title: Header title
    """
    print()
    print("=" * 70)
    print(title.center(70))
    print("=" * 70)


def print_section(title: str) -> None:
    """Print section divider.

    Args:
        title: Section title
    """
    print()
    print(f"{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


# ============================================================================
# Command Implementations
# ============================================================================


def cmd_sessions(memory: MemoryManager, args: argparse.Namespace) -> int:
    """List active sessions.

    Args:
        memory: MemoryManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success)
    """
    print_header("ACTIVE SESSIONS")

    try:
        # Get all sessions from database
        query = f"""
        SELECT
            session_id,
            customer_email,
            started_at,
            last_activity_at,
            current_agent,
            metadata
        FROM {memory.schema}.conversation_sessions
        WHERE last_activity_at >= NOW() - INTERVAL '7 days'
        ORDER BY last_activity_at DESC
        LIMIT 50
        """

        from utils.db import fetchall

        sessions = fetchall(query)

        if not sessions:
            print("\n  ℹ️  No active sessions found in last 7 days")
            return 0

        print(f"\n  Found {len(sessions)} active session(s):\n")

        # Print sessions
        for session in sessions:
            session_id = session["session_id"]
            email = session["customer_email"] or "anonymous"
            last_activity = format_time_ago(session["last_activity_at"])
            current_agent = session["current_agent"] or "none"
            started = format_timestamp(session["started_at"])

            print(f"  📌 {session_id[:16]}...")
            print(f"     Email: {email}")
            print(f"     Agent: {current_agent}")
            print(f"     Started: {started}")
            print(f"     Last activity: {last_activity}")
            print()

        print("\n  💡 Tip: Use 'inspect <session_id>' to view details")

        return 0

    except Exception as e:
        logger.exception(f"Failed to list sessions: {e}")
        print(f"\n  ❌ Error: {e}")
        return 1


def cmd_inspect(memory: MemoryManager, args: argparse.Namespace) -> int:
    """Inspect session details.

    Args:
        memory: MemoryManager instance
        args: Parsed arguments with session_id

    Returns:
        Exit code (0 for success)
    """
    session_id = args.session_id

    print_header(f"SESSION DETAILS: {session_id[:16]}...")

    try:
        # Get session info
        from utils.db import fetchone

        session_query = f"""
        SELECT session_id, customer_email, current_agent, started_at, last_activity_at
        FROM {memory.schema}.conversation_sessions
        WHERE session_id = %s
        """
        session_info = fetchone(session_query, (session_id,))

        if not session_info:
            print(f"\n  ❌ Session not found: {session_id}")
            return 1

        # Get session statistics
        stats = memory.get_session_statistics(session_info["session_id"])

        # Session info
        print_section("Session Information")
        print(f"  Session ID: {session_id}")
        print(f"  Customer: {session_info.get('customer_email') or 'anonymous'}")
        print(f"  Current Agent: {session_info.get('current_agent') or 'none'}")
        print(f"  Started: {format_timestamp(session_info.get('started_at'))}")
        print(
            f"  Last Activity: {format_time_ago(session_info.get('last_activity_at'))}"
        )
        if stats:
            print(f"  Duration: {stats.get('session_duration_minutes', 0):.1f} minutes")

        # Message statistics
        print_section("Message Statistics")
        if stats:
            print(f"  Total Messages: {stats.get('total_messages', 0)}")
            print(f"  User Messages: {stats.get('user_messages', 0)}")
            print(f"  Model Messages: {stats.get('model_messages', 0)}")
        else:
            print("  Total Messages: 0")

        # Memory blocks
        print_section("Memory Blocks")
        blocks = memory.get_active_memory_blocks(session_info["session_id"])
        print(f"  Active Memory Blocks: {len(blocks)}")

        if blocks:
            print("\n  Top 5 Memory Blocks:")
            for block in blocks[:5]:
                label = block["block_label"]
                value = block["block_value"][:60]
                priority = block["priority"]
                scope = block["agent_scope"]
                print(f"\n    [{label}] (priority={priority}, scope={scope})")
                print(f"    {value}...")

        # Context transfers
        print_section("Context Transfers")
        if stats:
            transfers = stats.get("context_transfers", 0)
            print(f"  Total Transfers: {transfers}")
        else:
            print("  Total Transfers: 0")

        # Recent messages
        print_section("Recent Messages (Last 5)")
        messages = memory.get_recent_messages(session_info["session_id"], limit=5)

        if messages:
            for msg in reversed(messages):
                role = msg["role"]
                text = msg["message_text"][:80]
                timestamp = format_timestamp(msg["created_at"])
                print(f"\n    [{timestamp}] {role}:")
                print(f"    {text}...")
        else:
            print("  No messages found")

        print()
        return 0

    except Exception as e:
        logger.exception(f"Failed to inspect session: {e}")
        print(f"\n  ❌ Error: {e}")
        return 1


def cmd_cleanup(memory: MemoryManager, args: argparse.Namespace) -> int:
    """Clean expired memory blocks.

    Args:
        memory: MemoryManager instance
        args: Parsed arguments with --dry-run flag

    Returns:
        Exit code (0 for success)
    """
    dry_run = args.dry_run

    if dry_run:
        print_header("CLEANUP PREVIEW (DRY RUN)")
    else:
        print_header("CLEANUP EXPIRED MEMORIES")

    try:
        # Count expired blocks
        query = f"""
        SELECT COUNT(*) as count
        FROM {memory.schema}.agent_memory_blocks
        WHERE expires_at IS NOT NULL AND expires_at < NOW()
        """

        from utils.db import fetchone

        result = fetchone(query)
        expired_count = result["count"] if result else 0

        print(f"\n  Found {expired_count} expired memory block(s)")

        if expired_count == 0:
            print("\n  ✅ Nothing to clean")
            return 0

        if dry_run:
            print("\n  💡 Run without --dry-run to actually delete these blocks")
            return 0

        # Perform cleanup
        delete_query = f"""
        DELETE FROM {memory.schema}.agent_memory_blocks
        WHERE expires_at IS NOT NULL AND expires_at < NOW()
        """

        from utils.db import execute

        execute(delete_query)

        print(f"\n  ✅ Deleted {expired_count} expired memory block(s)")

        return 0

    except Exception as e:
        logger.exception(f"Failed to cleanup: {e}")
        print(f"\n  ❌ Error: {e}")
        return 1


def cmd_user_profile(memory: MemoryManager, args: argparse.Namespace) -> int:
    """View user memory profile (cross-session).

    Args:
        memory: MemoryManager instance
        args: Parsed arguments with customer_email

    Returns:
        Exit code (0 for success)
    """
    customer_email = args.customer_email

    print_header(f"USER MEMORY PROFILE: {customer_email}")

    try:
        # Get user profile metadata
        profile = memory.get_user_profile(customer_email)

        if not profile:
            print(f"\n  ℹ️  No user profile found for: {customer_email}")
            print("\n  💡 Tip: User profiles are created automatically when a session")
            print("          is created with customer_email set.")
            return 0

        # Profile information
        print_section("Profile Information")
        print(f"  Customer Email: {profile.get('customer_email')}")
        print(f"  First Seen: {format_timestamp(profile.get('first_seen_at'))}")
        print(f"  Last Seen: {format_time_ago(profile.get('last_seen_at'))}")
        print(f"  Total Sessions: {profile.get('total_sessions', 0)}")
        print(f"  Preferred Agent: {profile.get('preferred_agent') or 'none'}")

        # User memory blocks
        print_section("Cross-Session Memory Blocks")
        user_blocks = memory.get_user_memory_blocks(
            customer_email=customer_email, agent_scope="shared"
        )
        print(f"  Active User Memory Blocks: {len(user_blocks)}")

        if user_blocks:
            print("\n  Top 10 User Memory Blocks (sorted by priority):")
            for block in user_blocks[:10]:
                label = block["block_label"]
                value = block["block_value"][:80]
                priority = block["priority"]
                scope = block["agent_scope"]
                extracted = format_time_ago(block["extracted_at"])
                source_sessions = block.get("source_session_ids", [])
                session_count = (
                    len(source_sessions) if isinstance(source_sessions, list) else 0
                )

                print(f"\n    [{label}] (priority={priority}, scope={scope})")
                print(f"    {value}...")
                print(f"    Extracted: {extracted} | From {session_count} session(s)")

        # Recent sessions for this user
        print_section("Recent Sessions")
        query = f"""
        SELECT session_id, started_at, last_activity_at, current_agent
        FROM {memory.schema}.conversation_sessions
        WHERE customer_email = %s
        ORDER BY last_activity_at DESC
        LIMIT 5
        """

        from utils.db import fetchall

        sessions = fetchall(query, (customer_email,))

        if sessions:
            print("\n  Last 5 sessions:")
            for session in sessions:
                session_id = session["session_id"]
                agent = session["current_agent"] or "none"
                last_activity = format_time_ago(session["last_activity_at"])
                print(f"\n    📌 {session_id[:16]}...")
                print(f"       Agent: {agent} | Last activity: {last_activity}")
        else:
            print("\n  No sessions found")

        print()
        return 0

    except Exception as e:
        logger.exception(f"Failed to get user profile: {e}")
        print(f"\n  ❌ Error: {e}")
        return 1


def cmd_stats(memory: MemoryManager, args: argparse.Namespace) -> int:
    """Show global statistics.

    Args:
        memory: MemoryManager instance
        args: Parsed arguments

    Returns:
        Exit code (0 for success)
    """
    print_header("GLOBAL MEMORY STATISTICS")

    try:
        from utils.db import fetchone

        # Total sessions
        query = f"SELECT COUNT(*) as count FROM {memory.schema}.conversation_sessions"
        result = fetchone(query)
        total_sessions = result["count"] if result else 0

        # Active sessions (last 7 days)
        query = f"""
        SELECT COUNT(*) as count
        FROM {memory.schema}.conversation_sessions
        WHERE last_activity_at >= NOW() - INTERVAL '7 days'
        """
        result = fetchone(query)
        active_sessions = result["count"] if result else 0

        # Total messages
        query = f"SELECT COUNT(*) as count FROM {memory.schema}.conversation_messages"
        result = fetchone(query)
        total_messages = result["count"] if result else 0

        # Total memory blocks
        query = f"SELECT COUNT(*) as count FROM {memory.schema}.agent_memory_blocks"
        result = fetchone(query)
        total_blocks = result["count"] if result else 0

        # Active memory blocks
        query = f"""
        SELECT COUNT(*) as count
        FROM {memory.schema}.agent_memory_blocks
        WHERE expires_at IS NULL OR expires_at > NOW()
        """
        result = fetchone(query)
        active_blocks = result["count"] if result else 0

        # Total context transfers
        query = f"SELECT COUNT(*) as count FROM {memory.schema}.agent_context_transfers"
        result = fetchone(query)
        total_transfers = result["count"] if result else 0

        # Print statistics
        print_section("Sessions")
        print(f"  Total Sessions: {total_sessions}")
        print(f"  Active (7 days): {active_sessions}")

        print_section("Messages")
        print(f"  Total Messages: {total_messages}")
        if total_sessions > 0:
            avg_messages = total_messages / total_sessions
            print(f"  Average per Session: {avg_messages:.1f}")

        print_section("Memory Blocks")
        print(f"  Total Blocks: {total_blocks}")
        print(f"  Active Blocks: {active_blocks}")
        if total_blocks > 0:
            expired = total_blocks - active_blocks
            print(f"  Expired Blocks: {expired}")

        print_section("Context Transfers")
        print(f"  Total Transfers: {total_transfers}")
        if active_sessions > 0:
            avg_transfers = total_transfers / active_sessions
            print(f"  Average per Session: {avg_transfers:.2f}")

        # Memory block breakdown by scope
        query = f"""
        SELECT agent_scope, COUNT(*) as count
        FROM {memory.schema}.agent_memory_blocks
        WHERE expires_at IS NULL OR expires_at > NOW()
        GROUP BY agent_scope
        ORDER BY count DESC
        """

        from utils.db import fetchall

        scope_breakdown = fetchall(query)

        if scope_breakdown:
            print_section("Memory Blocks by Scope")
            for row in scope_breakdown:
                scope = row["agent_scope"]
                count = row["count"]
                print(f"  {scope}: {count}")

        print()
        return 0

    except Exception as e:
        logger.exception(f"Failed to get statistics: {e}")
        print(f"\n  ❌ Error: {e}")
        return 1


# ============================================================================
# Main CLI
# ============================================================================


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code
    """
    # Check if memory is available
    if not MEMORY_AVAILABLE:
        print("\n❌ ERROR: MemoryManager not available")
        print("   Please check your configuration and database connection")
        return 1

    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Odiseo Memory Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/odiseo_memory.py sessions
  python3 scripts/odiseo_memory.py inspect abc123...
  python3 scripts/odiseo_memory.py user-profile user@example.com
  python3 scripts/odiseo_memory.py cleanup --dry-run
  python3 scripts/odiseo_memory.py stats
        """,
    )

    # Add subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # sessions command
    parser_sessions = subparsers.add_parser(
        "sessions", help="List active sessions from last 7 days"
    )

    # inspect command
    parser_inspect = subparsers.add_parser("inspect", help="Inspect session details")
    parser_inspect.add_argument("session_id", help="Session ID to inspect")

    # user-profile command
    parser_user_profile = subparsers.add_parser(
        "user-profile", help="View user memory profile (cross-session)"
    )
    parser_user_profile.add_argument(
        "customer_email", help="Customer email to view profile for"
    )

    # cleanup command
    parser_cleanup = subparsers.add_parser(
        "cleanup", help="Clean expired memory blocks"
    )
    parser_cleanup.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without actually deleting",
    )

    # stats command
    parser_stats = subparsers.add_parser("stats", help="Show global statistics")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Initialize MemoryManager
    try:
        memory = MemoryManager()
    except Exception as e:
        logger.exception(f"Failed to initialize MemoryManager: {e}")
        print(f"\n❌ ERROR: Failed to initialize MemoryManager: {e}")
        return 1

    # Execute command
    try:
        if args.command == "sessions":
            return cmd_sessions(memory, args)
        elif args.command == "inspect":
            return cmd_inspect(memory, args)
        elif args.command == "user-profile":
            return cmd_user_profile(memory, args)
        elif args.command == "cleanup":
            return cmd_cleanup(memory, args)
        elif args.command == "stats":
            return cmd_stats(memory, args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
