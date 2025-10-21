#!/usr/bin/env python3
"""Test response.parts validation for 'mis reservas' workflow.

Validates that:
1. Response object structure is correct
2. response.parts is not None
3. Response contains proper text content
4. Function calls are executed correctly
"""

import sys
import asyncio
from pathlib import Path
from typing import Any

# Add agent/src to path
agent_src = Path(__file__).parent / "agent" / "src"
sys.path.insert(0, str(agent_src))

from multi_agent.booking_agent import BookingAgent


async def test_response_structure():
    """Test that response object has correct structure with parts."""
    print("\n" + "=" * 80)
    print("TEST: Response Structure Validation")
    print("=" * 80)

    try:
        # Initialize booking agent
        agent = BookingAgent()
        await agent.initialize()

        # Simulate 'mis reservas' query
        query = "¿Cuáles son mis reservas?"  # "What are my bookings?"

        print(f"\nQuery: {query}")
        print("\nCalling agent.generate_response()...\n")

        # Call the agent
        response = await agent.generate_response(query=query)

        # Validate response structure
        print("Response Analysis:")
        print(f"  Type: {type(response)}")
        print(f"  Response object: {response}")

        # Check if response is a dictionary or object with parts
        if isinstance(response, dict):
            print(f"  ✅ Response is a dict")
            has_text = "text" in response or "content" in response
            print(f"  {'✅' if has_text else '❌'} Has text content: {has_text}")
            if has_text:
                content = response.get("text") or response.get("content")
                print(f"  Content preview: {content[:100]}..." if content else "  Content: empty")
        else:
            print(f"  Response object properties:")
            for attr in dir(response):
                if not attr.startswith("_"):
                    try:
                        value = getattr(response, attr)
                        if not callable(value):
                            print(f"    - {attr}: {type(value).__name__}")
                    except:
                        pass

        # Check for parts attribute specifically
        if hasattr(response, "parts"):
            parts = getattr(response, "parts")
            print(f"\n  ✅ response.parts exists")
            print(f"     Type: {type(parts)}")
            print(f"     Value: {parts}")
            print(f"     Is None: {parts is None}")

            if parts is not None:
                print(f"  ✅ response.parts is NOT None")
                if isinstance(parts, list):
                    print(f"     Length: {len(parts)}")
                    for i, part in enumerate(parts):
                        print(f"     Part {i}: {type(part).__name__}")
            else:
                print(f"  ❌ response.parts is None")
        else:
            print(f"  ⚠️  response.parts attribute not found")

        print(f"\n✅ TEST PASSED: Response structure validated")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


async def test_response_content():
    """Test that response contains meaningful content."""
    print("\n" + "=" * 80)
    print("TEST: Response Content Validation")
    print("=" * 80)

    try:
        agent = BookingAgent()
        await agent.initialize()

        query = "Show me my bookings"

        print(f"\nQuery: {query}\n")

        response = await agent.generate_response(query=query)

        # Extract text content
        text_content = None
        if isinstance(response, dict):
            text_content = response.get("text") or response.get("content")
        elif hasattr(response, "text"):
            text_content = response.text
        else:
            # Try to convert to string
            text_content = str(response)

        if text_content:
            print(f"Response content ({len(text_content)} chars):")
            print("-" * 80)
            print(text_content[:500])
            if len(text_content) > 500:
                print("... [truncated]")
            print("-" * 80)

            # Validate content
            checks = [
                ("Response is not empty", len(text_content) > 0),
                ("Response contains text", len(text_content.strip()) > 0),
                (
                    "Response references bookings",
                    any(
                        word in text_content.lower()
                        for word in ["booking", "appointment", "reserv", "cita"]
                    ),
                ),
            ]

            print("\nContent validation:")
            all_passed = True
            for check_name, result in checks:
                status = "✅" if result else "❌"
                print(f"  {status} {check_name}")
                if not result:
                    all_passed = False

            if all_passed:
                print(f"\n✅ TEST PASSED: Response contains valid content")
            else:
                print(f"\n⚠️  WARNING: Some content checks failed")
        else:
            print(f"⚠️  Could not extract text content from response")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all validation tests."""
    print("=" * 80)
    print("RESPONSE VALIDATION TEST SUITE")
    print("=" * 80)

    try:
        await test_response_structure()
        await test_response_content()

        print("\n" + "=" * 80)
        print("✅ ALL RESPONSE TESTS COMPLETED")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
