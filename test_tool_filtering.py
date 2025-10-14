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
    print("=" * 70)
    print("🧪 Testing Tool Filtering by Category")
    print("=" * 70)

    # Create orchestrator
    orchestrator = AgentOrchestrator()

    try:
        # Initialize
        print("\n[1/3] Initializing agent orchestrator...")
        await orchestrator.initialize()
        print("   ✅ Orchestrator initialized")

        # Check SalesAgent tools
        print("\n[2/3] Checking SalesAgent tools...")
        if orchestrator.sales_agent and orchestrator.sales_mcp_tools:
            sales_tool_names = [tool.name for tool in orchestrator.sales_mcp_tools]
            print(f"   📦 SalesAgent has {len(sales_tool_names)} tools:")
            for name in sales_tool_names:
                print(f"      - {name}")

            # Verify only product tools
            expected_tools = {
                "fetch_by_sku",
                "fetch_by_id",
                "search_products",
                "fuzzy_search_smart",
                "ingest_products",
            }
            unexpected = set(sales_tool_names) - expected_tools
            if unexpected:
                print(f"   ❌ FAIL: SalesAgent has unexpected tools: {unexpected}")
                return False
            elif len(sales_tool_names) != 5:
                print(
                    f"   ❌ FAIL: SalesAgent should have 5 tools, has {len(sales_tool_names)}"
                )
                return False
            else:
                print("   ✅ SUCCESS: SalesAgent has only product tools!")
        else:
            print("   ⚠️  SalesAgent not initialized with tools")

        # Check BookingAgent tools
        print("\n[3/3] Checking BookingAgent tools...")
        if orchestrator.booking_agent and orchestrator.booking_mcp_tools:
            booking_tool_names = [tool.name for tool in orchestrator.booking_mcp_tools]
            print(f"   📅 BookingAgent has {len(booking_tool_names)} tools:")
            for name in booking_tool_names:
                print(f"      - {name}")

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
            if unexpected:
                print(f"   ❌ FAIL: BookingAgent has unexpected tools: {unexpected}")
                return False
            elif len(booking_tool_names) != 8:
                print(
                    f"   ❌ FAIL: BookingAgent should have 8 tools, has {len(booking_tool_names)}"
                )
                return False
            else:
                print("   ✅ SUCCESS: BookingAgent has only booking tools!")
        else:
            print("   ⚠️  BookingAgent not initialized with tools")

        return True

    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await orchestrator.cleanup()
        print("\n" + "=" * 70)
        print("✅ Test completed")
        print("=" * 70)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
