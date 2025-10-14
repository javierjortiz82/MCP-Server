"""Fallback strategy for tool execution failures.

This module provides fallback mechanisms to use alternative tools
when primary tool execution fails.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class FallbackRule:
    """Rule for falling back from one tool to another."""

    primary_tool: str
    fallback_tool: str
    param_mapping: dict[str, str] | None = (
        None  # Maps primary params to fallback params
    )
    condition: Callable[[Exception], bool] | None = (
        None  # Optional condition to trigger fallback
    )


class FallbackStrategy:
    """Strategy for handling tool failures with fallbacks.

    Provides intelligent fallback to alternative tools when primary
    tool execution fails, with parameter mapping and conditional rules.

    Example:
        strategy = FallbackStrategy()

        # Define fallback rule
        strategy.add_rule(
            primary_tool="search_products",
            fallback_tool="fuzzy_search_smart",
            param_mapping={"query": "search_term"}
        )

        # Execute with fallback
        result = await strategy.execute_with_fallback(
            primary_tool="search_products",
            params={"query": "laptop"},
            executor=tool_executor
        )
    """

    def __init__(self, logger: logging.Logger | None = None):
        """Initialize fallback strategy.

        Args:
            logger: Optional logger for fallback events
        """
        self.logger = logger or logging.getLogger(__name__)
        self._rules: dict[str, list[FallbackRule]] = {}

    def add_rule(
        self,
        primary_tool: str,
        fallback_tool: str,
        param_mapping: dict[str, str] | None = None,
        condition: Callable[[Exception], bool] | None = None,
    ) -> None:
        """Add a fallback rule.

        Args:
            primary_tool: Primary tool name
            fallback_tool: Fallback tool name to use on failure
            param_mapping: Optional parameter name mapping
            condition: Optional condition function to check if fallback should trigger
        """
        rule = FallbackRule(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            param_mapping=param_mapping,
            condition=condition,
        )

        if primary_tool not in self._rules:
            self._rules[primary_tool] = []

        self._rules[primary_tool].append(rule)

    async def execute_with_fallback(
        self,
        primary_tool: str,
        params: dict[str, Any],
        executor: Any,  # ToolExecutor type (avoiding circular import)
        max_fallback_depth: int = 2,
    ) -> Any:
        """Execute tool with automatic fallback on failure.

        Args:
            primary_tool: Primary tool to execute
            params: Tool parameters
            executor: ToolExecutor instance to use for execution
            max_fallback_depth: Maximum number of fallback attempts

        Returns:
            Result from successful execution (primary or fallback)

        Raises:
            Exception: If all fallback attempts fail
        """
        current_tool = primary_tool
        current_params = params
        depth = 0

        while depth <= max_fallback_depth:
            try:
                # Try to execute current tool (without fallback to avoid recursion)
                result = await executor.execute_tool(
                    current_tool, current_params, _use_fallback=False
                )

                if depth > 0:
                    self.logger.info(
                        f"Fallback successful: used '{current_tool}' instead of '{primary_tool}'"
                    )

                return result

            except Exception as e:
                # Check if fallback rules exist for current tool
                if current_tool not in self._rules:
                    self.logger.error(
                        f"Tool '{current_tool}' failed and no fallback rules defined"
                    )
                    raise

                # Find applicable fallback rule
                fallback_rule = self._find_applicable_rule(current_tool, e)

                if not fallback_rule:
                    self.logger.error(
                        f"Tool '{current_tool}' failed but no applicable fallback rule found"
                    )
                    raise

                # Apply fallback
                self.logger.warning(
                    f"Tool '{current_tool}' failed: {e}. Falling back to '{fallback_rule.fallback_tool}'"
                )

                # Map parameters if needed
                if fallback_rule.param_mapping:
                    current_params = self._map_parameters(
                        current_params, fallback_rule.param_mapping
                    )

                # Update for next iteration
                current_tool = fallback_rule.fallback_tool
                depth += 1

        # Max depth reached
        raise RuntimeError(
            f"Maximum fallback depth ({max_fallback_depth}) reached. Original tool: {primary_tool}"
        )

    def _find_applicable_rule(
        self, tool_name: str, exception: Exception
    ) -> FallbackRule | None:
        """Find the first applicable fallback rule for a tool.

        Args:
            tool_name: Tool that failed
            exception: Exception that occurred

        Returns:
            Applicable FallbackRule or None
        """
        rules = self._rules.get(tool_name, [])

        for rule in rules:
            # If rule has condition, check it
            if rule.condition:
                if rule.condition(exception):
                    return rule
            else:
                # No condition, rule applies
                return rule

        return None

    def _map_parameters(
        self, params: dict[str, Any], mapping: dict[str, str]
    ) -> dict[str, Any]:
        """Map parameters from one tool's schema to another.

        Args:
            params: Original parameters
            mapping: Parameter name mapping (old_name -> new_name)

        Returns:
            Mapped parameters
        """
        mapped_params: dict[str, Any] = {}

        for old_name, value in params.items():
            # Use mapping if exists, otherwise keep same name
            new_name = mapping.get(old_name, old_name)
            mapped_params[new_name] = value

        return mapped_params

    def get_fallback_chain(self, primary_tool: str) -> list[str]:
        """Get the chain of fallback tools for a primary tool.

        Args:
            primary_tool: Primary tool name

        Returns:
            List of tool names in fallback order
        """
        chain = [primary_tool]
        current = primary_tool

        # Build chain (limit to prevent infinite loops)
        max_chain_length = 10
        while len(chain) < max_chain_length:
            rules = self._rules.get(current, [])

            if not rules:
                break

            # Take first rule's fallback
            current = rules[0].fallback_tool
            chain.append(current)

        return chain

    def has_fallback(self, tool_name: str) -> bool:
        """Check if a tool has any fallback rules.

        Args:
            tool_name: Tool name to check

        Returns:
            True if fallback rules exist, False otherwise
        """
        return tool_name in self._rules and len(self._rules[tool_name]) > 0

    def clear_rules(self) -> None:
        """Clear all fallback rules."""
        self._rules.clear()


def create_default_fallback_strategy() -> FallbackStrategy:
    """Create a fallback strategy with common default rules.

    Returns:
        FallbackStrategy with pre-configured common rules
    """
    strategy = FallbackStrategy()

    # Example default rules (customize based on actual MCP tools)
    # search_products -> fuzzy_search_smart
    strategy.add_rule(
        primary_tool="search_products",
        fallback_tool="fuzzy_search_smart",
        param_mapping={"query": "search_term"},
    )

    # fetch_by_sku -> fetch_by_id (if SKU not found, try as ID)
    strategy.add_rule(
        primary_tool="fetch_by_sku",
        fallback_tool="fetch_by_id",
        param_mapping={"sku": "product_id"},
    )

    return strategy
