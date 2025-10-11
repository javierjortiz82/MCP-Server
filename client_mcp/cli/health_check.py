#!/usr/bin/env python3
"""Health check CLI for Odiseo Bot.

This script provides a command-line interface to check the health
of the Odiseo Bot client and its dependencies.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add client_mcp directory to path to import client modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from monitoring.client_health import ClientHealthMonitor


async def main():
    """Main health check function."""
    parser = argparse.ArgumentParser(description="Health check for Odiseo Bot")
    parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        help="Output format (default: human)",
    )
    parser.add_argument(
        "--component",
        choices=["bot", "mcp", "gemini", "resources", "all"],
        default="all",
        help="Component to check (default: all)",
    )
    parser.add_argument("--exit-code", action="store_true", help="Exit with non-zero code if unhealthy")

    args = parser.parse_args()

    # Create health monitor
    monitor = ClientHealthMonitor()

    # Run specific check or all checks
    if args.component == "all":
        health_data = await monitor.get_full_health()
    else:
        # Run specific component check
        check_method = {
            "bot": monitor.check_bot_status,
            "mcp": monitor.check_mcp_connectivity,
            "gemini": monitor.check_gemini_api,
            "resources": monitor.check_system_resources,
        }[args.component]

        check_result = await check_method()
        health_data = {
            "status": check_result.status.value,
            "timestamp": (check_result.timestamp.isoformat() if check_result.timestamp else None),
            "checks": [check_result.to_dict()],
        }

    # Output results
    if args.format == "json":
        print(json.dumps(health_data, indent=2))
    else:
        monitor.print_health_status(health_data)

    # Exit code handling
    if args.exit_code:
        if health_data["status"] == "unhealthy":
            sys.exit(1)
        elif health_data["status"] == "degraded":
            sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
