#!/usr/bin/env python3
"""
Test Full Integration - Simula flujo completo con datos reales
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google.genai import types


def test_mcp_tools_conversion():
    """Test converting MCP tools to FunctionDeclaration."""
    print("\n" + "=" * 60)
    print("🔄 TEST: MCP Tools → FunctionDeclaration Conversion")
    print("=" * 60)

    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        # Simulate MCP tools response
        mock_mcp_tools = [
            {
                "name": "search_products",
                "description": "Search for products in the database using a query string",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query string",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                        },
                        "category": {
                            "type": "string",
                            "description": "Filter by category",
                            "enum": ["laptops", "phones", "tablets"],
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_product_details",
                "description": "Get detailed information about a specific product",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Unique product identifier",
                        }
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "check_inventory",
                "description": "Check current inventory status for a product",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "product_id": {
                            "type": "string",
                            "description": "Product ID to check",
                        },
                        "location": {"type": "string", "description": "Store location"},
                    },
                    "required": ["product_id"],
                },
            },
        ]

        bot = OdiseoBot()

        print(f"\n📦 Converting {len(mock_mcp_tools)} MCP tools...")

        # Convert using bot's method
        function_declarations = bot._convert_tools_to_genai(mock_mcp_tools)

        print(f"✅ Converted to {len(function_declarations)} FunctionDeclarations")

        # Validate each conversion
        for i, (mcp_tool, func_decl) in enumerate(
            zip(mock_mcp_tools, function_declarations), 1
        ):
            print(f"\n🔍 Tool {i}: {func_decl.name}")

            # Check name
            if func_decl.name == mcp_tool["name"]:
                print(f"  ✅ Name: {func_decl.name}")
            else:
                print(f"  ❌ Name mismatch: {func_decl.name} != {mcp_tool['name']}")
                return False

            # Check description
            if func_decl.description == mcp_tool["description"]:
                print(f"  ✅ Description: {func_decl.description[:50]}...")
            else:
                print("  ❌ Description mismatch")
                return False

            # Check parameters
            if func_decl.parameters:
                print(
                    f"  ✅ Parameters: {len(func_decl.parameters.properties)} properties"
                )

                # Check type
                if func_decl.parameters.type == types.Type.OBJECT:
                    print("  ✅ Parameters type: OBJECT")
                else:
                    print(
                        f"  ❌ Parameters type incorrect: {func_decl.parameters.type}"
                    )
                    return False

                # Check required fields
                mcp_required = mcp_tool["inputSchema"].get("required", [])
                if func_decl.parameters.required == mcp_required:
                    print(f"  ✅ Required fields: {func_decl.parameters.required}")
                else:
                    print("  ❌ Required fields mismatch")
                    return False

                # Check properties
                for prop_name, prop_schema in func_decl.parameters.properties.items():
                    print(f"    • {prop_name}: {prop_schema.type}")

                    # Validate enum if present
                    mcp_prop = mcp_tool["inputSchema"]["properties"][prop_name]
                    if "enum" in mcp_prop:
                        if prop_schema.enum == mcp_prop["enum"]:
                            print(f"      ✅ Enum: {prop_schema.enum}")
                        else:
                            print("      ❌ Enum mismatch")
                            return False

            else:
                print("  ❌ Parameters missing")
                return False

        print("\n✅ All MCP tools converted correctly to FunctionDeclaration")
        return True

    except Exception as e:
        print(f"\n❌ Error in conversion: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_serialization_real_data():
    """Test serialization with realistic data."""
    print("\n" + "=" * 60)
    print("📦 TEST: Serialization with Real Data")
    print("=" * 60)

    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        bot = OdiseoBot()

        # Test case 1: Dict with nested structure
        print("\n🧪 Test 1: Nested Dict")
        product_data = {
            "id": "LAPTOP001",
            "name": "Gaming Laptop Pro",
            "price": 1299.99,
            "specs": {"cpu": "Intel i7", "ram": "16GB", "storage": "512GB SSD"},
            "in_stock": True,
            "tags": ["gaming", "high-performance"],
        }

        serialized = bot._serialize_tool_result(product_data)

        if serialized == product_data:
            print("  ✅ Dict preserved with all nested structure")
            print(f"     Keys: {list(serialized.keys())}")
        else:
            print("  ❌ Dict not preserved correctly")
            return False

        # Test case 2: List of products
        print("\n🧪 Test 2: List of Products")
        products_list = [
            {"id": "LAPTOP001", "name": "Gaming Laptop", "price": 1299.99},
            {"id": "LAPTOP002", "name": "Business Laptop", "price": 899.99},
            {"id": "LAPTOP003", "name": "Budget Laptop", "price": 499.99},
        ]

        serialized = bot._serialize_tool_result(products_list)

        if (
            isinstance(serialized, dict)
            and "items" in serialized
            and serialized["items"] == products_list
            and serialized["count"] == 3
        ):
            print("  ✅ List wrapped correctly")
            print(f"     Count: {serialized['count']}")
            print(f"     First item: {serialized['items'][0]['name']}")
        else:
            print("  ❌ List not wrapped correctly")
            return False

        # Test case 3: JSON string that should be parsed
        print("\n🧪 Test 3: JSON String Parsing")
        json_string = (
            '{"status": "success", "message": "Product found", "data": {"id": 123}}'
        )

        serialized = bot._serialize_tool_result(json_string)

        if (
            isinstance(serialized, dict)
            and "status" in serialized
            and serialized["status"] == "success"
        ):
            print("  ✅ JSON string parsed to dict")
            print(f"     Keys: {list(serialized.keys())}")
        else:
            print("  ❌ JSON string not parsed correctly")
            return False

        # Test case 4: Plain text string
        print("\n🧪 Test 4: Plain Text String")
        text_string = "No products found matching your criteria"

        serialized = bot._serialize_tool_result(text_string)

        if (
            isinstance(serialized, dict)
            and "text" in serialized
            and serialized["text"] == text_string
        ):
            print("  ✅ Text string wrapped correctly")
            print(f"     Text: {serialized['text'][:50]}...")
        else:
            print("  ❌ Text string not wrapped correctly")
            return False

        # Test case 5: Number
        print("\n🧪 Test 5: Numeric Result")
        number_result = 42

        serialized = bot._serialize_tool_result(number_result)

        if (
            isinstance(serialized, dict)
            and "value" in serialized
            and serialized["value"] == number_result
        ):
            print("  ✅ Number wrapped correctly")
            print(f"     Value: {serialized['value']}")
        else:
            print("  ❌ Number not wrapped correctly")
            return False

        # Test case 6: Boolean
        print("\n🧪 Test 6: Boolean Result")
        bool_result = True

        serialized = bot._serialize_tool_result(bool_result)

        if (
            isinstance(serialized, dict)
            and "value" in serialized
            and serialized["value"] == bool_result
        ):
            print("  ✅ Boolean wrapped correctly")
            print(f"     Value: {serialized['value']}")
        else:
            print("  ❌ Boolean not wrapped correctly")
            return False

        # Test case 7: None
        print("\n🧪 Test 7: None Result")
        none_result = None

        serialized = bot._serialize_tool_result(none_result)

        if (
            isinstance(serialized, dict)
            and "status" in serialized
            and serialized["data"] is None
        ):
            print("  ✅ None wrapped correctly")
            print(f"     Result: {serialized}")
        else:
            print("  ❌ None not wrapped correctly")
            return False

        print("\n✅ All serialization tests passed with real data")
        return True

    except Exception as e:
        print(f"\n❌ Error in serialization: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tool_wrapping():
    """Test wrapping FunctionDeclarations in Tool."""
    print("\n" + "=" * 60)
    print("🎁 TEST: Tool Wrapping")
    print("=" * 60)

    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        # Create mock MCP tools
        mock_tools = [
            {
                "name": "tool1",
                "description": "First tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param1": {"type": "string"}},
                    "required": ["param1"],
                },
            },
            {
                "name": "tool2",
                "description": "Second tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param2": {"type": "integer"}},
                    "required": ["param2"],
                },
            },
        ]

        bot = OdiseoBot()
        function_declarations = bot._convert_tools_to_genai(mock_tools)

        # Wrap in Tool
        tools_param = [types.Tool(function_declarations=function_declarations)]

        print(f"✅ Created tools_param with {len(tools_param)} Tool")
        print(
            f"✅ Tool contains {len(tools_param[0].function_declarations)} FunctionDeclarations"
        )

        for i, func_decl in enumerate(tools_param[0].function_declarations, 1):
            print(f"  {i}. {func_decl.name}")

        return True

    except Exception as e:
        print(f"❌ Error in tool wrapping: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_generation_config_structure():
    """Test generation config structure."""
    print("\n" + "=" * 60)
    print("⚙️  TEST: Generation Config Structure")
    print("=" * 60)

    try:
        from client_mcp.config.settings import settings
        from client_mcp.core.odiseo_bot import OdiseoBot

        bot = OdiseoBot()

        # Simulate having tools
        mock_tools = [
            {
                "name": "test_tool",
                "description": "Test",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"],
                },
            }
        ]

        bot.mcp_tools = bot._convert_tools_to_genai(mock_tools)
        bot.system_prompt = "You are a helpful assistant"

        # Build config
        config = bot._build_generation_config()

        print("✅ GenerateContentConfig created:")
        print(f"   Temperature: {config.temperature}")
        print(f"   Top K: {config.top_k}")
        print(f"   Top P: {config.top_p}")
        print(f"   Max tokens: {config.max_output_tokens}")
        print(f"   Has system instruction: {config.system_instruction is not None}")
        print(f"   Has tool_config: {config.tool_config is not None}")

        if config.tool_config:
            print(
                f"   Function calling mode: {config.tool_config.function_calling_config.mode}"
            )
            print(
                f"   Allowed functions: {config.tool_config.function_calling_config.allowed_function_names}"
            )

        # Validate values
        if config.temperature == settings.TEMPERATURE:
            print("✅ Temperature matches settings")
        else:
            print("❌ Temperature mismatch")
            return False

        if (
            config.tool_config
            and config.tool_config.function_calling_config.mode
            == types.FunctionCallingConfigMode.AUTO
        ):
            print("✅ Tool config mode is AUTO")
        else:
            print("❌ Tool config mode incorrect")
            return False

        return True

    except Exception as e:
        print(f"❌ Error building config: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 FULL INTEGRATION TEST SUITE")
    print("=" * 60)
    print("Testing with realistic data and scenarios...")

    results = []

    # Test 1: MCP tools conversion
    results.append(("MCP Tools Conversion", test_mcp_tools_conversion()))

    # Test 2: Serialization with real data
    results.append(("Serialization Real Data", test_serialization_real_data()))

    # Test 3: Tool wrapping
    results.append(("Tool Wrapping", test_tool_wrapping()))

    # Test 4: Generation config
    results.append(("Generation Config", test_generation_config_structure()))

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
        print("\n🎉 ¡Integración completa validada!")
        print("✅ Conversión MCP → FunctionDeclaration funcional")
        print("✅ Serialización preserva estructura JSON")
        print("✅ Tool config con modo AUTO correcto")
    else:
        print(f"\n⚠️ {total - passed} test(s) fallaron")

    print("=" * 60 + "\n")

    sys.exit(0 if passed == total else 1)
