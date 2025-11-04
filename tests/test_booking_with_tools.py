#!/usr/bin/env python
"""Script to reproduce and diagnose the first request failure with tools loaded."""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Setup paths
agent_path = Path("agent/src").absolute()
mcp_path = Path("mcp_server").absolute()
sys.path.insert(0, str(agent_path))
sys.path.insert(0, str(mcp_path))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress verbose logs
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('google.generativeai').setLevel(logging.WARNING)

from multi_agent.booking_agent import BookingAgent
from mcp_handlers.booking_handlers import get_booking_tools
import google.genai as genai

async def test_booking_with_tools():
    """Test BookingAgent with tools loaded, first request."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return

    print("\n" + "="*80)
    print("BOOKING AGENT TEST WITH TOOLS - FIRST REQUEST")
    print("="*80 + "\n")

    # Initialize Gemini client
    genai.configure(api_key=api_key)
    client = genai.Client(api_key=api_key)

    # Load booking tools from MCP server
    booking_tools = get_booking_tools()
    print(f"✅ Loaded {len(booking_tools)} booking tools")
    for tool in booking_tools[:3]:
        print(f"   - {tool.name}")
    print(f"   ... ({len(booking_tools) - 3} more)\n")

    # Create agent with tools
    agent = BookingAgent(
        api_key=api_key,
        model_name="gemini-2.5-flash",
        mcp_tools=booking_tools,
        mcp_client=client,
    )

    # Initialize
    await agent.initialize()
    print(f"✅ Agent initialized")
    print(f"   - Model: {agent.model_name}")
    print(f"   - Has MCP tools: {len(agent.mcp_tools)}")
    print(f"   - Language: {agent.language}\n")

    # Test query
    query = "quiero reservar"

    print(f"📝 Query: '{query}'")
    print("-" * 80)

    try:
        # Make the call
        response = await agent.generate_response(query)
        print(f"\n✅ SUCCESS - Response received:")
        print(f"\n{response}\n")
    except Exception as e:
        print(f"\n❌ ERROR - {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()

    print("="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_booking_with_tools())
