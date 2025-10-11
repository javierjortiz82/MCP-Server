#!/usr/bin/env python3
"""
Test Bot Initialization - Verifica inicialización completa del bot
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_bot_constructor():
    """Test bot constructor (sync)."""
    print("\n" + "=" * 60)
    print("🏗️ TEST: Bot Constructor")
    print("=" * 60)

    try:
        from client_mcp.config.settings import settings
        from client_mcp.core.odiseo_bot import OdiseoBot

        # Check API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("❌ GOOGLE_API_KEY not found in environment")
            return False

        print(f"✅ API Key found: {api_key[:10]}...")
        print(f"✅ Model: {settings.MODEL}")

        # Create bot instance
        print("\n📦 Creating OdiseoBot instance...")
        bot = OdiseoBot()

        # Check attributes after __init__
        print("\n🔍 Checking bot attributes (after __init__):")

        # Client should be None until initialize()
        if hasattr(bot, "client"):
            if bot.client is None:
                print("  ✅ client: None (as expected before initialize)")
            else:
                print(f"  ⚠️ client: {type(bot.client).__name__} (should be None)")
        else:
            print("  ❌ client attribute missing")
            return False

        # System prompt should be empty until initialize()
        if hasattr(bot, "system_prompt"):
            if bot.system_prompt == "":
                print("  ✅ system_prompt: empty (as expected before initialize)")
            else:
                print("  ⚠️ system_prompt: has content (should be empty)")
        else:
            print("  ❌ system_prompt attribute missing")
            return False

        # MCP tools should be empty list
        if hasattr(bot, "mcp_tools"):
            if isinstance(bot.mcp_tools, list) and len(bot.mcp_tools) == 0:
                print("  ✅ mcp_tools: empty list (as expected)")
            else:
                print(f"  ⚠️ mcp_tools: {len(bot.mcp_tools)} items")
        else:
            print("  ❌ mcp_tools attribute missing")
            return False

        # Conversation history should be empty list
        if hasattr(bot, "conversation_history"):
            if (
                isinstance(bot.conversation_history, list)
                and len(bot.conversation_history) == 0
            ):
                print("  ✅ conversation_history: empty list (as expected)")
            else:
                print(
                    f"  ⚠️ conversation_history: {len(bot.conversation_history)} items"
                )
        else:
            print("  ❌ conversation_history attribute missing")
            return False

        # Generation config should be None until initialize()
        if hasattr(bot, "_generation_config"):
            if bot._generation_config is None:
                print("  ✅ _generation_config: None (as expected)")
            else:
                print(f"  ⚠️ _generation_config: {type(bot._generation_config)}")
        else:
            print("  ❌ _generation_config attribute missing")
            return False

        # Tools param should be None until initialize()
        if hasattr(bot, "_tools_param"):
            if bot._tools_param is None:
                print("  ✅ _tools_param: None (as expected)")
            else:
                print(f"  ⚠️ _tools_param: {type(bot._tools_param)}")
        else:
            print("  ❌ _tools_param attribute missing")
            return False

        print("\n✅ Bot constructor working correctly!")
        return True

    except Exception as e:
        print(f"\n❌ Error during constructor: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_method_existence():
    """Test that all critical methods exist."""
    print("\n" + "=" * 60)
    print("🔧 TEST: Method Existence")
    print("=" * 60)

    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        required_methods = [
            "_convert_tools_to_genai",
            "_convert_json_schema_to_gemini_schema",
            "_map_json_type_to_gemini",
            "_serialize_tool_result",
            "_build_generation_config",
            "_generate_tools_context",
            "_execute_function_calls",
            "_execute_tool",
        ]

        all_exist = True
        for method_name in required_methods:
            if hasattr(OdiseoBot, method_name):
                print(f"  ✅ {method_name}")
            else:
                print(f"  ❌ {method_name} MISSING")
                all_exist = False

        if all_exist:
            print("\n✅ All critical methods exist!")

        return all_exist

    except Exception as e:
        print(f"\n❌ Error checking methods: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 BOT INITIALIZATION TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: Method existence
    results.append(("Method Existence", test_method_existence()))

    # Test 2: Bot constructor
    results.append(("Bot Constructor", test_bot_constructor()))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "=" * 60)
    print(f"📈 Score: {passed}/{total} ({passed / total * 100:.1f}%)")

    if passed == total:
        print("\n🎉 ¡Bot constructor funciona correctamente con google-genai 1.41.0!")
        print("✅ Todos los atributos críticos inicializados correctamente")
    else:
        print(f"\n⚠️ {total - passed} test(s) fallaron")

    print("=" * 60 + "\n")

    sys.exit(0 if passed == total else 1)
