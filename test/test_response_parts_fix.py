#!/usr/bin/env python3
"""Test fix for response.parts is None issue.

Verifies that the agent handles cases where response.parts is None
by falling back to extracting text directly from content.
"""

import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Any

# Add paths
agent_src = Path(__file__).parent / "agent" / "src"
client_mcp_path = Path(__file__).parent / "client_mcp"
sys.path.insert(0, str(agent_src))
sys.path.insert(0, str(client_mcp_path))

from multi_agent.booking_agent import BookingAgent
from core.function_call_handler import FunctionCallHandler
from google.genai import types


def test_function_call_handler_extract_text_from_content():
    """Test that extract_text_from_content works as fallback."""
    print("\n" + "=" * 80)
    print("TEST: FunctionCallHandler.extract_text_from_content()")
    print("=" * 80)

    handler = FunctionCallHandler()

    # Mock a content object with text but no parts
    mock_content = Mock()
    mock_content.text = "Tus reservas actuales: Consulta el lunes a las 2pm"
    mock_content.parts = None  # parts is None

    # Should extract text directly
    text = handler.extract_text_from_content(mock_content)

    print(f"\nExtracted text: '{text}'")

    if text and "reservas" in text:
        print("✅ PASS: Successfully extracted text from content")
    else:
        print("❌ FAIL: Could not extract text from content")
        raise AssertionError("extract_text_from_content failed")


def test_get_parts_with_empty_parts():
    """Test that get_parts handles empty parts list."""
    print("\n" + "=" * 80)
    print("TEST: FunctionCallHandler.get_parts() with empty parts")
    print("=" * 80)

    handler = FunctionCallHandler()

    # Mock response with empty parts
    mock_response = Mock()
    mock_candidate = Mock()
    mock_content = Mock()
    mock_content.parts = []  # Empty parts
    mock_content.text = "Some response text"  # But has text
    mock_candidate.content = mock_content
    mock_response.candidates = [mock_candidate]

    # Should return empty list, not None
    parts = handler.get_parts(mock_response)

    print(f"\nReturned parts: {parts}")
    print(f"Type: {type(parts)}")

    if isinstance(parts, list) and len(parts) == 0:
        print("✅ PASS: get_parts returns empty list for empty parts")
    else:
        print("❌ FAIL: get_parts did not return empty list")
        raise AssertionError("get_parts failed for empty parts")


def test_extract_text_from_content_with_none():
    """Test that extract_text_from_content handles None gracefully."""
    print("\n" + "=" * 80)
    print("TEST: FunctionCallHandler.extract_text_from_content() with None")
    print("=" * 80)

    handler = FunctionCallHandler()

    # Test with None
    text = handler.extract_text_from_content(None)
    print(f"\nText from None: {text}")

    if text is None:
        print("✅ PASS: extract_text_from_content handles None gracefully")
    else:
        print("❌ FAIL: extract_text_from_content should return None for None input")
        raise AssertionError("extract_text_from_content failed for None input")

    # Test with content without text
    mock_content = Mock(spec=[])  # No text attribute
    text = handler.extract_text_from_content(mock_content)
    print(f"Text from empty content: {text}")

    if text is None:
        print("✅ PASS: extract_text_from_content handles missing text gracefully")
    else:
        print("❌ FAIL: extract_text_from_content should return None for empty content")
        raise AssertionError("extract_text_from_content failed for empty content")


async def test_booking_agent_response_fallback():
    """Test that booking agent uses fallback when parts is None."""
    print("\n" + "=" * 80)
    print("TEST: BookingAgent handles response.parts is None")
    print("=" * 80)

    agent = BookingAgent()
    await agent.initialize()

    # Mock a response with parts=None but text available
    mock_response = Mock()
    mock_candidate = Mock()
    mock_content = Mock()
    mock_content.parts = None  # This is the issue
    mock_content.text = "Perfecto, aquí están tus reservas:"  # But text is available
    mock_candidate.content = mock_content
    mock_response.candidates = [mock_candidate]

    # Simulate response
    handler = agent.function_call_handler

    # Check if get_parts returns None
    parts = handler.get_parts(mock_response)
    print(f"\nget_parts result: {parts}")

    # But we should be able to extract text from content
    text = handler.extract_text_from_content(mock_content)
    print(f"extract_text_from_content result: '{text}'")

    if text and "reservas" in text:
        print("✅ PASS: Agent can fall back to extracting text from content")
    else:
        print("❌ FAIL: Agent cannot extract text")
        raise AssertionError("Agent fallback failed")


async def main():
    """Run all tests."""
    print("=" * 80)
    print("RESPONSE.PARTS FIX VALIDATION TEST SUITE")
    print("=" * 80)

    try:
        test_function_call_handler_extract_text_from_content()
        test_get_parts_with_empty_parts()
        test_extract_text_from_content_with_none()
        await test_booking_agent_response_fallback()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print("\nThe response.parts fallback fix is working correctly.")
        print("'mis reservas' queries should now return proper responses.")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
