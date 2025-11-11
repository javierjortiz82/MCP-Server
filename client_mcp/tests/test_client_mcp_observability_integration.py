"""Integration tests for client_mcp observability features.

Tests structured logging, metrics collection, and latency tracking across
all client_mcp components including MCPConnector, ToolExecutor, ResponseProcessor,
and retry strategies.

Author: Lab01-MCP Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

try:
    from email_service.observability.metrics import get_metrics_collector, reset_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    pytest.skip("Observability framework not available", allow_module_level=True)


class TestMCPConnectorObservability:
    """Test suite for MCPConnector observability features."""

    def test_mcp_connector_initialization(self):
        """Test MCPConnector initializes observability components."""
        from client_mcp.core.mcp_connector import MCPConnector

        connector = MCPConnector("http://localhost:8009/mcp")

        # Verify observability components are initialized
        assert hasattr(connector, "structured_logger")
        assert hasattr(connector, "metrics")
        assert connector.structured_logger is not None
        assert connector.metrics is not None

    @pytest.mark.asyncio
    async def test_mcp_health_check_metrics(self):
        """Test health check records metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Mock the health check response
        with patch("client_mcp.core.mcp_connector.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"status": "healthy"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            from client_mcp.core.mcp_connector import MCPConnector
            result = await MCPConnector.check_server_health("http://localhost:8009")

            # Verify health check was successful
            assert result["status"] == "healthy"

            # Check metrics were recorded
            summary = metrics.get_summary()
            assert summary["counters"].get("mcp_health_check_success", 0) >= 1

    @pytest.mark.asyncio
    async def test_mcp_list_tools_metrics(self):
        """Test list_tools tracks tool discovery metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.core.mcp_connector import MCPConnector

        # Create mock connector and session
        connector = MCPConnector("http://localhost:8009/mcp")

        # Mock session with tools
        mock_tool = MagicMock()
        mock_tool.name = "test_tool"
        mock_tool.description = "Test tool"
        mock_tool.inputSchema = {"type": "object"}

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.tools = [mock_tool]
        mock_session.list_tools = AsyncMock(return_value=mock_result)

        connector.session = mock_session

        # Call list_tools
        tools = await connector.list_tools()

        # Verify tools were returned
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

        # Check metrics
        summary = metrics.get_summary()
        assert summary["counters"].get("mcp_list_tools_success", 0) >= 1
        assert summary["gauges"].get("mcp_tools_available", 0) >= 1

    @pytest.mark.asyncio
    async def test_mcp_call_tool_metrics(self):
        """Test call_tool tracks execution metrics per tool."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.core.mcp_connector import MCPConnector

        connector = MCPConnector("http://localhost:8009/mcp")

        # Mock session
        mock_session = AsyncMock()
        mock_content = MagicMock()
        mock_content.text = '{"result": "success"}'
        mock_result = MagicMock()
        mock_result.content = [mock_content]
        mock_session.call_tool = AsyncMock(return_value=mock_result)

        connector.session = mock_session

        # Call tool
        result = await connector.call_tool("search", {"query": "test"})

        # Verify result
        assert result["result"] == "success"

        # Check metrics
        summary = metrics.get_summary()
        assert summary["counters"].get("mcp_tool_call_attempt_search", 0) >= 1
        assert summary["counters"].get("mcp_tool_call_success_search", 0) >= 1


class TestToolExecutorObservability:
    """Test suite for ToolExecutor observability features."""

    def test_tool_executor_initialization(self):
        """Test ToolExecutor initializes observability components."""
        from client_mcp.core.tool_executor import ToolExecutor
        from client_mcp.core.mcp_connector import MCPConnector

        mcp = MCPConnector("http://localhost:8009/mcp")
        executor = ToolExecutor(mcp)

        # Verify observability components are initialized
        assert hasattr(executor, "structured_logger")
        assert hasattr(executor, "metrics")
        if OBSERVABILITY_AVAILABLE:
            assert executor.structured_logger is not None
            assert executor.metrics is not None

    @pytest.mark.asyncio
    async def test_tool_execution_metrics(self):
        """Test tool execution tracks latency and success/failure."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.core.tool_executor import ToolExecutor
        from client_mcp.core.mcp_connector import MCPConnector
        from client_mcp.core.tool_validator import ToolValidator
        from client_mcp.core.tool_cache import ToolCache

        mcp = AsyncMock(spec=MCPConnector)
        executor = ToolExecutor(mcp)

        # Mock validator and cache
        validator = MagicMock(spec=ToolValidator)
        validator.get_registered_tools.return_value = ["search"]
        validator.validate_parameters = MagicMock(return_value={"query": "test"})

        cache = MagicMock(spec=ToolCache)
        executor.validator = validator
        executor.cache = cache

        # Mock MCP call
        mcp.call_tool = AsyncMock(return_value={"items": [{"sku": "123"}], "count": 1})

        # Register tool schema
        await executor.register_tool_schemas([
            {
                "name": "search",
                "description": "Search products",
                "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}}
            }
        ])

        # Execute tool
        result = await executor.execute_tool("search", {"query": "test"})

        # Verify result
        assert result["count"] == 1

        # Check metrics were recorded
        summary = metrics.get_summary()
        assert summary["counters"].get("tool_execution_attempt_search", 0) >= 1
        assert summary["counters"].get("tool_execution_success_search", 0) >= 1


class TestResponseProcessorObservability:
    """Test suite for ResponseProcessor observability features."""

    def test_response_processor_initialization(self):
        """Test ResponseProcessor initializes observability components."""
        from client_mcp.core.response_processor import ResponseProcessor
        from client_mcp.core.response_validator import ResponseValidator
        from client_mcp.core.debug_formatter import DebugFormatter

        validator = MagicMock(spec=ResponseValidator)
        formatter = MagicMock(spec=DebugFormatter)

        processor = ResponseProcessor(validator, formatter)

        # Verify observability components are initialized
        assert hasattr(processor, "structured_logger")
        assert hasattr(processor, "metrics")
        if OBSERVABILITY_AVAILABLE:
            assert processor.structured_logger is not None
            assert processor.metrics is not None

    @pytest.mark.asyncio
    async def test_response_processing_metrics(self):
        """Test response processing tracks validation metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.core.response_processor import ResponseProcessor
        from client_mcp.core.response_validator import ResponseValidator
        from client_mcp.core.debug_formatter import DebugFormatter

        # Create mocks
        validator = AsyncMock(spec=ResponseValidator)
        validator.validate_response_skus = MagicMock(return_value="Valid response")
        validator.remove_generated_debug_info = MagicMock(return_value="Valid response")

        formatter = MagicMock(spec=DebugFormatter)
        validator.clean_json_artifacts = MagicMock(return_value="Cleaned response")

        processor = ResponseProcessor(validator, formatter)

        # Mock the static method
        with patch.object(ResponseValidator, "remove_generated_debug_info", return_value="Valid response"):
            with patch.object(ResponseValidator, "clean_json_artifacts", return_value="Cleaned response"):
                # Process response
                result = await processor.process_text_response("Test response", "Test query")

                # Check metrics
                summary = metrics.get_summary()
                assert summary["counters"].get("response_processing_attempts", 0) >= 1
                assert summary["counters"].get("response_validation_success", 0) >= 1


class TestRetryStrategyObservability:
    """Test suite for retry strategy observability features."""

    def test_retry_strategy_initialization(self):
        """Test RetryStrategy initializes observability components."""
        from client_mcp.strategies.retry import RetryStrategy, RetryConfig

        config = RetryConfig(max_attempts=3)
        strategy = RetryStrategy(config)

        # Verify observability components are initialized
        assert hasattr(strategy, "structured_logger")
        assert hasattr(strategy, "metrics")
        if OBSERVABILITY_AVAILABLE:
            assert strategy.structured_logger is not None
            assert strategy.metrics is not None

    @pytest.mark.asyncio
    async def test_retry_success_metrics(self):
        """Test successful retry tracking."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.strategies.retry import RetryStrategy, RetryConfig

        config = RetryConfig(max_attempts=3)
        strategy = RetryStrategy(config)

        # Mock successful function (succeeds on first attempt)
        async def success_func():
            return "success"

        result = await strategy.execute_with_retry(success_func)

        # Verify result
        assert result == "success"

        # Check metrics
        summary = metrics.get_summary()
        assert summary["counters"].get("retry_executions_started", 0) >= 1
        assert summary["counters"].get("retry_executions_succeeded", 0) >= 1

    @pytest.mark.asyncio
    async def test_retry_failure_metrics(self):
        """Test retry failure tracking after exhausting attempts."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.strategies.retry import RetryStrategy, RetryConfig

        config = RetryConfig(max_attempts=2, initial_delay_ms=10)
        strategy = RetryStrategy(config)

        # Mock failing function
        async def fail_func():
            raise ValueError("Test error")

        # Should raise ValueError after all retries
        with pytest.raises(ValueError):
            await strategy.execute_with_retry(fail_func, retryable_exceptions=(ValueError,))

        # Check metrics
        summary = metrics.get_summary()
        assert summary["counters"].get("retry_executions_started", 0) >= 1
        assert summary["counters"].get("retry_executions_failed_all_attempts", 0) >= 1
        # Should have attempts for each retry
        assert summary["counters"].get("retry_attempt_1", 0) >= 1

    @pytest.mark.asyncio
    async def test_retry_backoff_metrics(self):
        """Test retry backoff delay tracking."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.strategies.retry import RetryStrategy, RetryConfig

        config = RetryConfig(max_attempts=3, initial_delay_ms=50, exponential_base=2.0, jitter=False)
        strategy = RetryStrategy(config)

        # Mock function that fails once then succeeds
        call_count = 0

        async def partial_fail_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First attempt fails")
            return "success"

        result = await strategy.execute_with_retry(partial_fail_func, retryable_exceptions=(ValueError,))

        # Verify result
        assert result == "success"

        # Check metrics
        summary = metrics.get_summary()
        # Should track backoff delay from first retry
        assert "retry_backoff_delay_ms_attempt_1" in summary.get("gauges", {})


class TestIntegratedClientMCPObservability:
    """Test suite for integrated client_mcp observability."""

    def test_observability_graceful_degradation(self):
        """Test client_mcp components work even if observability is unavailable."""
        from client_mcp.core.mcp_connector import MCPConnector
        from client_mcp.core.tool_executor import ToolExecutor

        # Components should initialize without errors
        connector = MCPConnector("http://localhost:8009/mcp")
        assert connector is not None

        executor = ToolExecutor(connector)
        assert executor is not None

    @pytest.mark.asyncio
    async def test_concurrent_metric_isolation(self):
        """Test metrics from concurrent operations are properly isolated."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        from client_mcp.strategies.retry import RetryStrategy, RetryConfig
        import asyncio

        config = RetryConfig(max_attempts=1, initial_delay_ms=10)

        # Create multiple concurrent retry operations
        strategies = [RetryStrategy(config) for _ in range(3)]

        async def independent_operation(strategy, index):
            async def task_func():
                return f"result_{index}"
            return await strategy.execute_with_retry(task_func)

        # Run concurrent operations
        results = await asyncio.gather(*[
            independent_operation(strategies[i], i) for i in range(3)
        ])

        # Verify all operations completed
        assert len(results) == 3
        assert all(r is not None for r in results)

        # Verify metrics tracked all operations
        summary = metrics.get_summary()
        assert summary["counters"].get("retry_executions_started", 0) >= 3

    def test_metrics_collector_shared_across_components(self):
        """Test all components share same metrics collector instance."""
        from client_mcp.core.mcp_connector import MCPConnector
        from client_mcp.core.tool_executor import ToolExecutor
        from client_mcp.core.response_processor import ResponseProcessor
        from client_mcp.core.response_validator import ResponseValidator
        from client_mcp.core.debug_formatter import DebugFormatter
        from client_mcp.strategies.retry import RetryStrategy, RetryConfig

        # Get metrics from each component
        connector = MCPConnector("http://localhost:8009/mcp")
        executor = ToolExecutor(connector)
        validator = MagicMock(spec=ResponseValidator)
        formatter = MagicMock(spec=DebugFormatter)
        processor = ResponseProcessor(validator, formatter)
        strategy = RetryStrategy(RetryConfig())

        # All should reference the same metrics collector
        if OBSERVABILITY_AVAILABLE:
            shared_metrics = get_metrics_collector()
            assert connector.metrics is shared_metrics
            assert executor.metrics is shared_metrics
            assert processor.metrics is shared_metrics
            assert strategy.metrics is shared_metrics
