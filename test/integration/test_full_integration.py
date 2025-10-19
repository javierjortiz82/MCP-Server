#!/usr/bin/env python3
"""DEPRECATED: Legacy OdiseoBot Full Integration Tests.

⚠️  WARNING: This test file tests Legacy OdiseoBot internal implementation.

Status: DEPRECATED as of 2025-10-12
Replacement: agent/test_odiseo_bot_v2_integration.py
Removal: Scheduled for Week 6-8 of Legacy elimination plan

These tests simulate Legacy OdiseoBot integration with mock data.
They test internal conversion and serialization methods that do
not exist in OdiseoBotV2 (BaseAgent handles these internally).

For V2 testing, see:
  - agent/test_odiseo_bot_v2_integration.py (8 REAL integration tests)
  - agent/test_odiseo_bot_v2.py (unit tests)

V2 integration tests are SUPERIOR:
  - Use real MCP server (not mocks)
  - Test end-to-end functionality
  - Cover more features (caching, pagination, history)

See: agent/docs/TEST_MIGRATION_ANALYSIS.md for migration decision details.
"""

import sys
import warnings
from pathlib import Path

warnings.warn(
    "test_full_integration.py tests deprecated Legacy OdiseoBot. "
    "Use agent/test_odiseo_bot_v2_integration.py instead. "
    "This file will be removed in Week 6-8 of Legacy elimination.",
    DeprecationWarning,
    stacklevel=2,
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from google.genai import types


def test_mcp_tools_conversion():
    """Test converting MCP tools to FunctionDeclaration."""
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
                        },
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

        # Convert using bot's method
        function_declarations = bot._convert_tools_to_genai(mock_mcp_tools)

        # Validate each conversion
        for _i, (mcp_tool, func_decl) in enumerate(
            zip(mock_mcp_tools, function_declarations, strict=False),
            1,
        ):
            # Check name
            if func_decl.name == mcp_tool["name"]:
                pass
            else:
                return False

            # Check description
            if func_decl.description == mcp_tool["description"]:
                pass
            else:
                return False

            # Check parameters
            if func_decl.parameters:
                # Check type
                if func_decl.parameters.type == types.Type.OBJECT:
                    pass
                else:
                    return False

                # Check required fields
                mcp_required = mcp_tool["inputSchema"].get("required", [])
                if func_decl.parameters.required == mcp_required:
                    pass
                else:
                    return False

                # Check properties
                for prop_name, prop_schema in func_decl.parameters.properties.items():
                    # Validate enum if present
                    mcp_prop = mcp_tool["inputSchema"]["properties"][prop_name]
                    if "enum" in mcp_prop:
                        if prop_schema.enum == mcp_prop["enum"]:
                            pass
                        else:
                            return False

            else:
                return False

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def test_serialization_real_data():
    """Test serialization with realistic data."""
    try:
        from client_mcp.core.odiseo_bot import OdiseoBot

        bot = OdiseoBot()

        # Test case 1: Dict with nested structure
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
            pass
        else:
            return False

        # Test case 2: List of products
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
            pass
        else:
            return False

        # Test case 3: JSON string that should be parsed
        json_string = '{"status": "success", "message": "Product found", "data": {"id": 123}}'

        serialized = bot._serialize_tool_result(json_string)

        if (
            isinstance(serialized, dict)
            and "status" in serialized
            and serialized["status"] == "success"
        ):
            pass
        else:
            return False

        # Test case 4: Plain text string
        text_string = "No products found matching your criteria"

        serialized = bot._serialize_tool_result(text_string)

        if (
            isinstance(serialized, dict)
            and "text" in serialized
            and serialized["text"] == text_string
        ):
            pass
        else:
            return False

        # Test case 5: Number
        number_result = 42

        serialized = bot._serialize_tool_result(number_result)

        if (
            isinstance(serialized, dict)
            and "value" in serialized
            and serialized["value"] == number_result
        ):
            pass
        else:
            return False

        # Test case 6: Boolean
        bool_result = True

        serialized = bot._serialize_tool_result(bool_result)

        if (
            isinstance(serialized, dict)
            and "value" in serialized
            and serialized["value"] == bool_result
        ):
            pass
        else:
            return False

        # Test case 7: None
        none_result = None

        serialized = bot._serialize_tool_result(none_result)

        if isinstance(serialized, dict) and "status" in serialized and serialized["data"] is None:
            pass
        else:
            return False

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def test_tool_wrapping():
    """Test wrapping FunctionDeclarations in Tool."""
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

        for _i, _func_decl in enumerate(tools_param[0].function_declarations, 1):
            pass

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def test_generation_config_structure():
    """Test generation config structure."""
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
            },
        ]

        bot.mcp_tools = bot._convert_tools_to_genai(mock_tools)
        bot.system_prompt = "You are a helpful assistant"

        # Build config
        config = bot._build_generation_config()

        if config.tool_config:
            pass

        # Validate values
        if config.temperature == settings.TEMPERATURE:
            pass
        else:
            return False

        if (
            config.tool_config
            and config.tool_config.function_calling_config.mode
            == types.FunctionCallingConfigMode.AUTO
        ):
            pass
        else:
            return False

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
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

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for _test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"

    if passed == total:
        pass
    else:
        pass

    sys.exit(0 if passed == total else 1)
