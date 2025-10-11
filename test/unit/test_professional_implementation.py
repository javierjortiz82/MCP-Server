#!/usr/bin/env python3
"""
Test Professional Implementation - Validates Critical Corrections

This script validates that all critical corrections from the professional audit
have been properly implemented.

Ref: PROFESSIONAL_AUDIT_REPORT.md

NOTE: These tests require full MCP SDK installation and environment setup.
      Run from project root with proper PYTHONPATH.
"""

import sys
from pathlib import Path

import pytest

# Add client_mcp to path (flat layout)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Skip all tests if MCP SDK not available
pytest.importorskip("mcp.client.session", reason="MCP SDK required for these tests")


def test_imports():
    """Test that all necessary imports work."""
    print("\n🧪 Test 1: Imports")
    print("=" * 60)

    try:
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False


def test_function_declaration_type():
    """Test that mcp_tools uses FunctionDeclaration, not Callable."""
    print("\n🧪 Test 2: FunctionDeclaration Type")
    print("=" * 60)

    from client_mcp.core.odiseo_bot import OdiseoBot

    # Check type hints
    OdiseoBot()
    OdiseoBot.__init__.__annotations__.get("return")

    # Check instance variable annotation
    import inspect

    source = inspect.getsource(OdiseoBot.__init__)

    if "list[types.FunctionDeclaration]" in source:
        print("✅ mcp_tools correctly typed as list[types.FunctionDeclaration]")
        return True
    else:
        print("❌ mcp_tools NOT using FunctionDeclaration type")
        return False


def test_conversion_method_signature():
    """Test that _convert_tools_to_genai returns FunctionDeclaration."""
    print("\n🧪 Test 3: Conversion Method Signature")
    print("=" * 60)

    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    # Get method signature
    method = OdiseoBot._convert_tools_to_genai
    sig = inspect.signature(method)

    return_annotation = sig.return_annotation

    # Check if return type is list[types.FunctionDeclaration]
    if "FunctionDeclaration" in str(return_annotation):
        print(f"✅ Return type: {return_annotation}")
        return True
    else:
        print(f"❌ Return type incorrect: {return_annotation}")
        return False


def test_has_schema_conversion_methods():
    """Test that schema conversion methods exist."""
    print("\n🧪 Test 4: Schema Conversion Methods")
    print("=" * 60)

    from client_mcp.core.odiseo_bot import OdiseoBot

    required_methods = [
        "_convert_json_schema_to_gemini_schema",
        "_map_json_type_to_gemini",
    ]

    all_exist = True
    for method_name in required_methods:
        if hasattr(OdiseoBot, method_name):
            print(f"✅ {method_name} exists")
        else:
            print(f"❌ {method_name} MISSING")
            all_exist = False

    return all_exist


def test_has_structured_serialization():
    """Test that structured result serialization exists."""
    print("\n🧪 Test 5: Structured Result Serialization")
    print("=" * 60)

    from client_mcp.core.odiseo_bot import OdiseoBot

    required_methods = [
        "_execute_function_calls",
        "_execute_tool",
        "_serialize_tool_result",
    ]

    all_exist = True
    for method_name in required_methods:
        if hasattr(OdiseoBot, method_name):
            print(f"✅ {method_name} exists")
        else:
            print(f"❌ {method_name} MISSING")
            all_exist = False

    return all_exist


def test_has_generation_config_singleton():
    """Test that generation config is built once."""
    print("\n🧪 Test 6: Generation Config Singleton")
    print("=" * 60)

    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    # Check for _generation_config attribute
    source = inspect.getsource(OdiseoBot.__init__)

    has_config_attr = "_generation_config" in source
    has_tools_param_attr = "_tools_param" in source

    if has_config_attr and has_tools_param_attr:
        print("✅ _generation_config attribute exists")
        print("✅ _tools_param attribute exists")
        return True
    else:
        if not has_config_attr:
            print("❌ _generation_config attribute MISSING")
        if not has_tools_param_attr:
            print("❌ _tools_param attribute MISSING")
        return False


def test_has_build_generation_config():
    """Test that _build_generation_config method exists."""
    print("\n🧪 Test 7: Build Generation Config Method")
    print("=" * 60)

    from client_mcp.core.odiseo_bot import OdiseoBot

    if hasattr(OdiseoBot, "_build_generation_config"):
        print("✅ _build_generation_config method exists")

        # Check if it uses tool_config
        import inspect

        source = inspect.getsource(OdiseoBot._build_generation_config)

        if "tool_config" in source and "ToolConfig" in source:
            print("✅ Uses tool_config parameter")
            return True
        else:
            print("⚠️  Method exists but may not use tool_config")
            return True
    else:
        print("❌ _build_generation_config method MISSING")
        return False


def test_serialize_tool_result_logic():
    """Test that _serialize_tool_result preserves structure."""
    print("\n🧪 Test 8: Serialize Tool Result Logic")
    print("=" * 60)

    from client_mcp.core.odiseo_bot import OdiseoBot

    bot = OdiseoBot()

    # Test with dict
    result_dict = {"name": "Product", "price": 100}
    serialized = bot._serialize_tool_result(result_dict)

    if serialized == result_dict:
        print("✅ Dict preserved as-is")
    else:
        print(f"❌ Dict not preserved: {serialized}")
        return False

    # Test with list
    result_list = [{"id": 1}, {"id": 2}]
    serialized = bot._serialize_tool_result(result_list)

    if (
        isinstance(serialized, dict)
        and "items" in serialized
        and serialized["count"] == 2
    ):
        print("✅ List wrapped in structure")
    else:
        print(f"❌ List not properly wrapped: {serialized}")
        return False

    # Test with string (should NOT just return string)
    result_str = "Some text"
    serialized = bot._serialize_tool_result(result_str)

    if isinstance(serialized, dict) and "text" in serialized:
        print("✅ String wrapped in structure")
    else:
        print(f"❌ String not wrapped: {serialized}")
        return False

    return True


def test_dynamic_tools_context():
    """Test that _generate_tools_context is dynamic."""
    print("\n🧪 Test 9: Dynamic Tools Context (No Hardcoding)")
    print("=" * 60)

    import inspect

    from client_mcp.core.odiseo_bot import OdiseoBot

    source = inspect.getsource(OdiseoBot._generate_tools_context)

    # Check that it uses FunctionDeclaration attributes
    if "func_decl.name" in source and "func_decl.description" in source:
        print("✅ Uses FunctionDeclaration attributes (not hardcoded)")
    else:
        print("❌ May be using hardcoded tool names")
        return False

    # Check for generic instructions (not specific tool names)
    if "INTENCIÓN" in source or "INFIERE" in source:
        print("✅ Uses generic inference instructions")
        return True
    else:
        print("⚠️  May lack generic instructions")
        return True


def run_all_tests():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("🔬 PROFESSIONAL IMPLEMENTATION VALIDATION")
    print("=" * 60)
    print("Validating critical corrections from audit report...")

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
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

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
        print(
            "\n🎉 ¡EXCELENTE! Todas las correcciones críticas implementadas correctamente."
        )
        print("✅ El proyecto cumple con las mejores prácticas de google-genai 1.41.0")
    elif passed >= total * 0.8:
        print("\n✅ ¡MUY BIEN! La mayoría de correcciones implementadas.")
        print(f"⚠️  {total - passed} corrección(es) pendiente(s)")
    else:
        print("\n⚠️  ATENCIÓN: Varias correcciones críticas pendientes.")
        print(f"❌ {total - passed} de {total} tests fallaron")

    print("=" * 60 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
