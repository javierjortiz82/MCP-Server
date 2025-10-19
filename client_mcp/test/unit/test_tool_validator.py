"""Unit tests for ToolValidator."""

import pytest
from pydantic import ValidationError

from core.tool_validator import ToolValidator


class TestToolValidator:
    """Test suite for ToolValidator class."""

    def test_initialization(self):
        """Test ToolValidator initialization."""
        validator = ToolValidator()
        assert validator._models_cache == {}
        assert validator._schemas_cache == {}

    def test_register_tool_schema_simple(self):
        """Test registering a simple tool schema."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        }

        validator.register_tool_schema("search", schema)

        assert "search" in validator._schemas_cache
        assert "search" in validator._models_cache
        assert validator._schemas_cache["search"] == schema

    def test_register_tool_schema_complex(self):
        """Test registering a complex tool schema with multiple types."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
                "tags": {"type": "array", "items": {"type": "string"}},
                "active": {"type": "boolean"},
            },
            "required": ["query"],
        }

        validator.register_tool_schema("advanced_search", schema)

        assert "advanced_search" in validator._schemas_cache
        assert "advanced_search" in validator._models_cache

    def test_validate_parameters_success(self):
        """Test successful parameter validation."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        validator.register_tool_schema("search", schema)

        params = {"query": "test", "limit": 5}
        validated = validator.validate_parameters("search", params)

        assert validated["query"] == "test"
        assert validated["limit"] == 5

    def test_validate_parameters_type_coercion(self):
        """Test parameter validation with type coercion."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
            },
            "required": [],
        }
        validator.register_tool_schema("search", schema)

        # String that can be coerced to integer
        params = {"limit": "10"}
        validated = validator.validate_parameters("search", params)

        assert validated["limit"] == 10
        assert isinstance(validated["limit"], int)

    def test_validate_parameters_missing_required(self):
        """Test validation fails with missing required parameter."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        }
        validator.register_tool_schema("search", schema)

        with pytest.raises(ValidationError):
            validator.validate_parameters("search", {})

    def test_validate_parameters_unregistered_tool(self):
        """Test validation fails for unregistered tool."""
        validator = ToolValidator()

        with pytest.raises(ValueError, match="schema not registered"):
            validator.validate_parameters("nonexistent_tool", {})

    def test_validate_parameters_with_defaults(self):
        """Test validation uses default values."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        }
        validator.register_tool_schema("search", schema)

        params = {"query": "test"}
        validated = validator.validate_parameters("search", params)

        assert validated["query"] == "test"
        assert validated["limit"] == 10

    def test_preprocess_gemini_params_list_to_string(self):
        """Test preprocessing converts list to string when schema expects string."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "string"},
            },
        }
        validator.register_tool_schema("test_tool", schema)

        params = {"tags": ["python", "coding", "ai"]}
        processed = validator._preprocess_gemini_params("test_tool", params)

        assert processed["tags"] == "python, coding, ai"
        assert isinstance(processed["tags"], str)

    def test_preprocess_gemini_params_string_to_list(self):
        """Test preprocessing wraps string in list when schema expects array."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
            },
        }
        validator.register_tool_schema("test_tool", schema)

        params = {"items": "single_item"}
        processed = validator._preprocess_gemini_params("test_tool", params)

        assert processed["items"] == ["single_item"]
        assert isinstance(processed["items"], list)

    def test_preprocess_gemini_params_preserve_array(self):
        """Test preprocessing preserves arrays when schema expects array."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        }
        validator.register_tool_schema("test_tool", schema)

        params = {"tags": ["tag1", "tag2", "tag3"]}
        processed = validator._preprocess_gemini_params("test_tool", params)

        assert processed["tags"] == ["tag1", "tag2", "tag3"]
        assert isinstance(processed["tags"], list)

    def test_preprocess_gemini_params_no_type_definition(self):
        """Test preprocessing handles properties without type definition."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "data": {"description": "Any data"},
            },
        }
        validator.register_tool_schema("test_tool", schema)

        # When no type is defined, preserve original value
        params = {"data": ["item1", "item2"]}
        processed = validator._preprocess_gemini_params("test_tool", params)

        assert processed["data"] == ["item1", "item2"]

    def test_sanitize_string_sql_injection(self):
        """Test sanitize_string removes SQL injection patterns."""
        validator = ToolValidator()

        malicious = "test'; DROP TABLE users; --"
        sanitized = validator.sanitize_string(malicious)

        assert "--" not in sanitized
        assert ";" not in sanitized

    def test_sanitize_string_xss(self):
        """Test sanitize_string removes XSS patterns."""
        validator = ToolValidator()

        malicious = "<script>alert('XSS')</script>"
        sanitized = validator.sanitize_string(malicious)

        assert "<script>" not in sanitized
        assert "</script>" not in sanitized

    def test_sanitize_string_clean_input(self):
        """Test sanitize_string preserves clean input."""
        validator = ToolValidator()

        clean = "This is a normal search query"
        sanitized = validator.sanitize_string(clean)

        assert sanitized == clean

    def test_sanitize_string_removes_whitespace(self):
        """Test sanitize_string removes leading/trailing whitespace."""
        validator = ToolValidator()

        input_str = "  test query  "
        sanitized = validator.sanitize_string(input_str)

        assert sanitized == "test query"

    def test_map_json_type_to_python_string(self):
        """Test JSON type mapping for string."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "string"})
        assert python_type == str

    def test_map_json_type_to_python_integer(self):
        """Test JSON type mapping for integer."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "integer"})
        assert python_type == int

    def test_map_json_type_to_python_number(self):
        """Test JSON type mapping for number."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "number"})
        assert python_type == float

    def test_map_json_type_to_python_boolean(self):
        """Test JSON type mapping for boolean."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "boolean"})
        assert python_type == bool

    def test_map_json_type_to_python_object(self):
        """Test JSON type mapping for object."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "object"})
        assert python_type == dict

    def test_map_json_type_to_python_array(self):
        """Test JSON type mapping for array."""
        validator = ToolValidator()
        python_type = validator._map_json_type_to_python({"type": "array", "items": {"type": "string"}})
        # Check it's a list type (actual type checking is complex in Python)
        assert "list" in str(python_type).lower()

    def test_map_json_type_to_python_no_type(self):
        """Test JSON type mapping when no type specified."""
        validator = ToolValidator()
        from typing import Any

        python_type = validator._map_json_type_to_python({})
        # When no type is specified, should return Any
        assert python_type == Any

    def test_get_registered_tools_empty(self):
        """Test get_registered_tools returns empty list initially."""
        validator = ToolValidator()
        assert validator.get_registered_tools() == []

    def test_get_registered_tools_multiple(self):
        """Test get_registered_tools returns all registered tools."""
        validator = ToolValidator()

        schema1 = {"type": "object", "properties": {"query": {"type": "string"}}}
        schema2 = {"type": "object", "properties": {"sku": {"type": "string"}}}

        validator.register_tool_schema("search", schema1)
        validator.register_tool_schema("fetch", schema2)

        registered = validator.get_registered_tools()

        assert len(registered) == 2
        assert "search" in registered
        assert "fetch" in registered

    def test_clear_cache(self):
        """Test clear_cache removes all cached data."""
        validator = ToolValidator()

        schema = {"type": "object", "properties": {"query": {"type": "string"}}}
        validator.register_tool_schema("search", schema)

        assert len(validator._schemas_cache) == 1
        assert len(validator._models_cache) == 1

        validator.clear_cache()

        assert len(validator._schemas_cache) == 0
        assert len(validator._models_cache) == 0

    def test_validate_parameters_exclude_none(self):
        """Test validation excludes None values from output."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        validator.register_tool_schema("search", schema)

        params = {"query": "test", "limit": None}
        validated = validator.validate_parameters("search", params)

        assert "query" in validated
        assert "limit" not in validated  # None values excluded

    def test_create_model_from_schema_required_fields(self):
        """Test dynamic model creation handles required fields."""
        validator = ToolValidator()
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "optional": {"type": "string"},
            },
            "required": ["query"],
        }

        model = validator._create_model_from_schema("test_tool", schema)

        # Required field should not have default
        assert "query" in model.model_fields
        # Optional field should allow None
        assert "optional" in model.model_fields


