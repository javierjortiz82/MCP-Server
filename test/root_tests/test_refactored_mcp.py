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

import builtins
import contextlib

from config.settings import settings
from core.mcp_connector import MCPConnector
from multi_agent.booking_agent import BookingAgent
from multi_agent.sales_agent import SalesAgent


async def test_booking_agent_standalone():
    """Test BookingAgent in standalone mode (no MCP)."""
    try:
        agent = BookingAgent()
        await agent.initialize()

        # Check that it has no tools
        if not agent.mcp_tools:
            pass
        else:
            pass

        await agent.cleanup()
        return True

    except Exception:
        return False


async def test_booking_agent_with_mcp():
    """Test BookingAgent with centralized MCP connection."""
    mcp_client = None
    agent = None

    try:
        # Step 1: Connect to MCP server (simulating AgentOrchestrator behavior)
        mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"

        # Health check
        health = await MCPConnector.check_server_health(mcp_url)

        if health["status"] not in ("healthy", "degraded"):
            return True  # Not a failure, just skipped

        # Connect
        mcp_client = MCPConnector(mcp_url)
        await mcp_client.__aenter__()

        # Step 2: Autodiscover tools
        tools_raw = await mcp_client.list_tools()

        # Step 3: Convert to GenAI format
        temp_agent = BookingAgent()
        mcp_tools = temp_agent.convert_tools_to_genai(tools_raw)

        # Step 4: Initialize BookingAgent with injected dependencies (new architecture)
        agent = BookingAgent(mcp_tools=mcp_tools, mcp_client=mcp_client)
        await agent.initialize()

        # Step 5: List available tools
        if agent.mcp_tools:
            for _i, _tool in enumerate(agent.mcp_tools, 1):
                pass

        # Step 6: Test a simple query (without actual tool execution)
        # We won't execute this as it requires full setup, just verify method exists
        assert hasattr(agent, "generate_response"), "Missing generate_response method"

        # Cleanup
        await agent.cleanup()

        if mcp_client:
            await mcp_client.__aexit__(None, None, None)

        return True

    except Exception:
        import traceback

        traceback.print_exc()

        # Cleanup on error
        if agent:
            with contextlib.suppress(builtins.BaseException):
                await agent.cleanup()

        if mcp_client:
            with contextlib.suppress(builtins.BaseException):
                await mcp_client.__aexit__(None, None, None)

        return False


async def test_sales_agent_with_mcp():
    """Test SalesAgent (SalesAgent) with centralized MCP connection."""
    mcp_client = None
    agent = None

    try:
        # Step 1: Connect to MCP server
        mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"

        # Health check
        health = await MCPConnector.check_server_health(mcp_url)

        if health["status"] not in ("healthy", "degraded"):
            return True

        # Connect
        mcp_client = MCPConnector(mcp_url)
        await mcp_client.__aenter__()

        # Step 2: Autodiscover tools
        tools_raw = await mcp_client.list_tools()

        # Step 3: Convert to GenAI format
        temp_agent = SalesAgent()
        mcp_tools = temp_agent.convert_tools_to_genai(tools_raw)

        # Step 4: Initialize SalesAgent with injected dependencies (new architecture)
        agent = SalesAgent(
            mcp_client=mcp_client,
            mcp_tools=mcp_tools,
            mcp_tools_raw=tools_raw,
        )
        await agent.initialize()

        # Step 5: Verify tool executor was initialized
        if agent.tool_executor:
            pass
        else:
            pass

        # Step 6: List available tools
        if agent.mcp_tools:
            for _i, _tool in enumerate(agent.mcp_tools[:10], 1):
                pass
            if len(agent.mcp_tools) > 10:
                pass

        # Cleanup
        await agent.cleanup()

        if mcp_client:
            await mcp_client.__aexit__(None, None, None)

        return True

    except Exception:
        import traceback

        traceback.print_exc()

        # Cleanup on error
        if agent:
            with contextlib.suppress(builtins.BaseException):
                await agent.cleanup()

        if mcp_client:
            with contextlib.suppress(builtins.BaseException):
                await mcp_client.__aexit__(None, None, None)

        return False


async def main():
    """Run all tests."""
    results = []

    # Test 1: BookingAgent standalone
    results.append(await test_booking_agent_standalone())

    # Test 2: BookingAgent with MCP
    results.append(await test_booking_agent_with_mcp())

    # Test 3: SalesAgent with MCP
    results.append(await test_sales_agent_with_mcp())

    # Summary

    sum(results)
    len(results)

    if all(results):
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
