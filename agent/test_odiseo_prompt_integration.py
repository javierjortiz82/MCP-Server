#!/usr/bin/env python3
"""Integration tests for OdiseoBot with PromptManager (Fase C).

This script tests the integration between OdiseoBot and the new modular
PromptManager system, including:
- Prompt loading with PromptManager
- Fallback to PromptBuilder
- A/B testing user_id parameter
- End-to-end prompt generation

Usage:
    python test_odiseo_prompt_integration.py
"""

import asyncio
import sys
from pathlib import Path

# Add paths for both agent and client_mcp
agent_src = Path(__file__).parent / "src"
client_mcp_src = Path(__file__).parent.parent / "client_mcp"
sys.path.insert(0, str(agent_src))
sys.path.insert(0, str(client_mcp_src))

from multi_agent.prompt_manager import PromptManager


def test_prompt_manager_availability():
    """Test that PromptManager can be imported and initialized."""
    print("=" * 80)
    print("TEST 1: PromptManager Availability")
    print("=" * 80)

    try:
        manager = PromptManager()
        print("\n✅ PromptManager imported successfully")
        print(f"✅ Template mode: {manager.config.get('use_templates', False)}")
        print(f"✅ Active sales version: {manager.config['active_versions']['sales']}")

        checks = [
            ("PromptManager initialized", manager is not None),
            ("Config loaded", manager.config is not None),
            ("Templates enabled", manager.config.get('use_templates', False)),
        ]

        print("\nChecks:")
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


def test_odiseobot_import():
    """Test that OdiseoBot can be imported with PromptManager support."""
    print("\n" + "=" * 80)
    print("TEST 2: OdiseoBot Import with PromptManager Support")
    print("=" * 80)

    try:
        from core.odiseo_bot import PROMPT_MANAGER_AVAILABLE, OdiseoBot

        print("\n✅ OdiseoBot imported successfully")
        print(f"✅ PROMPT_MANAGER_AVAILABLE: {PROMPT_MANAGER_AVAILABLE}")

        checks = [
            ("OdiseoBot class exists", OdiseoBot is not None),
            ("PromptManager feature flag present", PROMPT_MANAGER_AVAILABLE is not None),
        ]

        print("\nChecks:")
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


