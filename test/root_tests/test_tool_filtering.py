#!/usr/bin/env python3
"""Test tool filtering by category.

This script verifies that agents receive only their relevant tools.
"""

import asyncio
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "client_mcp"))

from client_mcp.core.agent_orchestrator import AgentOrchestrator


async def main():
    """Test tool filtering."""
    # Create orchestrator
    orchestrator = AgentOrchestrator()

    try:
        # Initialize
        await orchestrator.initialize()

        # Check SalesAgent tools
        if orchestrator.sales_agent and orchestrator.sales_mcp_tools:
            sales_tool_names = [tool.name for tool in orchestrator.sales_mcp_tools]
            for _name in sales_tool_names:
                pass

            # Verify only product tools
            expected_tools = {
                "fetch_by_sku",
                "fetch_by_id",
                "search_products",
                "fuzzy_search_smart",
                "ingest_products",
            }
            unexpected = set(sales_tool_names) - expected_tools
            if unexpected or len(sales_tool_names) != 5:
                return False
            else:
                pass
        else:
            pass

        # Check BookingAgent tools
        if orchestrator.booking_agent and orchestrator.booking_mcp_tools:
            booking_tool_names = [tool.name for tool in orchestrator.booking_mcp_tools]
            for _name in booking_tool_names:
                pass

            # Verify only booking tools
            expected_tools = {
                "create_booking",
                "cancel_booking",
                "reschedule_booking",
                "get_available_slots",
                "get_booking_by_id",
                "list_customer_bookings",
                "get_services",
                "get_business_hours",
            }
            unexpected = set(booking_tool_names) - expected_tools
            if unexpected or len(booking_tool_names) != 8:
                return False
            else:
                pass
        else:
            pass

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False

    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
