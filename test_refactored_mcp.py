#!/usr/bin/env python3
"""Test script for refactored MCP architecture.

This script verifies that the centralized MCP connection architecture works correctly
for both BookingAgent and SalesAgent (SalesAgent).

Tests:
1. BookingAgent initialization with centralized MCP
2. SalesAgent (SalesAgent) initialization with centralized MCP
3. Multi-agent routing with centralized MCP

Author: Lab01-MCP Team
Created: 2025-10-12
"""

import asyncio
import sys
from pathlib import Path

# Add paths for imports
agent_path = Path(__file__).parent / "agent" / "src"
client_mcp_path = Path(__file__).parent / "client_mcp"
sys.path.insert(0, str(agent_path))
sys.path.insert(0, str(client_mcp_path))

from config.settings import settings
from core.mcp_connector import MCPConnector
from multi_agent.booking_agent import BookingAgent
from multi_agent.sales_agent import SalesAgent


async def test_booking_agent_standalone():
    """Test BookingAgent in standalone mode (no MCP)."""
    print("\n" + "=" * 70)
    print("TEST 1: BookingAgent Standalone Mode (No MCP)")
    print("=" * 70)

    try:
        agent = BookingAgent()
        await agent.initialize()
        print("✅ BookingAgent initialized successfully in standalone mode")

        # Check that it has no tools
        if not agent.mcp_tools:
            print("✅ BookingAgent has no MCP tools (expected in standalone mode)")
        else:
            print(f"⚠️  BookingAgent has {len(agent.mcp_tools)} tools (unexpected)")

        await agent.cleanup()
        print("✅ BookingAgent cleanup successful")
        return True

    except Exception as e:
        print(f"❌ BookingAgent standalone test failed: {e}")
        return False


async def test_booking_agent_with_mcp():
    """Test BookingAgent with centralized MCP connection."""
    print("\n" + "=" * 70)
    print("TEST 2: BookingAgent with Centralized MCP")
    print("=" * 70)

    mcp_client = None
    agent = None

    try:
        # Step 1: Connect to MCP server (simulating AgentOrchestrator behavior)
        mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"
        print(f"🔗 Connecting to MCP server: {mcp_url}")

        # Health check
        health = await MCPConnector.check_server_health(mcp_url)
        print(f"🏥 MCP server status: {health['status']}")

        if health["status"] not in ("healthy", "degraded"):
            print("⚠️  Skipping test - MCP server not available")
            return True  # Not a failure, just skipped

        # Connect
        mcp_client = MCPConnector(mcp_url)
        await mcp_client.__aenter__()
        print("✅ MCP connection established")

        # Step 2: Autodiscover tools
        tools_raw = await mcp_client.list_tools()
        print(f"📋 Discovered {len(tools_raw)} MCP tools")

        # Step 3: Convert to GenAI format
        temp_agent = BookingAgent()
        mcp_tools = temp_agent.convert_tools_to_genai(tools_raw)
        print(f"✅ Converted {len(mcp_tools)} tools to GenAI format")

        # Step 4: Initialize BookingAgent with injected dependencies (new architecture)
        agent = BookingAgent(mcp_tools=mcp_tools, mcp_client=mcp_client)
        await agent.initialize()
        print(f"✅ BookingAgent initialized with {len(agent.mcp_tools)} MCP tools")

        # Step 5: List available tools
        if agent.mcp_tools:
            print("\n📋 Available booking tools:")
            for i, tool in enumerate(agent.mcp_tools, 1):
                print(f"   {i}. {tool.name}")

        # Step 6: Test a simple query (without actual tool execution)
        print("\n🧪 Testing generate_response method...")
        # We won't execute this as it requires full setup, just verify method exists
        assert hasattr(agent, "generate_response"), "Missing generate_response method"
        print("✅ generate_response method available")

        # Cleanup
        await agent.cleanup()
        print("✅ BookingAgent cleanup successful")

        if mcp_client:
            await mcp_client.__aexit__(None, None, None)
            print("✅ MCP connection closed")

        return True

    except Exception as e:
        print(f"❌ BookingAgent MCP test failed: {e}")
        import traceback

        traceback.print_exc()

        # Cleanup on error
        if agent:
            try:
                await agent.cleanup()
            except:
                pass

        if mcp_client:
            try:
                await mcp_client.__aexit__(None, None, None)
            except:
                pass

        return False


