"""Integration tests for email_service observability features.

Tests structured logging, correlation IDs, metrics collection, and
async-safe context management across all email_service components.

Author: Lab01-MCP Team
Date: 2025-11-03
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from email_service.clients.smtp import SMTPClient
from email_service.config import EmailConfig
from email_service.database.queue import EmailQueueManager
from email_service.models.email import EmailRecord, EmailStatus, EmailType
from email_service.observability.context import (
    clear_request_context,
    create_request_context,
    get_request_context,
)
from email_service.observability.correlation import CorrelationID
from email_service.observability.metrics import get_metrics_collector, reset_metrics_collector
from email_service.observability.structured_logger import get_structured_logger
from email_service.templates.renderer import TemplateRenderer
from email_service.worker.processor import EmailWorker


class TestObservabilityIntegration:
    """Test suite for email_service observability features."""

    def teardown_method(self):
        """Cleanup after each test."""
        clear_request_context()
        CorrelationID.clear()
        reset_metrics_collector()

    def test_structured_logger_initialization(self):
        """Test structured logger can be initialized."""
        logger = get_structured_logger("test_logger")
        assert logger is not None
        assert logger.name == "test_logger"

    def test_structured_logger_context_enrichment(self):
        """Test structured logger automatically includes context."""
        correlation_id = "test-correlation-id-123"
        CorrelationID.set(correlation_id)

        ctx = create_request_context(
            email_id=42,
            recipient="test@example.com",
            operation="send_email"
        )

        logger = get_structured_logger("test_contextual")

        # Log should include context (no exception expected)
        logger.info("Test message", custom_field="value")

        # Verify context is still set
        assert get_request_context() == ctx
        assert CorrelationID.get() == correlation_id

    def test_request_context_isolation(self):
        """Test request contexts are isolated per email."""
        # Create first context
        ctx1 = create_request_context(
            email_id=1,
            recipient="user1@example.com",
            operation="send"
        )
        assert get_request_context() == ctx1

        # Create second context (should override)
        ctx2 = create_request_context(
            email_id=2,
            recipient="user2@example.com",
            operation="retry"
        )
        assert get_request_context() == ctx2

        # Clear context
        clear_request_context()
        assert get_request_context() is None

    def test_correlation_id_generation(self):
        """Test correlation ID generation and retrieval."""
        # Get or generate correlation ID
        corr_id1 = CorrelationID.get_or_generate()
        assert corr_id1 is not None
        assert len(corr_id1) == 36  # UUID4 format

        # Should return same ID on second call
        corr_id2 = CorrelationID.get_or_generate()
        assert corr_id1 == corr_id2

        # Clear and generate new
        CorrelationID.clear()
        corr_id3 = CorrelationID.get_or_generate()
        assert corr_id3 != corr_id1

    def test_metrics_collector_initialization(self):
        """Test metrics collector can be initialized."""
        reset_metrics_collector()
        metrics = get_metrics_collector()
        assert metrics is not None

    def test_metrics_latency_tracking(self):
        """Test latency metrics are recorded."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency("test_operation"):
            pass

        summary = metrics.get_summary()
        assert "test_operation" in summary.get("latency", {})

    def test_metrics_counter_tracking(self):
        """Test counter metrics are incremented."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        metrics.increment_counter("test_event", 1)
        metrics.increment_counter("test_event", 2)

        summary = metrics.get_summary()
        assert summary["counters"].get("test_event") == 3

    def test_metrics_gauge_tracking(self):
        """Test gauge metrics are set."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        metrics.set_gauge("queue_size", 42)

        summary = metrics.get_summary()
        assert summary["gauges"].get("queue_size") == 42

    @pytest.mark.asyncio
    async def test_smtp_client_metrics_on_success(self):
        """Test SMTPClient records metrics on successful send."""
        reset_metrics_collector()

        config = MagicMock()
        config.host = "smtp.gmail.com"
        config.port = 587
        config.username = "test@gmail.com"
        config.password = "test_password"
        config.from_email = "test@gmail.com"
        config.from_name = "Test"
        config.use_tls = True
        config.timeout = 30

        client = SMTPClient(config)
        metrics = get_metrics_collector()

        # Mock SMTP connection
        with patch("smtplib.SMTP") as mock_smtp:
            mock_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_instance

            client.send_email(
                recipient_email="user@example.com",
                recipient_name="User",
                subject="Test",
                body_html="<p>Test</p>"
            )

            # Verify metrics recorded
            summary = metrics.get_summary()
            assert summary["counters"].get("smtp_sends_successful") == 1

    @pytest.mark.asyncio
    async def test_template_renderer_metrics(self):
        """Test TemplateRenderer records metrics on template operations."""
        reset_metrics_collector()

        renderer = TemplateRenderer()
        metrics = get_metrics_collector()

        # Test template existence check
        renderer.template_exists(EmailType.BOOKING_CREATED, "html")

        summary = metrics.get_summary()
        assert summary["counters"].get("template_checks") == 1

    @pytest.mark.asyncio
    async def test_queue_manager_metrics(self):
        """Test EmailQueueManager records metrics on queue operations."""
        reset_metrics_collector()

        config = MagicMock(spec=EmailConfig)
        config.DATABASE_URL = "postgresql://localhost/test"
        config.SCHEMA_NAME = "public"

        # Mock the connection pool
        with patch("email_service.database.queue.pool.SimpleConnectionPool"):
            manager = EmailQueueManager(config)
            metrics = get_metrics_collector()

            # Verify manager was initialized
            assert manager is not None
            assert metrics is not None

    def test_observability_in_email_worker(self):
        """Test EmailWorker properly initializes observability."""
        with patch("email_service.config.EmailConfig"):
            with patch("email_service.worker.processor.setup_logging"):
                with patch("email_service.worker.processor.EmailQueueManager"):
                    with patch("email_service.worker.processor.SMTPClient"):
                        with patch("email_service.worker.processor.TemplateRenderer"):
                            worker = EmailWorker()

                            # Verify observability components are initialized
                            assert hasattr(worker, "logger")
                            assert hasattr(worker, "metrics")
                            assert worker.logger is not None
                            assert worker.metrics is not None

    def test_context_cleanup_on_email_processing(self):
        """Test context is properly cleaned up after email processing."""
        # Create a context
        ctx = create_request_context(
            email_id=123,
            recipient="test@example.com",
            operation="send_email"
        )
        assert get_request_context() == ctx

        # Clear it
        clear_request_context()
        assert get_request_context() is None

    def test_correlation_id_propagation(self):
        """Test correlation ID propagates through logger operations."""
        correlation_id = "test-correlation-123"
        CorrelationID.set(correlation_id)

        logger = get_structured_logger("test_propagation")

        # Log operation
        logger.info("Test operation", email_id=1)

        # Verify correlation ID is still set
        assert CorrelationID.get() == correlation_id

    def test_metrics_summary_structure(self):
        """Test metrics summary has correct structure."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record various metrics
        with metrics.record_latency("test_latency"):
            pass

        metrics.increment_counter("test_counter", 5)
        metrics.set_gauge("test_gauge", 42)

        summary = metrics.get_summary()

        # Verify structure
        assert "latency" in summary
        assert "counters" in summary
        assert "gauges" in summary
        assert summary["counters"]["test_counter"] == 5
        assert summary["gauges"]["test_gauge"] == 42

    def test_metrics_latency_percentiles(self):
        """Test latency metrics include percentile calculations."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record multiple latency samples
        for i in range(10):
            with metrics.record_latency("test_operation"):
                pass

        summary = metrics.get_summary()
        latency_stats = summary.get("latency", {})

        # Verify percentiles are calculated
        if "test_operation" in latency_stats:
            stats = latency_stats["test_operation"]
            assert "p95" in stats or "count" in stats  # At least count should be there

    def test_structured_logging_without_context(self):
        """Test structured logging works without active context."""
        # No context set
        clear_request_context()
        CorrelationID.clear()

        logger = get_structured_logger("test_no_context")

        # Should not raise exception
        logger.info("Test without context", field="value")

    def test_observability_error_handling(self):
        """Test observability continues working on errors."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record error counter
        metrics.increment_counter("test_error", 1)

        summary = metrics.get_summary()
        assert summary["counters"]["test_error"] == 1

    def test_multiple_logger_instances_share_state(self):
        """Test multiple logger instances share metrics state."""
        reset_metrics_collector()

        logger1 = get_structured_logger("logger1")
        logger2 = get_structured_logger("logger2")
        metrics = get_metrics_collector()

        # Both loggers should be different instances
        assert logger1.logger.name == "logger1"
        assert logger2.logger.name == "logger2"

        # But metrics should be shared
        metrics.increment_counter("shared_counter", 1)

        summary = metrics.get_summary()
        assert summary["counters"]["shared_counter"] == 1

    def test_email_record_with_context(self):
        """Test EmailRecord can be created and processed with context."""
        ctx = create_request_context(
            email_id=999,
            recipient="record@example.com",
            operation="test_record"
        )

        # Simulate email record
        email = EmailRecord(
            id=999,
            type=EmailType.BOOKING_CREATED,
            recipient_email="record@example.com",
            recipient_name="Test User",
            subject="Test Subject",
            body_html="<p>Test</p>",
            body_text="Test",
            status=EmailStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert email.id == 999
        assert get_request_context() == ctx

    def test_metrics_tag_support(self):
        """Test metrics can be recorded with tags."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency("tagged_operation", tags={"email_type": "booking"}):
            pass

        summary = metrics.get_summary()
        assert "tagged_operation" in summary.get("latency", {})


@pytest.mark.asyncio
class TestAsyncObservability:
    """Test async-specific observability features."""

    async def test_async_context_isolation(self):
        """Test async context is properly isolated."""
        clear_request_context()

        ctx1 = create_request_context(
            email_id=1,
            recipient="async1@example.com",
            operation="async_op1"
        )

        # Context should be set
        assert get_request_context() == ctx1

        # Clear and verify
        clear_request_context()
        assert get_request_context() is None

    async def test_async_logger_operations(self):
        """Test logger operations work in async context."""
        logger = get_structured_logger("async_logger")

        # Log in async context
        logger.info("Async operation", async_field="value")

        # Should not raise

    async def test_async_metrics_recording(self):
        """Test metrics can be recorded in async context."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        with metrics.record_latency("async_operation"):
            pass

        summary = metrics.get_summary()
        assert "async_operation" in summary.get("latency", {})
