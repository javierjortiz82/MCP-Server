#!/usr/bin/env python
"""Diagnose the Gemini API configuration issue in BookingAgent."""

import asyncio
import sys
import os
import logging
from pathlib import Path
from unittest.mock import MagicMock

# Setup paths
agent_path = Path("agent/src").absolute()
sys.path.insert(0, str(agent_path))

# Configure logging to show only key messages
logging.basicConfig(
    level=logging.WARNING,
    format='%(name)s - %(levelname)s - %(message)s'
)

# Get specific loggers
booking_logger = logging.getLogger('multi_agent.booking_agent')
booking_logger.setLevel(logging.DEBUG)

from multi_agent.booking_agent import BookingAgent
from google.genai import types
import google.genai as genai

async def test_gemini_config_conflict():
    """Test if Gemini API has response_schema + function_calling conflict."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        return

    print("\n" + "="*80)
    print("GEMINI API CONFIGURATION CONFLICT DIAGNOSIS")
    print("="*80 + "\n")

    # Initialize Gemini
    client = genai.Client(api_key=api_key)

    # Create mock tools (similar to booking tools)
    mock_tools = [
        types.FunctionDeclaration(
            name="get_services",
            description="Get list of available services",
            parameters=types.Schema(
                type="object",
                properties={}
            )
        )
    ]

    # Test case 1: response_schema WITHOUT tools
    print("TEST 1: response_schema WITHOUT tools")
    print("-" * 80)
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="quiero reservar",
            config=types.GenerateContentConfig(
                response_schema=types.Schema(
                    type="object",
                    properties={"intent": types.Schema(type="string")}
                ),
                system_instruction="You are a helpful assistant.",
                temperature=0.3,
            )
        )
        print(f"✅ Response received (has parts: {bool(response.candidates[0].content.parts if response.candidates else None)})")
        if response.candidates:
            print(f"   Parts: {response.candidates[0].content.parts if response.candidates[0].content else None}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

    # Test case 2: function_calling WITHOUT response_schema
    print("TEST 2: function_calling WITHOUT response_schema")
    print("-" * 80)
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="quiero reservar",
            config=types.GenerateContentConfig(
                tools=[types.Tool(function_declarations=mock_tools)],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO
                    )
                ),
                system_instruction="You are a booking assistant.",
                temperature=0.3,
            )
        )
        print(f"✅ Response received (has parts: {bool(response.candidates[0].content.parts if response.candidates else None)})")
        if response.candidates:
            print(f"   Parts: {response.candidates[0].content.parts if response.candidates[0].content else None}\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

    # Test case 3: response_schema WITH function_calling (CONFLICT!)
    print("TEST 3: response_schema WITH function_calling (POTENTIAL CONFLICT)")
    print("-" * 80)
    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents="quiero reservar",
            config=types.GenerateContentConfig(
                response_schema=types.Schema(
                    type="object",
                    properties={"intent": types.Schema(type="string")}
                ),
                tools=[types.Tool(function_declarations=mock_tools)],
                tool_config=types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO
                    )
                ),
                system_instruction="You are a booking assistant.",
                temperature=0.3,
            )
        )
        print(f"✅ Response received (has parts: {bool(response.candidates[0].content.parts if response.candidates else None)})")
        if response.candidates:
            print(f"   Parts: {response.candidates[0].content.parts if response.candidates[0].content else None}\n")
        if response.candidates and response.candidates[0].content.parts is None:
            print("   🚨 WARNING: response.parts is None (CONFLICT DETECTED!)\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

    print("="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_gemini_config_conflict())
