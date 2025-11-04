#!/usr/bin/env python
"""Test the exact BookingAgent flow to reproduce the first request issue."""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Setup paths
agent_path = Path("agent/src").absolute()
client_mcp_path = Path("client_mcp").absolute()
sys.path.insert(0, str(agent_path))
sys.path.insert(0, str(client_mcp_path))

# Configure logging to focus on key issues
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] %(levelname)s - %(message)s'
)

# Focus on specific loggers
for logger_name in ['google.genai', 'urllib3']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

from multi_agent.booking_agent import BookingAgent
from core.mcp_connector import MCPConnector
from google.genai import types
import google.genai as genai

async def test_exact_booking_flow():
    """Test BookingAgent with exact flow including MCP connector."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return

    print("\n" + "="*80)
    print("BOOKING AGENT - EXACT FLOW TEST")
    print("="*80 + "\n")

    # Initialize Gemini client
    client = genai.Client(api_key=api_key)

    # Initialize MCP connector
    try:
        mcp_connector = MCPConnector(mcp_server_url="http://localhost:8009")
        await mcp_connector.initialize()
        print(f"✅ MCP Connector initialized")
    except Exception as e:
        print(f"⚠️ MCP Connector failed: {e}")
        print(f"   Proceeding with empty tools list\n")
        mcp_connector = None

    # Create BookingAgent
    agent = BookingAgent(
        api_key=api_key,
        model_name="gemini-2.5-flash",
        mcp_tools=[],  # Will be loaded via MCP or empty
        mcp_client=client,
    )

    # Initialize agent
    await agent.initialize()
    print(f"✅ BookingAgent initialized")
    print(f"   - Has tools: {len(agent.mcp_tools) > 0}")
    print(f"   - Language: {agent.language}\n")

    # Test query
    query = "quiero reservar"
    print(f"📝 FIRST REQUEST: '{query}'")
    print("-" * 80)

    try:
        response = await agent.generate_response(query)
        print(f"✅ SUCCESS (Response: {len(response)} chars)")
        print(f"   Content preview: {response[:150]}...\n")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}\n")

    print(f"📝 SECOND REQUEST: '{query}' (same query)")
    print("-" * 80)

    try:
        response = await agent.generate_response(query)
        print(f"✅ SUCCESS (Response: {len(response)} chars)")
        print(f"   Content preview: {response[:150]}...\n")
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}\n")

    print("="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_exact_booking_flow())
