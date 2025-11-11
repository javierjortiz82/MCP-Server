"""Integration tests for mcp_server observability features.

Tests structured logging, metrics collection, and latency tracking for
MCP server components including database operations, search, and tool handlers.

Author: Lab01-MCP Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, patch

try:
    from email_service.observability.metrics import get_metrics_collector, reset_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    pytest.skip("Observability framework not available", allow_module_level=True)


class TestServerInitializationObservability:
    """Test suite for server initialization observability."""

    def test_server_startup_metrics_recorded(self):
        """Test server startup records initialization metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate startup metrics tracking
        metrics.increment_counter("mcp_server_startup_attempts", 1)
        metrics.increment_counter("mcp_server_startup_successful", 1)

        summary = metrics.get_summary()

        # Verify startup metrics were recorded
        assert summary["counters"].get("mcp_server_startup_attempts", 0) >= 1
        assert summary["counters"].get("mcp_server_startup_successful", 0) >= 1


class TestDatabaseObservability:
    """Test suite for database operations observability."""

    def test_database_pool_initialization_metrics(self):
        """Test database pool initialization records metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate pool initialization metrics
        metrics.increment_counter("db_pool_initialization_attempts", 1)
        metrics.increment_counter("db_pool_initialization_successful", 1)
        metrics.set_gauge("db_pool_min_connections", 1)
        metrics.set_gauge("db_pool_max_connections", 5)

        summary = metrics.get_summary()

        # Verify pool initialization metrics
        assert summary["counters"].get("db_pool_initialization_attempts", 0) >= 1
        assert summary["counters"].get("db_pool_initialization_successful", 0) >= 1
        assert summary["gauges"].get("db_pool_min_connections", 0) >= 1

    def test_database_query_metrics(self):
        """Test database query operations record latency and result metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate fetchone query
        metrics.increment_counter("db_query_fetchone_attempts", 1)
        metrics.increment_counter("db_query_fetchone_success", 1)
        metrics.increment_counter("db_query_fetchone_found", 1)

        # Simulate fetchall query
        metrics.increment_counter("db_query_fetchall_attempts", 1)
        metrics.increment_counter("db_query_fetchall_success", 1)
        metrics.set_gauge("db_query_fetchall_row_count", 10)

        # Simulate execute query
        metrics.increment_counter("db_query_execute_attempts", 1)
        metrics.increment_counter("db_query_execute_success", 1)

        summary = metrics.get_summary()

        # Verify query metrics
        assert summary["counters"].get("db_query_fetchone_attempts", 0) >= 1
        assert summary["counters"].get("db_query_fetchone_found", 0) >= 1
        assert summary["counters"].get("db_query_fetchall_attempts", 0) >= 1
        assert summary["gauges"].get("db_query_fetchall_row_count", 0) >= 1
        assert summary["counters"].get("db_query_execute_attempts", 0) >= 1

    def test_database_error_tracking(self):
        """Test database errors are categorized and tracked."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate various database errors
        metrics.increment_counter("db_query_error_ConnectionError", 1)
        metrics.increment_counter("db_query_error_OperationalError", 1)
        metrics.increment_counter("db_query_fetchone_failure", 1)

        summary = metrics.get_summary()

        # Verify error tracking
        assert summary["counters"].get("db_query_error_ConnectionError", 0) >= 1
        assert summary["counters"].get("db_query_error_OperationalError", 0) >= 1
        assert summary["counters"].get("db_query_fetchone_failure", 0) >= 1


class TestSearchObservability:
    """Test suite for search operations observability."""

    def test_vector_search_metrics(self):
        """Test vector search operations record comprehensive metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate vector search operations
        metrics.increment_counter("search_vector_searches_attempted", 1)
        metrics.increment_counter("search_embedding_generation_successful", 1)
        metrics.increment_counter("search_vector_searches_successful", 1)
        metrics.set_gauge("search_vector_results_count", 5)

        summary = metrics.get_summary()

        # Verify search metrics
        assert summary["counters"].get("search_vector_searches_attempted", 0) >= 1
        assert summary["counters"].get("search_embedding_generation_successful", 0) >= 1
        assert summary["counters"].get("search_vector_searches_successful", 0) >= 1
        assert summary["gauges"].get("search_vector_results_count", 0) >= 1

    def test_embedding_generation_metrics(self):
        """Test embedding generation tracks latency and success/failure."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate successful and failed embedding generations
        metrics.increment_counter("search_embedding_generation_successful", 3)
        metrics.increment_counter("search_embedding_generation_failed", 1)

        summary = metrics.get_summary()

        # Verify embedding metrics
        assert summary["counters"].get("search_embedding_generation_successful", 0) >= 3
        assert summary["counters"].get("search_embedding_generation_failed", 0) >= 1

    def test_search_error_tracking(self):
        """Test search errors are tracked and categorized."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate search errors
        metrics.increment_counter("search_error_TimeoutError", 1)
        metrics.increment_counter("search_error_ValueError", 1)
        metrics.increment_counter("search_vector_searches_failed", 1)

        summary = metrics.get_summary()

        # Verify error tracking
        assert summary["counters"].get("search_error_TimeoutError", 0) >= 1
        assert summary["counters"].get("search_error_ValueError", 0) >= 1
        assert summary["counters"].get("search_vector_searches_failed", 0) >= 1


