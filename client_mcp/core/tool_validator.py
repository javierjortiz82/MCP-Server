"""Tool Parameter Validator using Pydantic.

This module provides validation and sanitization of MCP tool parameters
using Pydantic dynamic models generated from JSON Schema.
"""

import re
from typing import Any

try:
    from pydantic import BaseModel, Field, ValidationError, create_model
except ImportError:
    raise RuntimeError("Instala Pydantic con: pip install pydantic>=2.0")


class ToolValidator:
    """Validator for MCP tool parameters using Pydantic.

    Dynamically creates Pydantic models from JSON Schema (inputSchema)
    and validates/coerces parameters before tool execution.
    """

    def __init__(self):
        """Initialize the tool validator."""
        self._models_cache: dict[str, type[BaseModel]] = {}
        self._schemas_cache: dict[str, dict] = {}

    def register_tool_schema(self, tool_name: str, input_schema: dict) -> None:
        """Register a tool's input schema for validation.

        Args:
            tool_name: Name of the tool
            input_schema: JSON Schema from tool's inputSchema field
        """
        self._schemas_cache[tool_name] = input_schema

        # Create Pydantic model from schema
        model = self._create_model_from_schema(tool_name, input_schema)
        self._models_cache[tool_name] = model

    def validate_parameters(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate and coerce parameters for a tool.

        Args:
            tool_name: Name of the tool
            params: Parameters to validate

        Returns:
            Validated and coerced parameters

        Raises:
            ValidationError: If parameters don't match schema
            ValueError: If tool schema not registered
        """
        if tool_name not in self._models_cache:
            raise ValueError(f"Tool '{tool_name}' schema not registered")

        model = self._models_cache[tool_name]

        # Pre-process parameters to handle common type mismatches from Gemini
        preprocessed_params = self._preprocess_gemini_params(tool_name, params)

        try:
            # Validate with Pydantic model
            validated_instance = model(**preprocessed_params)

            # Convert back to dict
            return validated_instance.model_dump(exclude_none=True)

        except ValidationError as e:
            # Re-raise with more context
            raise ValidationError.from_exception_data(
                title=f"Validation failed for tool '{tool_name}'",
                line_errors=e.errors(),  # type: ignore[arg-type]
            ) from e

    def _preprocess_gemini_params(
        self, tool_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Preprocess parameters from Gemini to handle type mismatches.

        Gemini sometimes sends lists as RepeatedComposite or in formats
        that don't match the expected schema. This method normalizes them.

        Args:
            tool_name: Name of the tool
            params: Raw parameters from Gemini

        Returns:
            Preprocessed parameters
        """
        # Get the schema for this tool
        schema = self._schemas_cache.get(tool_name, {})
        properties = schema.get("properties", {})

        processed: dict[str, Any] = {}
        for key, value in params.items():
            prop_def = properties.get(key, {})
            prop_type = prop_def.get("type")

            # Check if value is list-like (includes RepeatedComposite from protobuf)
            is_list_like = (
                isinstance(value, list | tuple)
                or hasattr(value, "__iter__")
                and not isinstance(value, str | bytes | dict)
            )

            # Convert protobuf RepeatedComposite and similar types to standard list
            if is_list_like and not isinstance(value, str | bytes | dict | list):
                value = list(value)
                is_list_like = True

            # Handle list-like values based on schema type
            if is_list_like and isinstance(value, list):
                if prop_type == "array":
                    # Schema expects array, keep as list
                    processed[key] = value
                elif prop_type == "string":
                    # Schema explicitly expects string, convert list to comma-separated
                    processed[key] = ", ".join(str(item) for item in value)
                elif prop_type is None:
                    # Schema doesn't define type - keep original list
                    # This is the most common case with MCP tools
                    processed[key] = value
                else:
                    # Unknown type, take first element as fallback
                    processed[key] = value[0] if value else None
            elif prop_type == "array" and not isinstance(value, list):
                # Schema expects array but value is not list, wrap in list
                processed[key] = [value] if value is not None else None
            else:
                # No conversion needed
                processed[key] = value
        return processed

    def sanitize_string(self, value: str) -> str:
        """Sanitize string input to prevent injection attacks.

        Args:
            value: String to sanitize

        Returns:
            Sanitized string
        """
        # Remove potential SQL injection patterns
        dangerous_patterns = [
            r"(\-\-)|(\;)|(\/*)|(\*\/)",  # SQL comments
            r"(exec\s)|(:execute\s)",  # SQL exec
            r"<script[^>]*>.*?</script>",  # XSS - complete script tags
            r"<script[^>]*>",  # XSS - opening script tags
            r"</script>",  # XSS - closing script tags
        ]

        sanitized = value
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        return sanitized.strip()

    def _create_model_from_schema(
        self, tool_name: str, schema: dict
    ) -> type[BaseModel]:
        """Create a Pydantic model dynamically from JSON Schema.

        Args:
            tool_name: Name of the tool (for model name)
            schema: JSON Schema definition

        Returns:
            Dynamically created Pydantic model class
        """
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))

        # Build field definitions for Pydantic
        field_definitions: dict[str, Any] = {}

        for prop_name, prop_def in properties.items():
            # Map JSON Schema types to Python types
            python_type = self._map_json_type_to_python(prop_def)

            # Check if field is required
            is_required = prop_name in required

            # Get default value if provided
            default_value = prop_def.get("default", ...)

            # Create Field with validation
            if is_required and default_value is ...:
                # Required field without default
                field_definitions[prop_name] = (
                    python_type,
                    Field(..., description=prop_def.get("description", "")),
                )
            elif default_value is not ...:
                # Field with default
                field_definitions[prop_name] = (
                    python_type,
                    Field(
                        default=default_value,
                        description=prop_def.get("description", ""),
                    ),
                )
            else:
                # Optional field
                field_definitions[prop_name] = (
                    python_type | None,
                    Field(default=None, description=prop_def.get("description", "")),
                )

        # Create dynamic Pydantic model
        model_name = f"{tool_name.title().replace('_', '')}Params"
        return create_model(model_name, **field_definitions)

    def _map_json_type_to_python(self, prop_def: dict) -> type:
        """Map JSON Schema type to Python type.

        Args:
            prop_def: JSON Schema property definition

        Returns:
            Python type
        """
        json_type = prop_def.get("type")

        # If no type specified, use Any to accept anything
        if json_type is None:
            return Any

        # Handle array type with items
        if json_type == "array":
            items_type = prop_def.get("items", {}).get("type", "string")
            item_python_type = self._get_basic_python_type(items_type)
            return list[item_python_type]  # type: ignore[valid-type]

        return self._get_basic_python_type(json_type)

    def _get_basic_python_type(self, json_type: str) -> type:
        """Get basic Python type from JSON type string.

        Args:
            json_type: JSON Schema type string

        Returns:
            Python type
        """
        type_mapping: dict[str, type] = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        return type_mapping.get(json_type, str)

    def get_registered_tools(self) -> list[str]:
        """Get list of registered tool names.

        Returns:
            List of tool names with registered schemas
        """
        return list(self._schemas_cache.keys())

    def clear_cache(self) -> None:
        """Clear all cached models and schemas."""
        self._models_cache.clear()
        self._schemas_cache.clear()
