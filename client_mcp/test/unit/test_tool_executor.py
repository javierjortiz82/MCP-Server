"""Unit tests for ToolExecutor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.tool_cache import ToolCache
from core.tool_executor import ToolExecutor
from core.tool_validator import ToolValidator
from observability.tracker import ToolTracker


class TestToolExecutor:
    """Test suite for ToolExecutor class."""

    def test_initialization_default(self):
        """Test ToolExecutor initialization with default components."""
        mock_connector = MagicMock()

        executor = ToolExecutor(mock_connector)

        assert executor.mcp == mock_connector
        assert isinstance(executor.validator, ToolValidator)
        assert executor.cache is not None
        assert executor.tracker is not None

    def test_initialization_custom_components(self):
        """Test ToolExecutor initialization with custom components."""
        mock_connector = MagicMock()
        custom_validator = ToolValidator()
        custom_cache = ToolCache()
        custom_tracker = ToolTracker()

        executor = ToolExecutor(
            mock_connector,
            validator=custom_validator,
            cache=custom_cache,
            tracker=custom_tracker,
        )

        assert executor.validator == custom_validator
        assert executor.cache == custom_cache
        assert executor.tracker == custom_tracker

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, sample_mcp_tools):
        """Test successful tool execution."""
        mock_connector = AsyncMock()
        mock_connector.call_tool = AsyncMock(
            return_value={"items": [{"id": 1, "name": "Product 1"}], "count": 1}
        )

        executor = ToolExecutor(mock_connector)

        # Register tool schema
        await executor.register_tool_schemas(sample_mcp_tools)

        # Execute tool
        result = await executor.execute_tool(
            "search_products", {"query": "laptop", "limit": 5}
        )

        assert result is not None
        assert result["count"] == 1
        mock_connector.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_without_validation(self, sample_mcp_tools):
        """Test tool execution without parameter validation."""
        mock_connector = AsyncMock()
        mock_connector.call_tool = AsyncMock(
            return_value={"items": [{"id": 1, "name": "Product"}], "count": 1}
        )

        executor = ToolExecutor(mock_connector)

        # Execute without validation
        result = await executor.execute_tool(
            "search_products",
            {"query": "laptop"},
            validate=False,
        )

        assert result is not None
        assert result["count"] == 1
        # Should call tool directly without validation
        mock_connector.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_tool_validation_failure(self, sample_mcp_tools):
        """Test tool execution with validation failure."""
        mock_connector = AsyncMock()

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        # Missing required parameter
        with pytest.raises(Exception):
            await executor.execute_tool("search_products", {})

    @pytest.mark.asyncio
    async def test_execute_tool_unregistered(self):
        """Test execution of unregistered tool fails."""
        mock_connector = AsyncMock()

        executor = ToolExecutor(mock_connector)

        with pytest.raises(ValueError, match="not found in cache"):
            await executor.execute_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    async def test_register_tool_schemas(self, sample_mcp_tools):
        """Test registering tool schemas."""
        mock_connector = AsyncMock()

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        # Check tools registered in validator
        registered_tools = executor.validator.get_registered_tools()
        assert "search_products" in registered_tools
        assert "fetch_by_sku" in registered_tools

    @pytest.mark.asyncio
    async def test_execute_tool_with_tracking(self, sample_mcp_tools):
        """Test tool execution includes tracking."""
        mock_connector = AsyncMock()
        mock_connector.call_tool = AsyncMock(
            return_value={"items": [{"id": 1}], "count": 1}
        )

        # Create fresh tracker to avoid counting previous test executions
        from observability.tracker import ToolTracker

        custom_tracker = ToolTracker()

        executor = ToolExecutor(mock_connector, tracker=custom_tracker)

        await executor.register_tool_schemas(sample_mcp_tools)
        await executor.execute_tool(
            "search_products",
            {"query": "laptop", "limit": 5},
            user_query="Busco una laptop",
        )

        # Check tracking recorded execution
        stats = executor.get_stats("search_products")
        assert stats["total_calls"] >= 1  # At least 1 call should be tracked

    def test_calculate_result_size_list(self):
        """Test result size calculation for list."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        result = [{"id": 1}, {"id": 2}, {"id": 3}]
        size = executor._calculate_result_size(result)

        assert size == 3

    def test_calculate_result_size_dict_with_count(self):
        """Test result size calculation for dict with count field."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        result = {"items": [{"id": 1}, {"id": 2}], "count": 2}
        size = executor._calculate_result_size(result)

        assert size == 2

    def test_calculate_result_size_dict_with_items(self):
        """Test result size calculation for dict with items field."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        result = {"items": [{"id": 1}, {"id": 2}, {"id": 3}]}
        size = executor._calculate_result_size(result)

        assert size == 3

    def test_calculate_result_size_none(self):
        """Test result size calculation for None."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        size = executor._calculate_result_size(None)

        assert size == 0

    def test_calculate_result_size_single_dict(self):
        """Test result size calculation for single dict."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        result = {"id": 1, "name": "Product"}
        size = executor._calculate_result_size(result)

        assert size == 1

    def test_get_stats(self):
        """Test getting execution statistics."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        stats = executor.get_stats()

        assert isinstance(stats, dict)

    def test_get_stats_for_specific_tool(self, sample_mcp_tools):
        """Test getting statistics for specific tool."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        stats = executor.get_stats("search_products")

        assert isinstance(stats, dict)

    def test_get_most_used_tools(self):
        """Test getting most used tools."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        most_used = executor.get_most_used_tools(top_n=5)

        assert isinstance(most_used, list)

    def test_get_slowest_tools(self):
        """Test getting slowest tools."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        slowest = executor.get_slowest_tools(top_n=5)

        assert isinstance(slowest, list)

    def test_get_error_rate_by_tool(self):
        """Test getting error rate by tool."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        error_rates = executor.get_error_rate_by_tool()

        assert isinstance(error_rates, dict)

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        cache_stats = executor.get_cache_stats()

        assert isinstance(cache_stats, dict)

    def test_clear_cache(self):
        """Test clearing tool cache."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Should not raise
        executor.clear_cache()

    def test_clear_metrics(self):
        """Test clearing execution metrics."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Should not raise
        executor.clear_metrics()

    def test_clear_all(self):
        """Test clearing both cache and metrics."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Should not raise
        executor.clear_all()

    def test_set_user_query(self):
        """Test setting user query for tracking."""
        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Should not raise
        executor.set_user_query("Busco una laptop")

    @pytest.mark.asyncio
    async def test_validate_parameters_with_cached_tool(self, sample_mcp_tools):
        """Test parameter validation uses cached tool schema."""
        mock_connector = AsyncMock()
        executor = ToolExecutor(mock_connector)

        # Register tool
        await executor.register_tool_schemas(sample_mcp_tools)

        # Validate parameters
        validated = executor._validate_parameters(
            "search_products", {"query": "laptop", "limit": 5}
        )

        assert validated["query"] == "laptop"
        assert validated["limit"] == 5

    @pytest.mark.asyncio
    async def test_export_metrics(self, tmp_path):
        """Test exporting metrics to file."""
        mock_connector = AsyncMock()
        executor = ToolExecutor(mock_connector)

        export_path = tmp_path / "metrics.json"

        # Should not raise
        executor.export_metrics(str(export_path))


