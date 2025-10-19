#!/usr/bin/env python3
"""Diagnostic script to test BookingAgent MCP tool availability.

This script helps debug why the booking agent says tools are not available.
"""

import asyncio
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "client_mcp"))
sys.path.insert(0, str(project_root / "agent" / "src"))

from multi_agent.booking_agent import BookingAgent

from client_mcp.core.mcp_connector import MCPConnector


async def main():
    """Diagnose booking agent initialization and tool availability."""
    print("=" * 70)
    print("🔍 BookingAgent MCP Tool Availability Diagnostic")
    print("=" * 70)

    # Step 1: Test MCP server health
    print("\n[1/5] Testing MCP server health...")
    mcp_url = "http://localhost:8009/mcp"
    health = await MCPConnector.check_server_health(mcp_url)
    print(f"   Status: {health.get('status')}")

    if health.get("status") != "healthy":
        print(f"   ❌ MCP server not healthy: {health}")
        return
    print("   ✅ MCP server is healthy")

    # Step 2: Connect to MCP server
    print("\n[2/5] Connecting to MCP server...")
    try:
        mcp_client = MCPConnector(mcp_url)
        await mcp_client.__aenter__()
        print("   ✅ Connected to MCP server")
    except Exception as e:
        print(f"   ❌ Failed to connect: {e}")
        return

    # Step 3: List available tools
    print("\n[3/5] Discovering MCP tools...")
    try:
        tools = await mcp_client.list_tools()
        print(f"   ✅ Discovered {len(tools)} tools:")
        for tool in tools:
            print(f"      - {tool['name']}: {tool['description'][:60]}...")
    except Exception as e:
        print(f"   ❌ Failed to list tools: {e}")
        await mcp_client.__aexit__(None, None, None)
        return

    # Step 4: Convert tools to GenAI format
    print("\n[4/5] Converting tools to GenAI format...")
    try:
        temp_agent = BookingAgent()
        genai_tools = temp_agent.convert_tools_to_genai(tools)
        print(f"   ✅ Converted {len(genai_tools)} tools to GenAI format")
        for tool in genai_tools:
            print(f"      - {tool.name}")
    except Exception as e:
        print(f"   ❌ Failed to convert tools: {e}")
        await mcp_client.__aexit__(None, None, None)
        return

    # Step 5: Initialize BookingAgent with tools
    print("\n[5/5] Initializing BookingAgent with MCP tools...")
    try:
        booking_agent = BookingAgent(
            mcp_tools=genai_tools,
            mcp_client=mcp_client,
        )
        await booking_agent.initialize()

        print("   ✅ BookingAgent initialized")
        print(
            f"   - MCP tools: {len(booking_agent.mcp_tools) if booking_agent.mcp_tools else 0}"
        )
        print(
            f"   - MCP client: {'✅ Available' if booking_agent.mcp_client else '❌ Not available'}"
        )
        print(
            f"   - Function handler: {'✅ Available' if booking_agent.function_call_handler else '❌ Not available'}"
        )

        # Test a simple query
        print("\n[TEST] Testing booking agent with a query...")
        response = await booking_agent.generate_response(
            "¿Qué servicios tienen disponibles?", customer_email="test@example.com"
        )
        print(f"\n   Response preview: {response[:200]}...")

        # Cleanup
        await booking_agent.cleanup()
        print("\n   ✅ Test completed successfully")

    except Exception as e:
        print(f"   ❌ Failed to initialize BookingAgent: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await mcp_client.__aexit__(None, None, None)

    print("\n" + "=" * 70)
    print("✅ Diagnostic completed")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
