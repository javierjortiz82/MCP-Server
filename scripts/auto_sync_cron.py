#!/usr/bin/env python3
"""Auto-Sync Cron Job - Sync Inactive Sessions to User Memory.

Lightweight cron job that only performs auto-sync of inactive sessions.
Can be run more frequently than full cleanup job (e.g., every 30 minutes).

USAGE:
    python3 scripts/auto_sync_cron.py

CRON SETUP:
    # Run every 30 minutes
    */30 * * * * /usr/bin/python3 /path/to/scripts/auto_sync_cron.py

    # Run every hour
    0 * * * * /usr/bin/python3 /path/to/scripts/auto_sync_cron.py

    # Run every 2 hours
    0 */2 * * * /usr/bin/python3 /path/to/scripts/auto_sync_cron.py

Example with logging:
    */30 * * * * /usr/bin/python3 /path/to/scripts/auto_sync_cron.py >> /var/log/auto_sync.log 2>&1

Author: Lab01-MCP Team
Created: 2025-10-13
Version: 1.0.0 (Fase 6.1 - Auto-Sync Cron)
"""

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
logger = setup_logging("auto_sync_cron")


def main() -> int:
    """Main auto-sync execution.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"[{timestamp}] Starting auto-sync job...")

    # Check prerequisites
    if not MEMORY_AVAILABLE:
        logger.error("❌ ERROR: MemoryManager not available")
        return 1

    try:
        memory = MemoryManager()

        # Call PostgreSQL function to auto-sync
        from utils.db import fetchall

        query = f"SELECT * FROM {memory.schema}.auto_sync_inactive_sessions(30)"
        results = fetchall(query)

        if results:
            logger.info(f"✅ Auto-synced {len(results)} inactive sessions:")
            for row in results:
                session_id = str(row.get("session_id", ""))[:8]
                email = row.get("customer_email", "unknown")
                synced = row.get("synced_blocks", 0)
                updated = row.get("updated_blocks", 0)
                logger.info(
                    f"   - {session_id}... ({email}): {synced} new, {updated} updated"
                )
        else:
            logger.info("No inactive sessions needed auto-sync")

        return 0

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Interrupted by user")
        return 130

    except Exception as e:
        logger.exception(f"❌ Auto-sync job failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