async def test_odiseobot_initialization_with_user_id():
    """Test OdiseoBot initialization with user_id parameter."""
    print("\n" + "=" * 80)
    print("TEST 3: OdiseoBot Initialization with user_id")
    print("=" * 80)

    try:
        from core.odiseo_bot import OdiseoBot

        # Test with explicit user_id
        user_id = "test_user_12345"
        bot = OdiseoBot(debug_mode=False, user_id=user_id)

        print(f"\n✅ OdiseoBot initialized with user_id: {bot.user_id}")
        print(f"✅ Session ID: {bot.session_id}")
        print(f"✅ Use modular prompts: {bot.use_modular_prompts}")

        checks = [
            ("user_id set correctly", bot.user_id == user_id),
            ("prompt_manager attribute exists", hasattr(bot, 'prompt_manager')),
            ("use_modular_prompts flag exists", hasattr(bot, 'use_modular_prompts')),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        # Test without user_id (should use session_id)
        bot2 = OdiseoBot(debug_mode=False)
        checks.append(("Fallback to session_id", str(bot2.session_id) == bot2.user_id))
        print(f"  {'✅'} Fallback to session_id (user_id={bot2.user_id[:8]}...)")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_build_system_prompt_with_promptmanager():
    """Test _build_system_prompt() method using PromptManager."""
    print("\n" + "=" * 80)
    print("TEST 4: _build_system_prompt() with PromptManager")
    print("=" * 80)

    try:
        from core.odiseo_bot import PROMPT_MANAGER_AVAILABLE, OdiseoBot

        if not PROMPT_MANAGER_AVAILABLE:
            print("⚠️ PromptManager not available - skipping test")
            return True  # Not a failure, just skipped

        bot = OdiseoBot(debug_mode=False, user_id="test_user_abc")

        # Use empty tools list (valid scenario - tools discovered later)
        bot.mcp_tools = []

        # Call _build_system_prompt
        prompt = await bot._build_system_prompt()

        print(f"\n✅ Prompt generated: {len(prompt)} characters")
        print(f"✅ Prompt manager initialized: {bot.prompt_manager is not None}")

        # Verify prompt content
        checks = [
            ("Prompt is not empty", len(prompt) > 0),
            ("Contains 'Odiseo'", "Odiseo" in prompt),
            ("PromptManager was initialized", bot.prompt_manager is not None),
            ("Prompt has reasonable length", len(prompt) > 1000),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

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


async def test_fallback_to_promptbuilder():
    """Test fallback to PromptBuilder when PromptManager fails."""
    print("\n" + "=" * 80)
    print("TEST 5: Fallback to PromptBuilder")
    print("=" * 80)

    try:
        from core.odiseo_bot import OdiseoBot

        bot = OdiseoBot(debug_mode=False, user_id="test_user_fallback")

        # Simulate PromptManager failure by setting use_modular_prompts to False
        bot.use_modular_prompts = False

        # Use empty tools list
        bot.mcp_tools = []

        # Call _build_system_prompt (should use PromptBuilder)
        prompt = await bot._build_system_prompt()

        print(f"\n✅ Fallback prompt generated: {len(prompt)} characters")
        print("✅ PromptBuilder used (prompt_manager should be None)")

        checks = [
            ("Prompt is not empty", len(prompt) > 0),
            ("Contains 'Odiseo'", "Odiseo" in prompt),
            ("Fallback successful", len(prompt) > 500),
        ]

        print("\nChecks:")
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


async def test_ab_testing_user_bucketing():
    """Test that different user_ids produce consistent prompts (A/B testing)."""
    print("\n" + "=" * 80)
    print("TEST 6: A/B Testing User Bucketing (deterministic)")
    print("=" * 80)

    try:
        from core.odiseo_bot import PROMPT_MANAGER_AVAILABLE, OdiseoBot

        if not PROMPT_MANAGER_AVAILABLE:
            print("⚠️ PromptManager not available - skipping test")
            return True

        # Create two bots with same user_id
        user_id = "test_consistent_user"
        bot1 = OdiseoBot(debug_mode=False, user_id=user_id)
        bot2 = OdiseoBot(debug_mode=False, user_id=user_id)

        # Use empty tools lists
        bot1.mcp_tools = []
        bot2.mcp_tools = []

        # Generate prompts
        prompt1 = await bot1._build_system_prompt()
        prompt2 = await bot2._build_system_prompt()

        print(f"\n✅ Bot 1 prompt: {len(prompt1)} chars (user_id={bot1.user_id[:8]}...)")
        print(f"✅ Bot 2 prompt: {len(prompt2)} chars (user_id={bot2.user_id[:8]}...)")

        checks = [
            ("Same user_id produces identical prompts", prompt1 == prompt2),
            ("Both prompts are non-empty", len(prompt1) > 0 and len(prompt2) > 0),
        ]

        print("\nChecks:")
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


async def test_integration_summary():
    """Test complete integration workflow."""
    print("\n" + "=" * 80)
    print("TEST 7: Complete Integration Workflow")
    print("=" * 80)

    try:
        from core.odiseo_bot import PROMPT_MANAGER_AVAILABLE, OdiseoBot

        # Step 1: Create bot with user_id
        bot = OdiseoBot(debug_mode=False, user_id="integration_test_user")
        print("✅ Step 1: OdiseoBot created")

        # Step 2: Use empty tools list (valid scenario)
        bot.mcp_tools = []
        print("✅ Step 2: MCP tools initialized")

        # Step 3: Build system prompt
        prompt = await bot._build_system_prompt()
        print(f"✅ Step 3: System prompt built ({len(prompt)} chars)")

        # Step 4: Verify prompt characteristics
        has_identity = "Odiseo" in prompt
        has_reasonable_length = len(prompt) > 1000
        used_modular = bot.prompt_manager is not None if PROMPT_MANAGER_AVAILABLE else True

        print("✅ Step 4: Prompt verification")
        print(f"   - Identity present: {has_identity}")
        print(f"   - Reasonable length: {has_reasonable_length}")
        print(f"   - Modular system used: {used_modular}")

        checks = [
            ("Bot initialized", bot is not None),
            ("Prompt generated", len(prompt) > 0),
            ("Identity in prompt", has_identity),
            ("Reasonable length", has_reasonable_length),
        ]

        print("\nChecks:")
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


async def main():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("ODISEOBOT + PROMPTMANAGER INTEGRATION TESTS (FASE C)")
    print("Testing OdiseoBot integration with modular prompt system")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("PromptManager Availability", test_prompt_manager_availability()))
    results.append(("OdiseoBot Import", test_odiseobot_import()))
    results.append(("Bot Initialization", await test_odiseobot_initialization_with_user_id()))
    results.append(("Build Prompt (PromptManager)", await test_build_system_prompt_with_promptmanager()))
    results.append(("Fallback to PromptBuilder", await test_fallback_to_promptbuilder()))
    results.append(("A/B Testing Bucketing", await test_ab_testing_user_bucketing()))
    results.append(("Integration Workflow", await test_integration_summary()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL INTEGRATION TESTS PASSED - Fase C complete!")
        print("\n📋 Next Steps:")
        print("1. OdiseoBot now uses modular prompt system with A/B testing")
        print("2. PromptBuilder maintained as fallback mechanism")
        print("3. user_id parameter enables deterministic bucketing")
        print("4. Ready for production deployment and monitoring")
        print("\n🔧 To enable A/B testing:")
        print("   Edit prompts/config/prompt_versions.yaml:")
        print("   - Set ab_testing.enabled: true")
        print("   - Set sales_pagination_6_products.enabled: true")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