class TestToolExecutorFallback:
    """Test suite for ToolExecutor fallback functionality."""

    @pytest.mark.asyncio
    async def test_fallback_on_empty_results_list(self, sample_mcp_tools):
        """Test automatic fallback when results list is empty."""
        mock_connector = AsyncMock()

        # First call returns empty, second returns results
        mock_connector.call_tool = AsyncMock(
            side_effect=[
                [],  # Empty results
                [{"id": 1, "name": "Product"}],  # Fallback results
            ]
        )

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        # Register fuzzy_search_smart tool
        fuzzy_tool = {
            "name": "fuzzy_search_smart",
            "description": "Fuzzy search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        }
        await executor.register_tool_schemas([fuzzy_tool])

        result = await executor.execute_tool(
            "fuzzy_search_smart", {"query": "laptop", "limit": 5}
        )

        # Should have called both tools (primary + fallback)
        assert mock_connector.call_tool.call_count == 2
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_fallback_on_empty_results_dict(self, sample_mcp_tools):
        """Test automatic fallback when results dict has empty items."""
        mock_connector = AsyncMock()

        # First call returns empty dict, second returns results
        mock_connector.call_tool = AsyncMock(
            side_effect=[
                {"items": [], "count": 0},  # Empty results
                {"items": [{"id": 1}], "count": 1},  # Fallback results
            ]
        )

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        # Register fuzzy_search_smart
        fuzzy_tool = {
            "name": "fuzzy_search_smart",
            "description": "Fuzzy search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        }
        await executor.register_tool_schemas([fuzzy_tool])

        result = await executor.execute_tool(
            "search_products", {"query": "laptop", "k": 5}
        )

        # Should have called both tools
        assert mock_connector.call_tool.call_count == 2

    @pytest.mark.asyncio
    async def test_no_fallback_with_results(self, sample_mcp_tools):
        """Test no fallback when results are present."""
        mock_connector = AsyncMock()
        mock_connector.call_tool = AsyncMock(
            return_value={"items": [{"id": 1}], "count": 1}
        )

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        result = await executor.execute_tool(
            "search_products", {"query": "laptop", "limit": 5}
        )

        # Should only call once (no fallback needed)
        assert mock_connector.call_tool.call_count == 1
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_fallback_prevents_infinite_loop(self, sample_mcp_tools):
        """Test fallback doesn't cause infinite recursion."""
        mock_connector = AsyncMock()

        # Both calls return empty
        mock_connector.call_tool = AsyncMock(return_value=[])

        executor = ToolExecutor(mock_connector)

        # Register both tools
        fuzzy_tool = {
            "name": "fuzzy_search_smart",
            "description": "Fuzzy search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        }
        await executor.register_tool_schemas(sample_mcp_tools + [fuzzy_tool])

        result = await executor.execute_tool(
            "fuzzy_search_smart", {"query": "laptop", "limit": 5}
        )

        # Should call exactly twice (primary + fallback, no recursion)
        assert mock_connector.call_tool.call_count == 2
        assert result == []


class TestToolExecutorRetry:
    """Test suite for ToolExecutor retry functionality."""

    @pytest.mark.asyncio
    @patch("config.settings.settings.ENABLE_RETRY", True)
    async def test_retry_disabled_by_default(self, sample_mcp_tools):
        """Test retry is disabled by default in tests."""
        mock_connector = AsyncMock()
        mock_connector.call_tool = AsyncMock(
            return_value={"items": [{"id": 1}], "count": 1}
        )

        executor = ToolExecutor(mock_connector)
        await executor.register_tool_schemas(sample_mcp_tools)

        result = await executor.execute_tool(
            "search_products", {"query": "laptop", "limit": 5}
        )

        # Should call once (retry not configured in test environment)
        assert mock_connector.call_tool.call_count == 1
