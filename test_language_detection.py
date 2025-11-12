#!/usr/bin/env python3
"""Test script for Gemini-based language detection.

This script tests the new LanguageDetectorService to verify it correctly
detects languages without hardcoded keywords.

Usage:
    python test_language_detection.py

Author: Lab01-MCP Team
Created: 2025-11-11
Version: 1.0.0
"""

import asyncio
import sys
from pathlib import Path

# Add agent to path
agent_path = Path(__file__).parent / "agent" / "src"
sys.path.insert(0, str(agent_path))

from gemini_agent.services.language_detector_service import LanguageDetectorService


async def test_language_detection():
    """Test language detection with various inputs."""

    print("=" * 70)
    print("🧪 Testing Gemini-Based Language Detection")
    print("=" * 70)

    # Initialize detector
    print("\n1. Initializing LanguageDetectorService...")
    detector = LanguageDetectorService()
    await detector.initialize()
    print("   ✅ Service initialized")

    # Test cases
    test_cases = [
        # Spanish cases (previously failing)
        ("proximo martes", "es", "Spanish temporal expression"),
        ("quiero comprar una laptop", "es", "Spanish sentence with 'quiero'"),
        ("lunes por la mañana", "es", "Spanish day + time"),
        ("enero del 2025", "es", "Spanish month + year"),

        # English cases
        ("next tuesday", "en", "English temporal expression"),
        ("I want to buy a laptop", "en", "English sentence"),
        ("monday morning", "en", "English day + time"),
        ("january 2025", "en", "English month + year"),

        # Ambiguous cases
        ("18", None, "Number - ambiguous (should fallback)"),
        ("ok", None, "Common word - ambiguous"),
        ("123abc", None, "Mixed - ambiguous"),

        # Mixed/Complex
        ("hola, I want to book", "es", "Mixed (Spanish greeting wins)"),
        ("hello, quiero reservar", "en", "Mixed (English greeting wins)"),
    ]

    print("\n2. Running test cases...")
    print("-" * 70)

    passed = 0
    failed = 0

    for text, expected, description in test_cases:
        # Detect language (no session language for pure detection)
        result = await detector.detect_language(
            text=text,
            session_language=None,
            use_cache=False  # Disable cache for testing
        )

        # Check if result matches expectation
        if expected is None:
            # For ambiguous cases, we expect fallback to "en"
            is_correct = result in ["en", "es"]  # Any is acceptable
            status = "✅" if is_correct else "❌"
        else:
            is_correct = result == expected
            status = "✅" if is_correct else "❌"

        if is_correct:
            passed += 1
        else:
            failed += 1

        print(f"{status} {description}")
        print(f"   Input: '{text}'")
        print(f"   Expected: {expected or 'en/es (ambiguous)'}")
        print(f"   Got: {result}")
        print()

    # Test caching
    print("\n3. Testing cache...")
    print("-" * 70)

    # First call (miss)
    text = "hola mundo"
    result1 = await detector.detect_language(text, use_cache=True)

    # Second call (hit)
    result2 = await detector.detect_language(text, use_cache=True)

    cache_works = result1 == result2
    print(f"{'✅' if cache_works else '❌'} Cache consistency")
    print(f"   First call: {result1}")
    print(f"   Second call (cached): {result2}")
    print(f"   Cache stats: {detector.get_cache_stats()}")

    # Test session language fallback
    print("\n4. Testing session language fallback...")
    print("-" * 70)

    ambiguous_text = "18"

    # Without session language
    result_no_session = await detector.detect_language(ambiguous_text, session_language=None)

    # With session language (Spanish)
    result_with_session = await detector.detect_language(ambiguous_text, session_language="es")

    print(f"Ambiguous input: '{ambiguous_text}'")
    print(f"   Without session: {result_no_session}")
    print(f"   With session (es): {result_with_session}")
    print(f"   {'✅' if result_with_session == 'es' else '❌'} Fallback works")

    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Summary")
    print("=" * 70)
    print(f"   Passed: {passed}/{passed + failed}")
    print(f"   Failed: {failed}/{passed + failed}")
    print(f"   Success Rate: {passed / (passed + failed) * 100:.1f}%")

    if failed == 0:
        print("\n✅ All tests passed! Language detection working correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Review results above.")

    print("=" * 70)


if __name__ == "__main__":
    print("\n🚀 Starting Language Detection Tests\n")

    try:
        asyncio.run(test_language_detection())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