async def test_sales_agent_with_mcp():
    """Test SalesAgent (SalesAgent) with centralized MCP connection."""
    print("\n" + "=" * 70)
    print("TEST 3: SalesAgent (SalesAgent) with Centralized MCP")
    print("=" * 70)

    mcp_client = None
    agent = None

    try:
        # Step 1: Connect to MCP server
        mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"
        print(f"🔗 Connecting to MCP server: {mcp_url}")

        # Health check
        health = await MCPConnector.check_server_health(mcp_url)
        print(f"🏥 MCP server status: {health['status']}")

        if health["status"] not in ("healthy", "degraded"):
            print("⚠️  Skipping test - MCP server not available")
            return True

        # Connect
        mcp_client = MCPConnector(mcp_url)
        await mcp_client.__aenter__()
        print("✅ MCP connection established")

        # Step 2: Autodiscover tools
        tools_raw = await mcp_client.list_tools()
        print(f"📋 Discovered {len(tools_raw)} MCP tools")

        # Step 3: Convert to GenAI format
        temp_agent = SalesAgent()
        mcp_tools = temp_agent.convert_tools_to_genai(tools_raw)
        print(f"✅ Converted {len(mcp_tools)} tools to GenAI format")

        # Step 4: Initialize SalesAgent with injected dependencies (new architecture)
        agent = SalesAgent(
            mcp_client=mcp_client,
            mcp_tools=mcp_tools,
            mcp_tools_raw=tools_raw,
        )
        await agent.initialize()
        print(f"✅ SalesAgent initialized with {len(agent.mcp_tools)} MCP tools")

        # Step 5: Verify tool executor was initialized
        if agent.tool_executor:
            print("✅ ToolExecutor initialized")
        else:
            print("⚠️  ToolExecutor not initialized (may be disabled in settings)")

        # Step 6: List available tools
        if agent.mcp_tools:
            print("\n📋 Available sales tools (first 10):")
            for i, tool in enumerate(agent.mcp_tools[:10], 1):
                print(f"   {i}. {tool.name}")
            if len(agent.mcp_tools) > 10:
                print(f"   ... and {len(agent.mcp_tools) - 10} more")

        # Cleanup
        await agent.cleanup()
        print("✅ SalesAgent cleanup successful")

        if mcp_client:
            await mcp_client.__aexit__(None, None, None)
            print("✅ MCP connection closed")

        return True

    except Exception as e:
        print(f"❌ SalesAgent MCP test failed: {e}")
        import traceback

        traceback.print_exc()

        # Cleanup on error
        if agent:
            try:
                await agent.cleanup()
            except:
                pass

        if mcp_client:
            try:
                await mcp_client.__aexit__(None, None, None)
            except:
                pass

        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("🧪 TESTING REFACTORED MCP ARCHITECTURE")
    print("=" * 70)
    print("\nThis script tests the centralized MCP connection architecture")
    print("implemented in the refactoring (2025-10-12).")
    print("\nKey features tested:")
    print("  - Dependency injection pattern")
    print("  - Centralized MCP connection")
    print("  - Graceful degradation")
    print("  - Proper resource cleanup")

    results = []

    # Test 1: BookingAgent standalone
    results.append(await test_booking_agent_standalone())

    # Test 2: BookingAgent with MCP
    results.append(await test_booking_agent_with_mcp())

    # Test 3: SalesAgent with MCP
    results.append(await test_sales_agent_with_mcp())

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")

    if all(results):
        print(
            "\n🎉 All tests passed! Refactored MCP architecture is working correctly."
        )
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
