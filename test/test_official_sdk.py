#!/usr/bin/env python3
"""Test MCP Connector Integration.

Tests the MCP Connector using official Anthropic MCP SDK.
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client_mcp.core.mcp_connector import MCPConnector


async def test_connection():
    """Test basic connection to MCP server."""
    try:
        async with MCPConnector("http://localhost:8009/mcp"):
            return True
    except Exception:
        return False


async def test_list_tools():
    """Test listing MCP tools."""
    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            tools = await client.list_tools()

            for _i, _tool in enumerate(tools, 1):
                pass

            return True
    except Exception:
        return False


async def test_call_tool():
    """Test calling an MCP tool."""
    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            # Test search_products tool
            result = await client.call_tool(
                "search_products",
                {"query": "laptop", "k": 3},
            )

            if result:
                if isinstance(result, list):
                    for _i, item in enumerate(result[:3], 1):
                        if isinstance(item, dict):
                            item.get("name", "N/A")
                else:
                    pass
            else:
                pass

            return True
    except Exception:
        return False


async def test_list_resources():
    """Test listing MCP resources."""
    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            resources = await client.list_resources()

            if resources:
                for _i, _resource in enumerate(resources, 1):
                    pass
            else:
                pass

            return True
    except Exception:
        return False


async def test_list_prompts():
    """Test listing MCP prompts."""
    try:
        async with MCPConnector("http://localhost:8009/mcp") as client:
            prompts = await client.list_prompts()

            if prompts:
                for _i, _prompt in enumerate(prompts, 1):
                    pass
            else:
                pass

            return True
    except Exception:
        return False


async def run_all_tests():
    """Run all tests."""
    results = []

    # Run tests
    results.append(await test_connection())
    results.append(await test_list_tools())
    results.append(await test_call_tool())
    results.append(await test_list_resources())
    results.append(await test_list_prompts())

    # Summary

    passed = sum(results)
    total = len(results)
    (passed / total) * 100

    if passed == total:
        pass
    else:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        pass
    except Exception:
        sys.exit(1)
