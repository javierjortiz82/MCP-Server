#!/usr/bin/env python
"""Script to reproduce and diagnose the first request failure in BookingAgent."""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Setup paths
agent_path = Path("agent/src").absolute()
sys.path.insert(0, str(agent_path))

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/tmp/booking_test.log")
    ]
)

from multi_agent.booking_agent import BookingAgent

async def test_booking_agent():
    """Test BookingAgent with 'quiero reservar' query."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return

    print("\n" + "="*80)
    print("BOOKING AGENT TEST - FIRST REQUEST REPRODUCTION")
    print("="*80 + "\n")

    # Create fresh agent instance
    agent = BookingAgent(
        api_key=api_key,
        model_name="gemini-2.5-flash",
        mcp_tools=[],  # Will be loaded from MCP server
        mcp_client=None,
    )

    # Initialize
    await agent.initialize()
    print(f"✅ Agent initialized")
    print(f"   - Model: {agent.model_name}")
    print(f"   - Has MCP tools: {len(agent.mcp_tools) if agent.mcp_tools else 0}")
    print(f"   - Language: {agent.language}\n")

    # Test query
    query = "quiero reservar"

    print(f"📝 Query: '{query}'")
    print("-" * 80)

    try:
        # Make the call
        response = await agent.generate_response(query)
        print(f"\n✅ SUCCESS - Response received:")
        print(f"{response}\n")
    except Exception as e:
        print(f"\n❌ ERROR - {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()

    print("="*80)
    print("TEST COMPLETE - Check /tmp/booking_test.log for detailed logs")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_booking_agent())