class TestToolValidatorIntegration:
    """Integration tests for ToolValidator with sample MCP tools."""

    def test_sample_search_tool(self, sample_mcp_tools):
        """Test validation with sample search_products tool."""
        validator = ToolValidator()

        # Get search_products tool
        search_tool = sample_mcp_tools[0]
        validator.register_tool_schema(search_tool["name"], search_tool["inputSchema"])

        # Valid parameters
        params = {"query": "laptop", "limit": 5}
        validated = validator.validate_parameters("search_products", params)

        assert validated["query"] == "laptop"
        assert validated["limit"] == 5

    def test_sample_search_tool_missing_optional(self, sample_mcp_tools):
        """Test search tool with missing optional parameter."""
        validator = ToolValidator()

        search_tool = sample_mcp_tools[0]
        validator.register_tool_schema(search_tool["name"], search_tool["inputSchema"])

        # Only required parameter
        params = {"query": "laptop"}
        validated = validator.validate_parameters("search_products", params)

        assert validated["query"] == "laptop"
        assert "limit" not in validated  # Optional, not provided

    def test_sample_fetch_tool(self, sample_mcp_tools):
        """Test validation with sample fetch_by_sku tool."""
        validator = ToolValidator()

        fetch_tool = sample_mcp_tools[1]
        validator.register_tool_schema(fetch_tool["name"], fetch_tool["inputSchema"])

        params = {"sku": "LAPTOP-001"}
        validated = validator.validate_parameters("fetch_by_sku", params)

        assert validated["sku"] == "LAPTOP-001"
