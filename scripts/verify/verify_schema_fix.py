#!/usr/bin/env python3
"""
Verify that Context parameter is properly excluded from MCP tool schemas.
"""

import asyncio
import sys

sys.path.insert(0, "/home/javort/Lab01-MCP/mcp_server")

# Import the tool functions directly
from mcp.server.fastmcp import FastMCP


async def verify_schemas():
    print("=" * 80)
    print(" CONTEXT PARAMETER FIX VERIFICATION")
    print("=" * 80)
    print()

    # Create a test MCP instance
    mcp = FastMCP("test_server")

    # Initialize handlers (this registers all booking tools)
    from mcp_handlers import booking_handlers

    booking_handlers.init_booking_handlers(mcp)

    # Get registered tools (async call)
    tools = await mcp.list_tools()

    print(f"✅ Found {len(tools)} registered tools")
    print()

    return tools


async def main():
    tools = await verify_schemas()

    # Check each booking tool
    booking_tools = [
        "create_booking",
        "cancel_booking",
        "reschedule_booking",
        "get_available_slots",
        "get_booking_by_id",
        "list_customer_bookings",
        "get_services",
        "get_business_hours",
    ]

    success_count = 0
    failure_count = 0

    for tool_name in booking_tools:
        tool = next((t for t in tools if t.name == tool_name), None)

        if not tool:
            print(f"❌ {tool_name}: NOT FOUND")
            failure_count += 1
            continue

        schema = tool.inputSchema
        properties = list(schema.get("properties", {}).keys()) if schema else []
        required = schema.get("required", []) if schema else []

        # Check if 'ctx' is in schema (it should NOT be)
        has_ctx = "ctx" in properties or "ctx" in required

        if has_ctx:
            print(f"❌ {tool_name}:")
            print(f"   Properties: {properties}")
            print(f"   Required: {required}")
            print("   ERROR: 'ctx' parameter found in schema!")
            failure_count += 1
        else:
            print(f"✅ {tool_name}:")
            print(f"   Properties: {properties}")
            print(f"   Required: {required}")
            success_count += 1

        print()

    print("=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print(f"✅ Passed: {success_count}/{len(booking_tools)}")
    print(f"❌ Failed: {failure_count}/{len(booking_tools)}")
    print()

    if failure_count == 0:
        print("🎉 ALL TESTS PASSED!")
        print("✅ Context parameter is properly excluded from all tool schemas")
        print("✅ The fix is successful - FastMCP is auto-injecting Context correctly")
    else:
        print("⚠️ SOME TESTS FAILED")
        print("❌ Context parameter is still appearing in tool schemas")
        print("❌ The fix may not be complete")

    print("=" * 80)

    sys.exit(0 if failure_count == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
