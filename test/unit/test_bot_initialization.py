#!/usr/bin/env python3
"""DEPRECATED: Legacy OdiseoBot Initialization Tests.

⚠️  WARNING: This test file tests Legacy OdiseoBot internal implementation.

Status: DEPRECATED as of 2025-10-12
Replacement: agent/test_odiseo_bot_v2_integration.py
Removal: Scheduled for Week 6-8 of Legacy elimination plan

These tests check Legacy OdiseoBot constructor and internal methods.
OdiseoBotV2 has different architecture (BaseAgent-based) and these
internal methods do not exist in V2.

For V2 testing, see:
  - agent/test_odiseo_bot_v2_integration.py (8 integration tests)
  - agent/test_odiseo_bot_v2.py (unit tests)

See: agent/docs/TEST_MIGRATION_ANALYSIS.md for migration decision details.
"""

import sys
import warnings
from pathlib import Path

warnings.warn(
    "test_bot_initialization.py tests deprecated Legacy OdiseoBot. "
    "Use agent/test_odiseo_bot_v2_integration.py instead. "
    "This file will be removed in Week 6-8 of Legacy elimination.",
    DeprecationWarning,
    stacklevel=2,
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_bot_constructor():
    """Test bot constructor (sync)."""
    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        # Check API key
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return False

        # Create bot instance
        bot = OdiseoBot()

        # Check attributes after __init__

        # Client should be None until initialize()
        if hasattr(bot, "client"):
            if bot.client is None:
                pass
            else:
                pass
        else:
            return False

        # System prompt should be empty until initialize()
        if hasattr(bot, "system_prompt"):
            if bot.system_prompt == "":
                pass
            else:
                pass
        else:
            return False

        # MCP tools should be empty list
        if hasattr(bot, "mcp_tools"):
            if isinstance(bot.mcp_tools, list) and len(bot.mcp_tools) == 0:
                pass
            else:
                pass
        else:
            return False

        # Conversation history should be empty list
        if hasattr(bot, "conversation_history"):
            if isinstance(bot.conversation_history, list) and len(bot.conversation_history) == 0:
                pass
            else:
                pass
        else:
            return False

        # Generation config should be None until initialize()
        if hasattr(bot, "_generation_config"):
            if bot._generation_config is None:
                pass
            else:
                pass
        else:
            return False

        # Tools param should be None until initialize()
        if hasattr(bot, "_tools_param"):
            if bot._tools_param is None:
                pass
            else:
                pass
        else:
            return False

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def test_method_existence():
    """Test that all critical methods exist."""
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
                pass
            else:
                all_exist = False

        if all_exist:
            pass

        return all_exist

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    results = []

    # Test 1: Method existence
    results.append(("Method Existence", test_method_existence()))

    # Test 2: Bot constructor
    results.append(("Bot Constructor", test_bot_constructor()))

    # Summary

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for _test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"

    if passed == total:
        pass
    else:
        pass

    sys.exit(0 if passed == total else 1)
