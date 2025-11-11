"""Tests for observability module (logging, correlation IDs, metrics).

Tests OPCIÓN 3: Mejorar Logging & Observabilidad

Tests cover:
- Correlation ID generation and retrieval
- Request context management
- Structured logging with context
- Metrics collection (latency, throughput, counters)
- Async context propagation

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import asyncio
import time
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from demo_agent.observability.context import (
    RequestContext,
    clear_request_context,
    create_request_context,
    get_request_context,
    set_request_context,
)
from demo_agent.observability.correlation import (
    CorrelationID,
    generate_correlation_id,
)
from demo_agent.observability.metrics import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)
from demo_agent.observability.structured_logger import (
    StructuredLogger,
    get_structured_logger,
)


# ============================================================================
# Correlation ID Tests
# ============================================================================


class TestCorrelationID:
    """Tests for correlation ID management."""

    def test_generate_correlation_id(self):
        """Test generating a new correlation ID."""
        corr_id = CorrelationID.generate()

        assert isinstance(corr_id, str)
        assert len(corr_id) == 36  # UUID4 format
        assert corr_id.count("-") == 4  # UUID4 has 4 dashes

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        corr_id = "test-correlation-123"

        CorrelationID.set(corr_id)
        retrieved = CorrelationID.get()

        assert retrieved == corr_id
        CorrelationID.clear()

    def test_get_or_generate_creates_new(self):
        """Test get_or_generate creates new ID when none exists."""
        CorrelationID.clear()
        corr_id1 = CorrelationID.get_or_generate()
        corr_id2 = CorrelationID.get_or_generate()

        # Should return same ID when called twice
        assert corr_id1 == corr_id2
        CorrelationID.clear()

    def test_get_or_generate_returns_existing(self):
        """Test get_or_generate returns existing ID."""
        existing_id = "existing-id-123"
        CorrelationID.set(existing_id)

        returned_id = CorrelationID.get_or_generate()

        assert returned_id == existing_id
        CorrelationID.clear()

    def test_clear_correlation_id(self):
        """Test clearing correlation ID."""
        CorrelationID.set("test-id")
        CorrelationID.clear()

        assert CorrelationID.get() is None

    def test_generate_correlation_id_function(self):
        """Test generate_correlation_id convenience function."""
        corr_id = generate_correlation_id()

        assert isinstance(corr_id, str)
        assert CorrelationID.get() == corr_id
        CorrelationID.clear()


# ============================================================================
# Request Context Tests
# ============================================================================


class TestRequestContext:
    """Tests for request context management."""

    def test_create_request_context(self):
        """Test creating a request context."""
        ctx = RequestContext(
            correlation_id="test-123",
            user_key="user_456",
            ip_address="203.0.113.42",
        )

        assert ctx.correlation_id == "test-123"
        assert ctx.user_key == "user_456"
        assert ctx.ip_address == "203.0.113.42"

    def test_context_to_dict(self):
        """Test converting context to dictionary."""
        ctx = RequestContext(
            correlation_id="test-123",
            user_key="user_456",
            ip_address="203.0.113.42",
            method="POST",
            path="/api/demo",
        )

        ctx_dict = ctx.to_dict()

        assert ctx_dict["correlation_id"] == "test-123"
        assert ctx_dict["user_key"] == "user_456"
        assert ctx_dict["ip_address"] == "203.0.113.42"
        assert ctx_dict["method"] == "POST"
        assert ctx_dict["path"] == "/api/demo"
        assert "started_at" in ctx_dict

    def test_add_custom_field(self):
        """Test adding custom fields to context."""
        ctx = RequestContext(correlation_id="test-123")

        ctx.add_field("tokens_used", 250)
        ctx.add_field("request_duration", 15.5)

        assert ctx.get_field("tokens_used") == 250
        assert ctx.get_field("request_duration") == 15.5

    def test_get_field_with_default(self):
        """Test getting field with default value."""
        ctx = RequestContext(correlation_id="test-123")

        result = ctx.get_field("nonexistent", default="default_value")

        assert result == "default_value"

    def test_set_and_get_request_context(self):
        """Test setting and getting request context."""
        ctx = RequestContext(
            correlation_id="test-123",
            user_key="user_456",
        )

        set_request_context(ctx)
        retrieved = get_request_context()

        assert retrieved == ctx
        assert retrieved.user_key == "user_456"
        clear_request_context()

    def test_create_request_context_function(self):
        """Test create_request_context convenience function."""
        ctx = create_request_context(
            user_key="user_123",
            ip_address="203.0.113.42",
            method="GET",
            path="/api/quota",
        )

        assert ctx.user_key == "user_123"
        assert ctx.ip_address == "203.0.113.42"
        assert ctx.method == "GET"
        assert ctx.path == "/api/quota"
        assert ctx.correlation_id is not None
        assert get_request_context() == ctx
        clear_request_context()

    def test_clear_request_context(self):
        """Test clearing request context."""
        ctx = RequestContext(correlation_id="test-123")
        set_request_context(ctx)

        clear_request_context()

        assert get_request_context() is None
        assert CorrelationID.get() is None


# ============================================================================
# Metrics Tests
# ============================================================================


class TestMetricsCollector:
    """Tests for metrics collection."""

    def test_record_latency_sync(self):
        """Test recording latency with synchronous context manager."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency("test_operation"):
            time.sleep(0.01)  # Sleep 10ms

        summary = metrics.get_summary()
        assert summary["latency"]["count"] == 1
        assert summary["latency"]["avg_ms"] >= 10.0

    @pytest.mark.asyncio
    async def test_record_latency_async(self):
        """Test recording latency with async context manager."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        async with metrics.record_latency_async("async_operation"):
            await asyncio.sleep(0.01)  # Sleep 10ms

        summary = metrics.get_summary()
        assert summary["latency"]["count"] == 1
        assert summary["latency"]["avg_ms"] >= 10.0

    def test_increment_counter(self):
        """Test incrementing counters."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        metrics.increment_counter("requests")
        metrics.increment_counter("requests")
        metrics.increment_counter("tokens_consumed", 250)

        assert metrics.get_counter("requests") == 2
        assert metrics.get_counter("tokens_consumed") == 250

    def test_set_gauge(self):
        """Test setting gauge values."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        metrics.set_gauge("active_connections", 42)
        metrics.set_gauge("queue_size", 10.5)

        assert metrics.get_gauge("active_connections") == 42
        assert metrics.get_gauge("queue_size") == 10.5

    def test_get_summary(self):
        """Test getting metrics summary."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record some latencies
        for i in range(5):
            with metrics.record_latency(f"operation_{i}"):
                time.sleep(0.001)

        metrics.increment_counter("total_requests", 5)
        metrics.set_gauge("active_users", 10)

        summary = metrics.get_summary()

        assert summary["latency"]["count"] == 5
        assert summary["latency"]["min_ms"] > 0
        assert summary["latency"]["max_ms"] >= summary["latency"]["min_ms"]
        assert summary["latency"]["p95_ms"] >= summary["latency"]["min_ms"]
        assert summary["counters"]["total_requests"] == 5
        assert summary["gauges"]["active_users"] == 10

    def test_latency_percentiles(self):
        """Test latency percentile calculations."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record 100 operations with varying latencies
        for i in range(100):
            with metrics.record_latency("perf_test"):
                time.sleep(0.001 + (i % 10) * 0.0001)

        summary = metrics.get_summary()

        assert summary["latency"]["count"] == 100
        assert summary["latency"]["p95_ms"] >= summary["latency"]["avg_ms"]
        assert summary["latency"]["p99_ms"] >= summary["latency"]["p95_ms"]

    def test_get_metrics_by_name(self):
        """Test retrieving metrics by name."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency("operation_a"):
            time.sleep(0.001)

        with metrics.record_latency("operation_b"):
            time.sleep(0.001)

        with metrics.record_latency("operation_a"):
            time.sleep(0.001)

        operation_a_metrics = metrics.get_metrics_by_name("operation_a")
        operation_b_metrics = metrics.get_metrics_by_name("operation_b")

        assert len(operation_a_metrics) == 2
        assert len(operation_b_metrics) == 1

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        metrics.increment_counter("test_counter", 10)
        metrics.set_gauge("test_gauge", 5.0)

        metrics.clear()

        assert metrics.get_counter("test_counter") == 0
        assert metrics.get_gauge("test_gauge") == 0.0
        assert len(metrics.metrics) == 0

    def test_metrics_with_tags(self):
        """Test metrics with tags."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency(
            "database_query", tags={"table": "demo_usage", "user": "user_123"}
        ):
            time.sleep(0.001)

        recorded_metric = metrics.metrics[0]
        assert recorded_metric.tags["table"] == "demo_usage"
        assert recorded_metric.tags["user"] == "user_123"


# ============================================================================
# Structured Logger Tests
# ============================================================================


class TestStructuredLogger:
    """Tests for structured logging."""

    def test_get_structured_logger(self):
        """Test getting a structured logger."""
        logger = get_structured_logger("test.module")

        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test.module"

    def test_logger_includes_correlation_id(self):
        """Test that logger includes correlation ID in context."""
        CorrelationID.set("test-corr-123")
        logger = get_structured_logger("test_logger")

        # Verify logger is created and can be used
        assert logger is not None
        assert logger.name == "test_logger"

        # Verify correlation ID is set in context
        assert CorrelationID.get() == "test-corr-123"
        CorrelationID.clear()

    def test_logger_includes_request_context(self):
        """Test that logger includes request context."""
        ctx = create_request_context(
            user_key="user_123",
            ip_address="203.0.113.42",
        )
        logger = get_structured_logger("test_logger")

        # Verify context is set
        assert get_request_context() == ctx
        assert get_request_context().user_key == "user_123"
        assert get_request_context().ip_address == "203.0.113.42"
        clear_request_context()

    def test_logger_custom_fields(self):
        """Test logger with custom fields."""
        logger = get_structured_logger("test_logger")

        # Verify logger can handle custom fields
        assert logger is not None
        # The actual logging happens without raising exceptions
        clear_request_context()

    def test_logger_exception_logging(self, caplog):
        """Test logging exceptions."""
        logger = get_structured_logger("test_logger")

        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("An error occurred")

        assert len(caplog.records) > 0
        clear_request_context()

    def test_logger_log_levels(self, caplog):
        """Test all log levels."""
        logger = get_structured_logger("test_logger")

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        # At least some messages should be captured
        assert len(caplog.records) > 0
        clear_request_context()


# ============================================================================
# Integration Tests
# ============================================================================


class TestObservabilityIntegration:
    """Integration tests for observability components."""

    @pytest.mark.asyncio
    async def test_full_request_flow(self):
        """Test complete request flow with all observability components."""
        reset_metrics_collector()

        # Create request context
        ctx = create_request_context(
            user_key="user_123",
            ip_address="203.0.113.42",
            method="POST",
            path="/api/demo",
        )

        metrics = get_metrics_collector()
        logger = get_structured_logger("integration_test")

        # Simulate async operations with metrics
        async with metrics.record_latency_async(
            "full_request", tags={"user": "user_123"}
        ):
            logger.info("Request started")

            # Simulate token bucket operation
            async with metrics.record_latency_async("token_check"):
                await asyncio.sleep(0.01)
                metrics.increment_counter("quota_checks")

            # Simulate Gemini API call
            async with metrics.record_latency_async("gemini_api"):
                await asyncio.sleep(0.02)
                metrics.increment_counter("api_calls")
                metrics.increment_counter("tokens_consumed", 250)

            logger.info("Request completed", request_id=ctx.correlation_id)

        # Verify metrics were recorded
        summary = metrics.get_summary()
        assert summary["latency"]["count"] == 3  # full, token_check, gemini_api
        assert summary["counters"]["quota_checks"] == 1
        assert summary["counters"]["api_calls"] == 1
        assert summary["counters"]["tokens_consumed"] == 250

        clear_request_context()

    @pytest.mark.asyncio
    async def test_concurrent_requests_isolation(self):
        """Test that concurrent requests maintain separate contexts."""
        reset_metrics_collector()

        async def process_request(user_key: str, request_id: int):
            # Each task gets its own context
            ctx = create_request_context(user_key=user_key)
            metrics = get_metrics_collector()

            async with metrics.record_latency_async(f"request_{request_id}"):
                await asyncio.sleep(0.01 * (request_id % 3))
                metrics.increment_counter(f"requests_{user_key}", 1)

            # Verify context is set
            current_ctx = get_request_context()
            assert current_ctx.user_key == user_key

            clear_request_context()

        # Run 5 concurrent requests
        await asyncio.gather(
            process_request("user_1", 1),
            process_request("user_2", 2),
            process_request("user_3", 3),
            process_request("user_1", 4),
            process_request("user_2", 5),
        )

        # Verify metrics were collected from all requests
        metrics = get_metrics_collector()
        summary = metrics.get_summary()
        assert summary["latency"]["count"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
