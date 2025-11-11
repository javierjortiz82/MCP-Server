#!/usr/bin/env python3
"""Diagnostic script for thinking + cache compatibility issue.

This script tests different configurations to identify the root cause of:
"400 INVALID_ARGUMENT - thinking is not supported by this model"

Tests:
1. Thinking mode WITHOUT cache
2. Cache WITHOUT thinking mode
3. Both thinking + cache together
4. Model name verification
"""

import asyncio
import sys
from pathlib import Path

# Add client_mcp to path
client_mcp_path = Path(__file__).parent / "client_mcp"
sys.path.insert(0, str(client_mcp_path))

# Add agent to path
agent_path = Path(__file__).parent / "agent" / "src"
sys.path.insert(0, str(agent_path))

from config.settings import settings
from gemini_agent import GeminiAgent
from google.genai import types


class ThinkingCacheDiagnostic:
    """Diagnostic tool for thinking + cache compatibility."""

    def __init__(self):
        """Initialize diagnostic tool."""
        self.api_key = settings.get_api_key()
        self.model = settings.MODEL
        self.test_query = "¿Qué es 2 + 2?"

        print("=" * 80)
        print("🔍 DIAGNOSTIC: Thinking + Cache Compatibility")
        print("=" * 80)
        print(f"Model: {self.model}")
        print(f"API Key: {self.api_key[:20]}...{self.api_key[-10:]}")
        print(f"Test Query: {self.test_query}")
        print("=" * 80)
        print()

    async def test_thinking_without_cache(self) -> dict:
        """Test 1: Thinking mode WITHOUT cache."""
        print("\n" + "─" * 80)
        print("📊 TEST 1: Thinking mode WITHOUT cache")
        print("─" * 80)

        try:
            client = GeminiAgent(api_key=self.api_key, model_name=self.model)
            await client.initialize()

            # Build config with thinking but NO cache
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1024, include_thoughts=True
                ),
            )

            print("✅ Config built: thinking_budget=1024, no cache")
            print(f"📤 Sending request to {self.model}...")

            response = client.client.models.generate_content(
                model=self.model, contents=self.test_query, config=config
            )

            # Extract response text
            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            # Check for thoughts
            has_thoughts = False
            thoughts_count = 0
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "grounding_metadata"):
                    # Check usage metadata
                    if hasattr(response, "usage_metadata"):
                        thoughts_count = getattr(
                            response.usage_metadata, "thoughts_token_count", 0
                        )
                        has_thoughts = thoughts_count > 0

            print("✅ SUCCESS: Thinking mode works WITHOUT cache")
            print(f"   Response: {response_text[:100]}...")
            print(f"   Thoughts tokens: {thoughts_count}")

            return {
                "success": True,
                "response": response_text,
                "thoughts_tokens": thoughts_count,
                "has_thoughts": has_thoughts,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED: {error_msg}")

            # Check for specific errors
            is_thinking_error = "thinking is not supported" in error_msg.lower()
            is_400_error = "400" in error_msg

            return {
                "success": False,
                "error": error_msg,
                "is_thinking_error": is_thinking_error,
                "is_400_error": is_400_error,
            }

    async def test_cache_without_thinking(self) -> dict:
        """Test 2: Cache WITHOUT thinking mode."""
        print("\n" + "─" * 80)
        print("📊 TEST 2: Cache WITHOUT thinking mode")
        print("─" * 80)

        try:
            client = GeminiAgent(api_key=self.api_key, model_name=self.model)
            await client.initialize()

            # Create a cache with sufficient content (min 1024 tokens for gemini-2.5-flash)
            system_prompt = (
                """You are a highly skilled mathematics tutor with expertise in algebra,
            geometry, calculus, statistics, and number theory. Your role is to help students
            understand mathematical concepts through clear explanations, step-by-step problem solving,
            and real-world examples. You should:

            1. Break down complex problems into manageable steps
            2. Explain the reasoning behind each step
            3. Provide alternative solution methods when applicable
            4. Use visual descriptions and analogies to aid understanding
            5. Encourage critical thinking and problem-solving skills
            6. Adapt your explanations to the student's level of understanding
            7. Be patient and encouraging, fostering a positive learning environment
            8. Verify solutions and check for common errors
            9. Connect mathematical concepts to practical applications
            10. Build confidence in the student's mathematical abilities

            Always maintain mathematical accuracy while being approachable and supportive.
            When solving problems, show your work clearly and explain any mathematical notation
            or terminology that might be unfamiliar. If a problem has multiple solution paths,
            consider discussing the pros and cons of different approaches.

            For basic arithmetic like addition, subtraction, multiplication, and division,
            provide quick, accurate answers while explaining the underlying principles if needed.
            For more complex topics like algebra, geometry, trigonometry, calculus, or statistics,
            take time to explain concepts thoroughly, using examples and practice problems to
            reinforce understanding.

            Remember that every student learns differently - some prefer visual explanations,
            others respond better to logical proofs, and some need hands-on examples. Try to
            incorporate multiple teaching strategies to reach different learning styles.

            Your ultimate goal is not just to provide answers, but to help students develop
            strong mathematical reasoning skills and confidence in their ability to tackle
            challenging problems independently. """
                * 3
            )  # Repeat 3x to ensure >1024 tokens

            print(
                f"🔄 Creating context cache (system prompt: {len(system_prompt)} chars)..."
            )
            cached_content = client.client.caches.create(
                model=self.model,
                config=types.CreateCachedContentConfig(
                    contents=[
                        types.Content(
                            role="user", parts=[types.Part(text="Cache initialization")]
                        )
                    ],
                    system_instruction=system_prompt,
                    display_name="diagnostic_cache",
                    ttl="300s",
                ),
            )

            print(f"✅ Cache created: {cached_content.name}")

            # Build config with cache but NO thinking
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
                cached_content=cached_content.name,
            )

            print("📤 Sending request with cache (no thinking)...")

            response = client.client.models.generate_content(
                model=self.model, contents=self.test_query, config=config
            )

            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            # Check cache usage
            cache_hit = False
            if hasattr(response, "usage_metadata"):
                cache_hit = (
                    getattr(response.usage_metadata, "cached_content_token_count", 0)
                    > 0
                )

            print("✅ SUCCESS: Cache works WITHOUT thinking")
            print(f"   Response: {response_text[:100]}...")
            print(f"   Cache hit: {cache_hit}")

            # Cleanup cache
            client.client.caches.delete(name=cached_content.name)
            print("🗑️  Cache deleted")

            return {"success": True, "response": response_text, "cache_hit": cache_hit}

        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED: {error_msg}")

            return {"success": False, "error": error_msg}

    async def test_thinking_with_cache(self) -> dict:
        """Test 3: Both thinking + cache together."""
        print("\n" + "─" * 80)
        print("📊 TEST 3: Thinking + Cache TOGETHER")
        print("─" * 80)

        try:
            client = GeminiAgent(api_key=self.api_key, model_name=self.model)
            await client.initialize()

            # Create a cache with sufficient content (min 1024 tokens for gemini-2.5-flash)
            system_prompt = (
                """You are a highly skilled mathematics tutor with expertise in algebra,
            geometry, calculus, statistics, and number theory. Your role is to help students
            understand mathematical concepts through clear explanations, step-by-step problem solving,
            and real-world examples. You should:

            1. Break down complex problems into manageable steps
            2. Explain the reasoning behind each step
            3. Provide alternative solution methods when applicable
            4. Use visual descriptions and analogies to aid understanding
            5. Encourage critical thinking and problem-solving skills
            6. Adapt your explanations to the student's level of understanding
            7. Be patient and encouraging, fostering a positive learning environment
            8. Verify solutions and check for common errors
            9. Connect mathematical concepts to practical applications
            10. Build confidence in the student's mathematical abilities

            Always maintain mathematical accuracy while being approachable and supportive.
            When solving problems, show your work clearly and explain any mathematical notation
            or terminology that might be unfamiliar. If a problem has multiple solution paths,
            consider discussing the pros and cons of different approaches.

            For basic arithmetic like addition, subtraction, multiplication, and division,
            provide quick, accurate answers while explaining the underlying principles if needed.
            For more complex topics like algebra, geometry, trigonometry, calculus, or statistics,
            take time to explain concepts thoroughly, using examples and practice problems to
            reinforce understanding.

            Remember that every student learns differently - some prefer visual explanations,
            others respond better to logical proofs, and some need hands-on examples. Try to
            incorporate multiple teaching strategies to reach different learning styles.

            Your ultimate goal is not just to provide answers, but to help students develop
            strong mathematical reasoning skills and confidence in their ability to tackle
            challenging problems independently. """
                * 3
            )  # Repeat 3x to ensure >1024 tokens

            print(
                f"🔄 Creating context cache (system prompt: {len(system_prompt)} chars)..."
            )
            cached_content = client.client.caches.create(
                model=self.model,
                config=types.CreateCachedContentConfig(
                    contents=[
                        types.Content(
                            role="user", parts=[types.Part(text="Cache initialization")]
                        )
                    ],
                    system_instruction=system_prompt,
                    display_name="diagnostic_cache_with_thinking",
                    ttl="300s",
                ),
            )

            print(f"✅ Cache created: {cached_content.name}")

            # Build config with BOTH cache AND thinking
            config = types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=512,
                cached_content=cached_content.name,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=1024, include_thoughts=True
                ),
            )

            print("📤 Sending request with BOTH cache + thinking...")

            response = client.client.models.generate_content(
                model=self.model, contents=self.test_query, config=config
            )

            response_text = (
                response.text if hasattr(response, "text") else str(response)
            )

            # Check both cache and thoughts
            cache_hit = False
            thoughts_count = 0
            if hasattr(response, "usage_metadata"):
                cache_hit = (
                    getattr(response.usage_metadata, "cached_content_token_count", 0)
                    > 0
                )
                thoughts_count = getattr(
                    response.usage_metadata, "thoughts_token_count", 0
                )

            print("✅ SUCCESS: Thinking + Cache work TOGETHER")
            print(f"   Response: {response_text[:100]}...")
            print(f"   Cache hit: {cache_hit}")
            print(f"   Thoughts tokens: {thoughts_count}")

            # Cleanup cache
            client.client.caches.delete(name=cached_content.name)
            print("🗑️  Cache deleted")

            return {
                "success": True,
                "response": response_text,
                "cache_hit": cache_hit,
                "thoughts_tokens": thoughts_count,
            }

        except Exception as e:
            error_msg = str(e)
            print(f"❌ FAILED: {error_msg}")

            # Check for specific errors
            is_thinking_error = "thinking is not supported" in error_msg.lower()
            is_cache_error = (
                "cachedcontent" in error_msg.lower() or "cache" in error_msg.lower()
            )
            is_400_error = "400" in error_msg

            return {
                "success": False,
                "error": error_msg,
                "is_thinking_error": is_thinking_error,
                "is_cache_error": is_cache_error,
                "is_400_error": is_400_error,
            }

    def print_summary(self, results: dict) -> None:
        """Print diagnostic summary."""
        print("\n" + "=" * 80)
        print("📋 DIAGNOSTIC SUMMARY")
        print("=" * 80)

        test1 = results["test1"]
        test2 = results["test2"]
        test3 = results["test3"]

        print(
            f"\nTest 1 (Thinking only):  {'✅ PASS' if test1['success'] else '❌ FAIL'}"
        )
        print(
            f"Test 2 (Cache only):     {'✅ PASS' if test2['success'] else '❌ FAIL'}"
        )
        print(
            f"Test 3 (Both together):  {'✅ PASS' if test3['success'] else '❌ FAIL'}"
        )

        print("\n" + "─" * 80)
        print("🎯 DIAGNOSIS:")
        print("─" * 80)

        if test1["success"] and test2["success"] and test3["success"]:
            print("✅ ALL TESTS PASSED: No compatibility issues detected!")
            print("   Your configuration should work correctly.")
            print("   If you're still seeing errors, check:")
            print("   - Environment variables are loaded correctly")
            print("   - MCP tools configuration")

        elif not test1["success"] and test1.get("is_thinking_error"):
            print("❌ ROOT CAUSE: Thinking mode NOT supported by this model or API key")
            print("   Possible reasons:")
            print("   1. Model is not gemini-2.5-flash (might be preview/experimental)")
            print("   2. API key doesn't have access to thinking mode (free tier?)")
            print("   3. Regional restrictions")
            print(f"   Error: {test1['error']}")

        elif test1["success"] and test2["success"] and not test3["success"]:
            print("❌ ROOT CAUSE: Thinking + Cache are INCOMPATIBLE")
            print("   Both work individually but fail together.")
            print("   This is a known limitation/bug in the Google GenAI API.")
            print(f"   Error: {test3['error']}")
            print("\n   SOLUTION: Use mutual exclusion - enable only ONE at a time:")
            print("   - For cost savings (75%): Use cache, disable thinking")
            print("   - For better reasoning: Use thinking, disable cache")

        elif not test2["success"]:
            print("❌ ROOT CAUSE: Context caching issue")
            print(f"   Error: {test2['error']}")
            print("   Check:")
            print("   - Model supports caching (gemini-2.5-flash does)")
            print("   - API key has caching permissions")

        else:
            print("⚠️  INCONCLUSIVE: Multiple failures detected")
            print("   Review individual test errors above")

        print("=" * 80)


async def main():
    """Run diagnostic tests."""
    diagnostic = ThinkingCacheDiagnostic()

    results = {
        "test1": await diagnostic.test_thinking_without_cache(),
        "test2": await diagnostic.test_cache_without_thinking(),
        "test3": await diagnostic.test_thinking_with_cache(),
    }

    diagnostic.print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
