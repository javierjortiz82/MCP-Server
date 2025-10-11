"""Tool executor orchestrator combining validation, caching, and tracking.

This module provides a high-level executor that orchestrates all improvements:
- Parameter validation (Pydantic)
- Result caching
- Execution tracking and metrics
- Error handling
"""

import uuid
from typing import Any

try:
    from ..config.settings import settings
    from ..observability.tracker import ToolTracker, get_global_tracker
    from ..strategies.fallback import FallbackStrategy
    from ..strategies.retry import RetryConfig, RetryStrategy
    from .mcp_connector import MCPConnector
    from .tool_cache import ToolCache, get_global_cache
    from .tool_validator import ToolValidator
except ImportError:
    # Fallback for test environment
    from config.settings import settings
    from core.mcp_connector import MCPConnector
    from core.tool_cache import ToolCache, get_global_cache
    from core.tool_validator import ToolValidator
    from observability.tracker import ToolTracker, get_global_tracker
    from strategies.fallback import FallbackStrategy
    from strategies.retry import RetryConfig, RetryStrategy


class ToolExecutor:
    """High-level executor for MCP tools with validation, caching, and tracking.

    Orchestrates all improvements into a single easy-to-use interface:
    - Validates parameters before execution
    - Caches tool schemas for performance
    - Tracks execution metrics automatically
    - Provides unified error handling

    Example:
        executor = ToolExecutor(mcp_connector)

        # Execute with automatic validation and tracking
        result = await executor.execute_tool(
            "search_products",
            {"query": "laptop", "limit": 5},
            user_query="Busco una laptop"
        )

        # Get execution stats
        stats = executor.get_stats()
    """

    def __init__(
        self,
        mcp_connector: MCPConnector,
        validator: ToolValidator | None = None,
        cache: ToolCache | None = None,
        tracker: ToolTracker | None = None,
        retry_strategy: RetryStrategy | None = None,
        fallback_strategy: FallbackStrategy | None = None,
    ):
        """Initialize tool executor.

        Args:
            mcp_connector: MCP connector instance
            validator: Optional custom validator (uses new instance if None)
            cache: Optional custom cache (uses global if None)
            tracker: Optional custom tracker (uses global if None)
            retry_strategy: Optional retry strategy (uses config if None)
            fallback_strategy: Optional fallback strategy (uses config if None)
        """
        self.mcp = mcp_connector
        self.validator = validator or ToolValidator()
        self.cache = cache or get_global_cache()
        self.tracker = tracker or get_global_tracker()

        # Initialize retry strategy if enabled
        self.retry_strategy: RetryStrategy | None
        if settings.ENABLE_RETRY:
            if retry_strategy:
                self.retry_strategy = retry_strategy
            else:
                retry_config = RetryConfig(
                    max_attempts=settings.RETRY_MAX_ATTEMPTS,
                    initial_delay_ms=settings.RETRY_INITIAL_DELAY_MS,
                    max_delay_ms=settings.RETRY_MAX_DELAY_MS,
                    exponential_base=settings.RETRY_EXPONENTIAL_BASE,
                    jitter=settings.RETRY_JITTER,
                )
                self.retry_strategy = RetryStrategy(retry_config)
        else:
            self.retry_strategy = None

        # Initialize fallback strategy if enabled
        self.fallback_strategy: FallbackStrategy | None
        if settings.ENABLE_FALLBACK:
            self.fallback_strategy = fallback_strategy or FallbackStrategy()
        else:
            self.fallback_strategy = None

        # Store current user query for tracking context
        self.current_user_query: str | None = None

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        user_query: str | None = None,
        validate: bool = True,
        _use_fallback: bool = True,
    ) -> Any:
        """Execute an MCP tool with validation and tracking.

        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            user_query: Optional user query for tracking context
            validate: Whether to validate parameters (default: True)
            _use_fallback: Internal flag to enable/disable fallback (default: True)

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found or validation fails
            RuntimeError: If execution fails
        """
        # Generate unique call ID for debugging duplicate calls
        call_id = str(uuid.uuid4())[:8]

        # Use current_user_query as fallback if user_query not provided
        effective_query = user_query or self.current_user_query

        # Import logger for debugging
        try:
            from ..utils.logger import logger
        except ImportError:
            from utils.logger import logger

        # Log tool execution for duplicate call detection
        logger.debug(
            f"🔧 [CALL-{call_id}] Tool: {tool_name} | "
            f"Query: {effective_query or 'N/A'} | "
            f"Params: {parameters}"
        )

        # Validate parameters if enabled
        validated_params = self._validate_parameters(tool_name, parameters) if validate else parameters

        # Execute with tracking (use effective_query for context)
        with self.tracker.track_with_result(tool_name, validated_params, effective_query) as track_ctx:
            # Call MCP tool with retry if enabled
            if self.retry_strategy:
                result = await self.retry_strategy.execute_with_retry(
                    lambda: self.mcp.call_tool(tool_name, validated_params)
                )
            else:
                result = await self.mcp.call_tool(tool_name, validated_params)

            # Update tracking context with result size
            track_ctx["result_size"] = self._calculate_result_size(result)

            # AUTOMATIC FALLBACK FOR EMPTY RESULTS: Check BEFORE exception-based fallback
            # This improves found rate without breaking existing behavior
            # Check for empty results in both list and dict formats
            is_empty = False

            if isinstance(result, list) and len(result) == 0:
                is_empty = True
            elif isinstance(result, dict) and (
                ("items" in result and isinstance(result["items"], list) and len(result["items"]) == 0)
                or ("count" in result and result["count"] == 0)
            ):
                # Handle MCP protocol format: {"items": [...], "count": N}
                is_empty = True

            if is_empty and _use_fallback:
                fallback_tool = None
                fallback_params = None

                # fuzzy_search_smart → search_products (conceptual search)
                if tool_name == "fuzzy_search_smart":
                    fallback_tool = "search_products"
                    fallback_params = {
                        "query": validated_params.get("query", ""),
                        "k": validated_params.get("limit", 5),
                    }
                # search_products → fuzzy_search_smart (broader fuzzy)
                elif tool_name == "search_products":
                    fallback_tool = "fuzzy_search_smart"
                    fallback_params = {
                        "query": validated_params.get("query", ""),
                        "limit": validated_params.get("k", 10),
                    }

                # Execute fallback if configured
                if fallback_tool and fallback_params:
                    try:
                        from ..utils.logger import logger
                    except ImportError:
                        from utils.logger import logger

                    logger.info(f"🔄 Fallback: {tool_name} (0 results) → {fallback_tool}")
                    # Recursive call with _use_fallback=False to prevent infinite loops
                    result = await self.execute_tool(
                        fallback_tool,
                        fallback_params,
                        user_query=effective_query,
                        validate=validate,
                        _use_fallback=False,
                    )

            return result

    def _validate_parameters(self, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate tool parameters using cached schema.

        Args:
            tool_name: Tool name
            parameters: Parameters to validate

        Returns:
            Validated parameters

        Raises:
            ValueError: If tool not registered or validation fails
        """
        # Check if tool schema is in validator cache
        if tool_name not in self.validator.get_registered_tools():
            # Try to get schema from cache
            cached_tool = self.cache.get_tool(tool_name)

            if cached_tool:
                # Register schema in validator
                self.validator.register_tool_schema(tool_name, cached_tool.input_schema)
            else:
                raise ValueError(f"Tool '{tool_name}' not found in cache. Ensure tools are discovered first.")

        # Validate parameters
        return self.validator.validate_parameters(tool_name, parameters)

    def _calculate_result_size(self, result: Any) -> int:
        """Calculate result size for metrics.

        Args:
            result: Tool execution result

        Returns:
            Size metric (number of items returned, 0 for None/empty)
        """
        if result is None:
            return 0
        if isinstance(result, list):
            return len(result)
        if isinstance(result, dict):
            # Check if this is the new MCP format with "count" field
            if "count" in result:
                return result["count"]
            # Check if this is a wrapped format with "items"
            if "items" in result and isinstance(result["items"], list):
                return len(result["items"])
            # Legacy: single item dict
            return 1
        return 1

    async def register_tool_schemas(self, tools_definitions: list[dict[str, Any]]) -> None:
        """Register tool schemas for validation from discovered tools.

        Args:
            tools_definitions: List of tool definitions from list_tools()
        """
        for tool_def in tools_definitions:
            tool_name = tool_def["name"]
            input_schema = tool_def.get("inputSchema", {})

            # Register in validator
            self.validator.register_tool_schema(tool_name, input_schema)

            # Cache tool definition
            self.cache.cache_tool(
                name=tool_name,
                description=tool_def.get("description", ""),
                input_schema=input_schema,
            )

    def get_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """Get execution statistics.

        Args:
            tool_name: Optional tool name to filter stats

        Returns:
            Statistics dictionary
        """
        return self.tracker.get_stats(tool_name)

    def get_most_used_tools(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Get most frequently used tools.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, call_count) tuples
        """
        return self.tracker.get_most_used_tools(top_n)

    def get_slowest_tools(self, top_n: int = 5) -> list[tuple[str, float]]:
        """Get slowest tools by average execution time.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, avg_time_ms) tuples
        """
        return self.tracker.get_slowest_tools(top_n)

    def get_error_rate_by_tool(self) -> dict[str, float]:
        """Get error rate percentage for each tool.

        Returns:
            Dictionary mapping tool name to error rate percentage
        """
        return self.tracker.get_error_rate_by_tool()

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Cache statistics dictionary
        """
        return self.cache.get_cache_stats()

    def export_metrics(self, file_path: str) -> None:
        """Export all collected metrics to JSON file.

        Args:
            file_path: Path to export file
        """
        self.tracker.export_metrics(file_path)

    def clear_cache(self) -> None:
        """Clear tool cache."""
        self.cache.invalidate_all()

    def clear_metrics(self) -> None:
        """Clear execution metrics."""
        self.tracker.clear_metrics()

    def clear_all(self) -> None:
        """Clear both cache and metrics."""
        self.clear_cache()
        self.clear_metrics()
        self.validator.clear_cache()

    def set_user_query(self, query: str) -> None:
        """Set current user query for tracking context.

        Args:
            query: User query string
        """
        self.current_user_query = query
        self.tracker.set_user_query(query)

    def add_fallback_rule(
        self,
        primary_tool: str,
        fallback_tool: str,
        param_mapping: dict[str, str] | None = None,
    ) -> None:
        """Add a fallback rule for a tool.

        Args:
            primary_tool: Primary tool name
            fallback_tool: Fallback tool to use if primary fails
            param_mapping: Optional parameter name mapping

        Raises:
            RuntimeError: If fallback strategy is not enabled
        """
        if not self.fallback_strategy:
            raise RuntimeError("Fallback strategy not enabled. Set ENABLE_FALLBACK=true")

        self.fallback_strategy.add_rule(
            primary_tool=primary_tool,
            fallback_tool=fallback_tool,
            param_mapping=param_mapping,
        )

    def get_fallback_chain(self, tool_name: str) -> list[str]:
        """Get fallback chain for a tool.

        Args:
            tool_name: Tool name

        Returns:
            List of tool names in fallback order (empty if no fallback)
        """
        if not self.fallback_strategy:
            return []

        return self.fallback_strategy.get_fallback_chain(tool_name)
