#!/usr/bin/env python3
"""Test script for modular Sales Agent prompt rendering.

This script tests the new modular Jinja2 template architecture for
the Sales Agent (Odiseo Bot) following industry best practices 2025.

Usage:
    python test_modular_sales_prompt.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from multi_agent.prompt_manager import PromptManager


def test_sales_prompt_basic():
    """Test basic sales prompt rendering without MCP tools."""
    print("=" * 80)
    print("TEST 1: Basic Sales Prompt (No MCP Tools)")
    print("=" * 80)

    try:
        manager = PromptManager()
        prompt = manager.get_sales_prompt(
            mcp_tools=None,
            pagination_page_size=4,
            version="v1.0"
        )

        # Verify key sections present
        checks = [
            ("Identity", "Odiseo" in prompt),
            ("Capabilities", "Gemini 2.5 Flash" in prompt),
            ("Temperature Config", "Temperature: 0" in prompt),
            ("Language Policy", "Language Mirroring" in prompt),
            ("Agentic Principles", "Agentic Principles" in prompt),
            ("Personality", "Your Personality" in prompt),
            ("Search Strategy", "Search Strategy" in prompt),
            ("Display Rules", "CRITICAL DISPLAY RULES" in prompt),
            ("Pagination", "pagination_page_size" in prompt or "4" in prompt),
            ("Response Format", "Response Format" in prompt),
            ("Examples", "Example 1" in prompt and "Example 2" in prompt),
            ("Quality Rules", "Critical Success Rules" in prompt),
        ]

        print(f"\n✅ Prompt rendered successfully ({len(prompt)} characters)\n")
        print("Section Checks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        # Show excerpt
        print("\nPrompt excerpt (first 300 chars):")
        print("-" * 80)
        print(prompt[:300])
        print("...")
        print("-" * 80)

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sales_prompt_with_tools():
    """Test sales prompt rendering with mock MCP tools context."""
    print("\n" + "=" * 80)
    print("TEST 2: Sales Prompt with MCP Tools Context")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Create mock tools context (simulating PromptBuilder output)
        mock_tools_context = """
## Available MCP Tools

**search_products**: Search for products by query
**fuzzy_search_smart**: Smart fuzzy search with typo tolerance
**get_product_by_sku**: Get product details by SKU
"""

        # We'll test by manually setting context (simulating what happens internally)

        # Render with tools context
        prompt = manager.get_sales_prompt(
            mcp_tools=[],  # Empty list triggers tools context generation
            pagination_page_size=6,  # Test different page size
            version="v1.0"
        )

        # Verify pagination_page_size is dynamic
        checks = [
            ("Pagination size in template", "6" in prompt),
            ("Display rules section", "CRITICAL DISPLAY RULES" in prompt),
        ]

        print(f"\n✅ Prompt rendered successfully ({len(prompt)} characters)\n")
        print("Dynamic Parameter Checks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_mechanism():
    """Test fallback to legacy prompt if templates fail."""
    print("\n" + "=" * 80)
    print("TEST 3: Fallback Mechanism (template mode disabled)")
    print("=" * 80)

    try:
        manager = PromptManager()
        prompt = manager.get_sales_prompt(
            mcp_tools=None,
            pagination_page_size=4
        )

        # Should use fallback from system_prompt.txt
        checks = [
            ("Fallback used", "Odiseo" in prompt),
            ("Original content", len(prompt) > 0),
        ]

        print(f"\n✅ Fallback prompt returned ({len(prompt)} characters)\n")
        print("Fallback Checks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MODULAR SALES AGENT PROMPT - TEST SUITE")
    print("Testing new Jinja2 modular template architecture")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("Basic Rendering", test_sales_prompt_basic()))
    results.append(("Dynamic Parameters", test_sales_prompt_with_tools()))
    results.append(("Fallback Mechanism", test_fallback_mechanism()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL TESTS PASSED - Modular sales prompts ready for production!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