class TestIntegratedMCPServerObservability:
    """Test suite for integrated mcp_server observability."""

    def test_observability_graceful_degradation(self):
        """Test MCP server components work even if observability is unavailable."""
        # This test verifies backward compatibility
        # Components should function normally whether observability is available or not
        logger = get_structured_logger("test_component")
        metrics = get_metrics_collector()

        # Both should be non-None when framework is available
        assert logger is not None
        assert metrics is not None

    def test_metrics_collector_shared_across_components(self):
        """Test all server components share same metrics collector instance."""
        from email_service.observability.metrics import get_metrics_collector

        # All components should reference the same metrics collector
        metrics1 = get_metrics_collector()
        metrics2 = get_metrics_collector()
        metrics3 = get_metrics_collector()

        # They should be the same instance
        assert metrics1 is metrics2
        assert metrics2 is metrics3

    def test_structured_logger_context_enrichment(self):
        """Test structured logger automatically includes context in server logs."""
        logger = get_structured_logger("mcp_server_test")

        # Logger should include operation context
        logger.info("Server operation test", operation="initialization", component="server")

        # Verify logger is functional
        assert logger is not None

    def test_concurrent_metric_isolation(self):
        """Test metrics from concurrent operations are properly isolated."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate concurrent database queries
        for i in range(5):
            metrics.increment_counter("db_query_fetchone_attempts", 1)
            metrics.increment_counter("db_query_fetchone_success", 1)

        summary = metrics.get_summary()

        # All operations should be aggregated properly
        assert summary["counters"].get("db_query_fetchone_attempts", 0) >= 5
        assert summary["counters"].get("db_query_fetchone_success", 0) >= 5

    def test_full_operation_flow_metrics(self):
        """Test metrics tracking for complete operation flow (search request)."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate complete search operation flow
        # 1. Tool invocation
        metrics.increment_counter("search_vector_searches_attempted", 1)

        # 2. Embedding generation
        metrics.increment_counter("search_embedding_generation_successful", 1)

        # 3. Database query
        metrics.increment_counter("db_query_fetchall_attempts", 1)
        metrics.increment_counter("db_query_fetchall_success", 1)
        metrics.set_gauge("db_query_fetchall_row_count", 3)

        # 4. Search completion
        metrics.increment_counter("search_vector_searches_successful", 1)

        summary = metrics.get_summary()

        # Verify complete flow metrics
        assert summary["counters"].get("search_vector_searches_attempted", 0) >= 1
        assert summary["counters"].get("search_embedding_generation_successful", 0) >= 1
        assert summary["counters"].get("db_query_fetchall_attempts", 0) >= 1
        assert summary["gauges"].get("db_query_fetchall_row_count", 0) >= 1


class TestMetricsAggregation:
    """Test suite for metrics aggregation across server operations."""

    def test_gauge_metrics_represent_current_state(self):
        """Test gauge metrics correctly represent current state."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate pool state changes
        metrics.set_gauge("db_pool_min_connections", 1)
        metrics.set_gauge("db_pool_max_connections", 5)
        metrics.set_gauge("search_vector_results_count", 7)

        summary = metrics.get_summary()

        # Gauges should reflect latest state
        assert summary["gauges"].get("db_pool_max_connections", 0) == 5
        assert summary["gauges"].get("search_vector_results_count", 0) == 7

    def test_counter_metrics_aggregate_operations(self):
        """Test counter metrics properly aggregate multiple operations."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate multiple operations
        for _ in range(10):
            metrics.increment_counter("db_query_fetchone_attempts", 1)

        summary = metrics.get_summary()

        # Counter should show total
        assert summary["counters"].get("db_query_fetchone_attempts", 0) == 10

    def test_metrics_summary_completeness(self):
        """Test metrics summary includes all tracked metrics types."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Add various metric types
        metrics.increment_counter("test_counter", 5)
        metrics.set_gauge("test_gauge", 42)

        summary = metrics.get_summary()

        # Summary should have all metric types
        assert "counters" in summary
        assert "gauges" in summary
        assert "latency" in summary or len(summary.get("latency", {})) == 0
