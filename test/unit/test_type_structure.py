#!/usr/bin/env python3
"""
DEPRECATED: Legacy OdiseoBot Type Structure Tests

⚠️  WARNING: This test file tests Legacy OdiseoBot internal implementation.

Status: DEPRECATED as of 2025-10-12
Replacement: agent/test_odiseo_bot_v2_integration.py
Removal: Scheduled for Week 6-8 of Legacy elimination plan

These tests verify Legacy OdiseoBot type structures and method signatures.
OdiseoBotV2 delegates type handling to BaseAgent and these internal
type conversions do not exist in V2.

For V2 testing, see:
  - agent/test_odiseo_bot_v2_integration.py (8 integration tests)
  - agent/test_odiseo_bot_v2.py (unit tests)

See: agent/docs/TEST_MIGRATION_ANALYSIS.md for migration decision details.
"""

import sys
from pathlib import Path
import warnings

warnings.warn(
    "test_type_structure.py tests deprecated Legacy OdiseoBot. "
    "Use agent/test_odiseo_bot_v2_integration.py instead. "
    "This file will be removed in Week 6-8 of Legacy elimination.",
    DeprecationWarning,
    stacklevel=2
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google.genai import types


def test_function_declaration_creation():
    """Test creating FunctionDeclaration with proper schema."""
    print("\n" + "=" * 60)
    print("🔧 TEST: FunctionDeclaration Creation")
    print("=" * 60)

    try:
        # Create a sample schema
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(
                    type=types.Type.STRING, description="The search query"
                ),
                "limit": types.Schema(
                    type=types.Type.INTEGER, description="Maximum number of results"
                ),
            },
            required=["query"],
        )

        # Create FunctionDeclaration
        func_decl = types.FunctionDeclaration(
            name="search_products",
            description="Search for products in the database",
            parameters=schema,
        )

        print("✅ FunctionDeclaration created:")
        print(f"   Name: {func_decl.name}")
        print(f"   Description: {func_decl.description}")
        print(f"   Parameters type: {type(func_decl.parameters).__name__}")
        print(f"   Has properties: {func_decl.parameters.properties is not None}")
        print(f"   Required fields: {func_decl.parameters.required}")

        return True

    except Exception as e:
        print(f"❌ Error creating FunctionDeclaration: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_wrapping():
    """Test wrapping FunctionDeclaration in Tool."""
    print("\n" + "=" * 60)
    print("🔧 TEST: Tool Wrapping")
    print("=" * 60)

    try:
        # Create a FunctionDeclaration
        func_decl = types.FunctionDeclaration(
            name="get_price",
            description="Get product price",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "product_id": types.Schema(
                        type=types.Type.STRING, description="Product ID"
                    )
                },
            ),
        )

        # Wrap in Tool
        tool = types.Tool(function_declarations=[func_decl])

        print("✅ Tool created:")
        print(f"   Function declarations count: {len(tool.function_declarations)}")
        print(f"   First function: {tool.function_declarations[0].name}")

        return True

    except Exception as e:
        print(f"❌ Error creating Tool: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_generation_config_with_tool_config():
    """Test GenerateContentConfig with tool_config."""
    print("\n" + "=" * 60)
    print("🔧 TEST: GenerationConfig with ToolConfig")
    print("=" * 60)

    try:
        # Create ToolConfig
        tool_config = types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO,  # ✅ Correct enum
                allowed_function_names=None,
            )
        )

        # Create GenerateContentConfig
        config = types.GenerateContentConfig(
            temperature=0.2,
            top_k=40,
            top_p=0.95,
            max_output_tokens=512,
            system_instruction="You are a helpful assistant",
            tool_config=tool_config,
        )

        print("✅ GenerateContentConfig created:")
        print(f"   Temperature: {config.temperature}")
        print(f"   Has tool_config: {config.tool_config is not None}")
        print(
            f"   Function calling mode: {config.tool_config.function_calling_config.mode}"
        )

        return True

    except Exception as e:
        print(f"❌ Error creating GenerateContentConfig: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_content_structure():
    """Test Content and Part structures."""
    print("\n" + "=" * 60)
    print("🔧 TEST: Content Structure")
    print("=" * 60)

    try:
        # Create user content
        user_content = types.Content(
            role="user", parts=[types.Part(text="Hello, how can you help?")]
        )

        print("✅ User Content created:")
        print(f"   Role: {user_content.role}")
        print(f"   Parts count: {len(user_content.parts)}")
        print(f"   First part has text: {user_content.parts[0].text is not None}")

        # Create function response
        func_response = types.Part(
            function_response=types.FunctionResponse(
                name="search_products",
                response={"items": [{"id": 1, "name": "Laptop"}], "count": 1},
            )
        )

        print("✅ Function Response created:")
        print(f"   Function name: {func_response.function_response.name}")
        print(f"   Response type: {type(func_response.function_response.response)}")

        return True

    except Exception as e:
        print(f"❌ Error creating Content structures: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_bot_method_types():
    """Test that bot methods return correct types."""
    print("\n" + "=" * 60)
    print("🔧 TEST: Bot Method Return Types")
    print("=" * 60)

    try:
        import inspect

        from client_mcp.core.odiseo_bot import OdiseoBot

        OdiseoBot()

        # Check _convert_tools_to_genai return type
        method = OdiseoBot._convert_tools_to_genai
        sig = inspect.signature(method)
        return_annotation = sig.return_annotation

        if "FunctionDeclaration" in str(return_annotation):
            print(f"✅ _convert_tools_to_genai returns: {return_annotation}")
        else:
            print(f"❌ Wrong return type: {return_annotation}")
            return False

        # Check _convert_json_schema_to_gemini_schema return type
        method = OdiseoBot._convert_json_schema_to_gemini_schema
        sig = inspect.signature(method)
        return_annotation = sig.return_annotation

        if "Schema" in str(return_annotation):
            print(
                f"✅ _convert_json_schema_to_gemini_schema returns: {return_annotation}"
            )
        else:
            print(f"❌ Wrong return type: {return_annotation}")
            return False

        # Check _build_generation_config return type
        method = OdiseoBot._build_generation_config
        sig = inspect.signature(method)
        return_annotation = sig.return_annotation

        if "GenerateContentConfig" in str(return_annotation):
            print(f"✅ _build_generation_config returns: {return_annotation}")
        else:
            print(f"❌ Wrong return type: {return_annotation}")
            return False

        return True

    except Exception as e:
        print(f"❌ Error checking method types: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 TYPE STRUCTURE TEST SUITE")
    print("=" * 60)

    results = []

    # Test 1: FunctionDeclaration creation
    results.append(
        ("FunctionDeclaration Creation", test_function_declaration_creation())
    )

    # Test 2: Tool wrapping
    results.append(("Tool Wrapping", test_tool_wrapping()))

    # Test 3: GenerationConfig with ToolConfig
    results.append(
        ("GenerationConfig + ToolConfig", test_generation_config_with_tool_config())
    )

    # Test 4: Content structure
    results.append(("Content Structure", test_content_structure()))

    # Test 5: Bot method types
    results.append(("Bot Method Return Types", test_bot_method_types()))

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
        print("\n🎉 ¡Todos los tipos correctos según google-genai 1.41.0!")
        print("✅ FunctionDeclaration, Schema, ToolConfig implementados correctamente")
    else:
        print(f"\n⚠️ {total - passed} test(s) fallaron")

    print("=" * 60 + "\n")

    sys.exit(0 if passed == total else 1)
