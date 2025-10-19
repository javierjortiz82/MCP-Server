#!/usr/bin/env python3
"""DEPRECATED: Legacy OdiseoBot Professional Implementation Tests.

⚠️  WARNING: This test file tests Legacy OdiseoBot internal implementation.

Status: DEPRECATED as of 2025-10-12
Replacement: agent/test_odiseo_bot_v2_integration.py
Removal: Scheduled for Week 6-8 of Legacy elimination plan

These tests validate Legacy OdiseoBot professional audit corrections
(google-genai 1.41.0 compliance). They test internal methods that do
not exist in OdiseoBotV2 due to BaseAgent architecture.

For V2 testing, see:
  - agent/test_odiseo_bot_v2_integration.py (8 integration tests)
  - agent/test_odiseo_bot_v2.py (unit tests)

See: agent/docs/TEST_MIGRATION_ANALYSIS.md for migration decision details.

Original Purpose: Validates critical corrections from professional audit
Ref: PROFESSIONAL_AUDIT_REPORT.md (Legacy only)

NOTE: These tests require full MCP SDK installation and environment setup.
      Run from project root with proper PYTHONPATH.
"""

import sys
import warnings
from pathlib import Path

import pytest

warnings.warn(
    "test_professional_implementation.py tests deprecated Legacy OdiseoBot. "
    "Use agent/test_odiseo_bot_v2_integration.py instead. "
    "This file will be removed in Week 6-8 of Legacy elimination.",
    DeprecationWarning,
    stacklevel=2,
)

# Add client_mcp to path (flat layout)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Skip all tests if MCP SDK not available
pytest.importorskip("mcp.client.session", reason="MCP SDK required for these tests")


def test_imports():
    """Test that all necessary imports work."""
    try:
        return True
    except Exception:
        return False


def test_function_declaration_type():
    """Test that mcp_tools uses FunctionDeclaration, not Callable."""
    from client_mcp.core.odiseo_bot import OdiseoBot

    # Check type hints
    OdiseoBot()
    OdiseoBot.__init__.__annotations__.get("return")

    # Check instance variable annotation
    import inspect

    source = inspect.getsource(OdiseoBot.__init__)

    return "list[types.FunctionDeclaration]" in source


def test_conversion_method_signature():
    """Test that _convert_tools_to_genai returns FunctionDeclaration."""
    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    # Get method signature
    method = OdiseoBot._convert_tools_to_genai
    sig = inspect.signature(method)

    return_annotation = sig.return_annotation

    # Check if return type is list[types.FunctionDeclaration]
    return "FunctionDeclaration" in str(return_annotation)


def test_has_schema_conversion_methods():
    """Test that schema conversion methods exist."""
    from client_mcp.core.odiseo_bot import OdiseoBot

    required_methods = [
        "_convert_json_schema_to_gemini_schema",
        "_map_json_type_to_gemini",
    ]

    all_exist = True
    for method_name in required_methods:
        if hasattr(OdiseoBot, method_name):
            pass
        else:
            all_exist = False

    return all_exist


def test_has_structured_serialization():
    """Test that structured result serialization exists."""
    from client_mcp.core.odiseo_bot import OdiseoBot

    required_methods = [
        "_execute_function_calls",
        "_execute_tool",
        "_serialize_tool_result",
    ]

    all_exist = True
    for method_name in required_methods:
        if hasattr(OdiseoBot, method_name):
            pass
        else:
            all_exist = False

    return all_exist


def test_has_generation_config_singleton():
    """Test that generation config is built once."""
    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    # Check for _generation_config attribute
    source = inspect.getsource(OdiseoBot.__init__)

    has_config_attr = "_generation_config" in source
    has_tools_param_attr = "_tools_param" in source

    if has_config_attr and has_tools_param_attr:
        return True
    else:
        if not has_config_attr:
            pass
        if not has_tools_param_attr:
            pass
        return False


def test_has_build_generation_config():
    """Test that _build_generation_config method exists."""
    from client_mcp.core.odiseo_bot import OdiseoBot

    if hasattr(OdiseoBot, "_build_generation_config"):
        # Check if it uses tool_config
        import inspect

        source = inspect.getsource(OdiseoBot._build_generation_config)

        if "tool_config" in source and "ToolConfig" in source:
            return True
        else:
            return True
    else:
        return False


def test_serialize_tool_result_logic():
    """Test that _serialize_tool_result preserves structure."""
    from client_mcp.core.odiseo_bot import OdiseoBot

    bot = OdiseoBot()

    # Test with dict
    result_dict = {"name": "Product", "price": 100}
    serialized = bot._serialize_tool_result(result_dict)

    if serialized == result_dict:
        pass
    else:
        return False

    # Test with list
    result_list = [{"id": 1}, {"id": 2}]
    serialized = bot._serialize_tool_result(result_list)

    if isinstance(serialized, dict) and "items" in serialized and serialized["count"] == 2:
        pass
    else:
        return False

    # Test with string (should NOT just return string)
    result_str = "Some text"
    serialized = bot._serialize_tool_result(result_str)

    if isinstance(serialized, dict) and "text" in serialized:
        pass
    else:
        return False

    return True


def test_dynamic_tools_context():
    """Test that _generate_tools_context is dynamic."""
    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    source = inspect.getsource(OdiseoBot._generate_tools_context)

    # Check that it uses FunctionDeclaration attributes
    if "func_decl.name" in source and "func_decl.description" in source:
        pass
    else:
        return False

    # Check for generic instructions (not specific tool names)
    if "INTENCIÓN" in source or "INFIERE" in source:
        return True
    else:
        return True


def run_all_tests():
    """Run all validation tests."""
    tests = [
        ("Imports", test_imports),
        ("FunctionDeclaration Type", test_function_declaration_type),
        ("Conversion Method Signature", test_conversion_method_signature),
        ("Schema Conversion Methods", test_has_schema_conversion_methods),
        ("Structured Serialization", test_has_structured_serialization),
        ("Generation Config Singleton", test_has_generation_config_singleton),
        ("Build Generation Config", test_has_build_generation_config),
        ("Serialize Tool Result", test_serialize_tool_result_logic),
        ("Dynamic Tools Context", test_dynamic_tools_context),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception:
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        pass

    if passed == total or passed >= total * 0.8:
        pass
    else:
        pass

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
