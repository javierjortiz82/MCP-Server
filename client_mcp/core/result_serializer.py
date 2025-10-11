"""Tool result serialization with anti-hallucination formatting.

This module handles serialization of tool execution results into structured
formats suitable for Gemini API, with special handling to prevent hallucinations.
"""

import json
from typing import Any


class ResultSerializer:
    """Serializer for tool execution results.

    This class handles conversion of tool results to structured formats
    that prevent LLM hallucinations by using native arrays instead of
    artificial numbering (item_1, item_2, etc.).

    Attributes:
        None (stateless serializer)
    """

    @staticmethod
    def format_items_as_response(items: list[Any]) -> dict[str, Any]:
        """Format items as response with native array (no artificial numbering).

        Using native arrays prevents Gemini from hallucinating non-existent items.
        When we use item_1, item_2, ..., item_5, Gemini sees 5 fields and tries
        to fill all 5 even if only 3 exist. With arrays, Gemini respects the
        actual length.

        CLIENT-SIDE PAGINATION APPROACH:
        - Pass ALL items from tool to Gemini (no truncation)
        - Let system prompt instruct Gemini to show only PAGINATION_PAGE_SIZE items
        - PaginationManager automatically calculates total pages: ceil(total / PAGE_SIZE)
        - Example: 12 items, PAGE_SIZE=4 → 3 pages (4+4+4)
        - Example: 9 items, PAGE_SIZE=4 → 3 pages (4+4+1)

        This follows client-side pagination best practices where all data is available
        and the client (Gemini + PaginationManager) handles the display logic.

        Args:
            items: List of items to format

        Returns:
            Dict with products array and metadata

        Example:
            >>> items = [{"name": "Product 1"}, {"name": "Product 2"}]
            >>> result = ResultSerializer.format_items_as_response(items)
            >>> result["total_found"]
            2
            >>> len(result["products"])
            2
        """
        num_items = len(items)
        # Client-side pagination: pass ALL items (no truncation)
        # The system prompt instructs Gemini to show only PAGINATION_PAGE_SIZE
        items_to_show = items

        return {
            "total_found": num_items,
            "showing": len(items_to_show),
            "products": items_to_show,  # ✅ ALL items - Gemini respects prompt instructions
            "has_more": False,  # All items included, pagination handled by PaginationManager
        }

    @staticmethod
    def serialize_tool_result(result: Any) -> dict[str, Any]:
        """Serialize tool result maintaining JSON structure.

        ✅ CRITICAL: Don't convert to string - preserve structure for model inference.

        Args:
            result: Tool execution result

        Returns:
            Structured dict suitable for FunctionResponse

        Example:
            >>> result = [{"name": "Product 1"}]
            >>> serialized = ResultSerializer.serialize_tool_result(result)
            >>> "products" in serialized
            True
        """
        if result is None:
            return {"status": "success", "data": None}

        elif isinstance(result, dict):
            # Check if this is a wrapped list response from MCP server
            if "items" in result and isinstance(result["items"], list):
                # This is the new MCP format: {"items": [...], "count": N}
                # Transform to array format (no numbering to prevent hallucinations)
                return ResultSerializer.format_items_as_response(result["items"])
            # ✅ Already structured - return as-is
            return result

        elif isinstance(result, list):
            # ✅ List of results - transform to array format
            return ResultSerializer.format_items_as_response(result)

        elif isinstance(result, str):
            # Try to parse JSON string
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict | list):
                    # ✅ Successfully parsed JSON
                    return parsed if isinstance(parsed, dict) else {"items": parsed}
            except (json.JSONDecodeError, ValueError):
                pass
            # Fallback: wrap string in structure
            return {"text": result}

        elif isinstance(result, int | float | bool):
            # Primitive types
            return {"value": result, "type": type(result).__name__}

        else:
            # Unknown type - convert to dict if possible
            try:
                return {"value": str(result), "type": type(result).__name__}
            except Exception:
                return {"error": "Failed to serialize result"}
