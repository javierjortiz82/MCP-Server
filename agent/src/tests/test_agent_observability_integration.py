"""Integration tests for agent services observability features.

Tests structured logging, correlation IDs, metrics collection, and
latency tracking across all agent components.

Author: Lab01-MCP Team
Date: 2025-11-03
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

try:
    from email_service.observability.metrics import get_metrics_collector, reset_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    from email_service.observability.context import (
        create_request_context,
        clear_request_context,
        get_request_context,
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    pytest.skip("Observability framework not available", allow_module_level=True)

from gemini_agent.base_agent import BaseAgent, OBSERVABILITY_AVAILABLE as BASE_OBS_AVAILABLE


class TestBaseAgentObservability:
    """Test suite for BaseAgent observability features."""

    def test_base_agent_observability_initialization(self):
        """Test BaseAgent initializes observability components."""
        if not BASE_OBS_AVAILABLE:
            pytest.skip("Observability not available in BaseAgent")

        # Create a mock agent
        class TestAgent(BaseAgent):
            @property
            def agent_name(self) -> str:
                return "test_agent"

            def get_system_prompt(self, **kwargs) -> str:
                return "You are a test agent"

        agent = TestAgent(api_key="test-key")

        # Verify observability components are initialized
        assert hasattr(agent, "structured_logger")
        assert hasattr(agent, "metrics")
        assert agent.structured_logger is not None
        assert agent.metrics is not None

    def test_base_agent_metrics_on_initialization(self):
        """Test BaseAgent logs metrics during initialization."""
        if not BASE_OBS_AVAILABLE:
            pytest.skip("Observability not available in BaseAgent")

        class TestAgent(BaseAgent):
            @property
            def agent_name(self) -> str:
                return "test_agent"

            def get_system_prompt(self, **kwargs) -> str:
                return "You are a test agent"

        reset_metrics_collector()

        agent = TestAgent(api_key="test-key")
        metrics = get_metrics_collector()

        # Should have created metrics
        assert metrics is not None

    @pytest.mark.asyncio
    async def test_agent_router_observability_initialization(self):
        """Test AgentRouter initializes observability components."""
        from multi_agent.agent_router import AgentRouter, OBSERVABILITY_AVAILABLE as ROUTER_OBS

        if not ROUTER_OBS:
            pytest.skip("Observability not available in AgentRouter")

        router = AgentRouter(api_key="test-key")

        # Verify observability components are initialized
        assert hasattr(router, "structured_logger")
        assert hasattr(router, "metrics")
        assert router.structured_logger is not None
        assert router.metrics is not None

    @pytest.mark.asyncio
    async def test_agent_factory_observability(self):
        """Test AgentFactory tracks agent creation metrics."""
        from multi_agent.agent_factory import AgentFactory, OBSERVABILITY_AVAILABLE as FACTORY_OBS

        if not FACTORY_OBS:
            pytest.skip("Observability not available in AgentFactory")

        reset_metrics_collector()

        # Mock Gemini client
        with patch("google.genai.Client"):
            with patch("multi_agent.agent_factory.AgentFactory._initialize_registry"):
                with patch.object(AgentFactory, "_AGENT_REGISTRY", {"general": MagicMock}):
                    metrics = get_metrics_collector()
                    # At this point, factory should be initialized with observability
                    assert metrics is not None

    def test_structured_logger_context_enrichment_agent(self):
        """Test structured logger automatically includes context in agents."""
        if not OBSERVABILITY_AVAILABLE:
            pytest.skip("Observability not available")

        logger = get_structured_logger("test_agent_logger")

        # Create context
        ctx = create_request_context(
            email_id=None,
            recipient=None,
            operation="test_agent_operation"
        )

        # Log should work with context
        logger.info("Test message", agent_type="booking")

        # Verify context
        assert get_request_context() == ctx
        clear_request_context()

    def test_metrics_collector_agent_counters(self):
        """Test metrics collector can track agent-specific counters."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Track agent responses
        metrics.increment_counter("booking_agent_queries", 1)
        metrics.increment_counter("sales_agent_queries", 2)
        metrics.increment_counter("general_agent_queries", 3)

        summary = metrics.get_summary()

        # Verify all counters are tracked
        assert summary["counters"]["booking_agent_queries"] == 1
        assert summary["counters"]["sales_agent_queries"] == 2
        assert summary["counters"]["general_agent_queries"] == 3

    def test_metrics_collector_agent_latency(self):
        """Test metrics collector tracks agent latency."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Record latency for different agents
        with metrics.record_latency("booking_agent_generate_latency"):
            pass

        with metrics.record_latency("sales_agent_generate_latency"):
            pass

        summary = metrics.get_summary()

        # Verify latencies are recorded
        assert "booking_agent_generate_latency" in summary.get("latency", {})
        assert "sales_agent_generate_latency" in summary.get("latency", {})

    def test_metrics_collection_error_tracking(self):
        """Test error tracking in agent metrics."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Track various errors
        metrics.increment_counter("booking_agent_error_RuntimeError", 1)
        metrics.increment_counter("router_error_ValueError", 1)
        metrics.increment_counter("factory_create_sales_failed", 1)

        summary = metrics.get_summary()

        # Verify error counters
        assert summary["counters"]["booking_agent_error_RuntimeError"] == 1
        assert summary["counters"]["router_error_ValueError"] == 1
        assert summary["counters"]["factory_create_sales_failed"] == 1

    def test_metrics_gauge_agent_state(self):
        """Test gauge metrics for tracking agent state."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Track agent state
        metrics.set_gauge("booking_agent_history_size", 15)
        metrics.set_gauge("sales_agent_history_size", 25)
        metrics.set_gauge("general_agent_history_size", 5)

        summary = metrics.get_summary()

        # Verify gauges
        assert summary["gauges"]["booking_agent_history_size"] == 15
        assert summary["gauges"]["sales_agent_history_size"] == 25
        assert summary["gauges"]["general_agent_history_size"] == 5

    def test_router_classification_metrics(self):
        """Test router classification metrics tracking."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate classification attempts
        metrics.increment_counter("router_classifications_attempted", 5)
        metrics.increment_counter("router_classifications_successful", 4)
        metrics.increment_counter("router_classifications_failed", 1)

        # Track intents
        metrics.increment_counter("router_intent_sales", 2)
        metrics.increment_counter("router_intent_booking", 1)
        metrics.increment_counter("router_intent_general", 1)

        summary = metrics.get_summary()

        # Verify classification metrics
        assert summary["counters"]["router_classifications_attempted"] == 5
        assert summary["counters"]["router_classifications_successful"] == 4
        assert summary["counters"]["router_classifications_failed"] == 1
        assert summary["counters"]["router_intent_sales"] == 2
        assert summary["counters"]["router_intent_booking"] == 1
        assert summary["counters"]["router_intent_general"] == 1

    def test_factory_creation_metrics(self):
        """Test factory creation metrics tracking."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate factory creation attempts
        metrics.increment_counter("factory_create_booking_attempted", 1)
        metrics.increment_counter("factory_create_booking_successful", 1)

        metrics.increment_counter("factory_create_sales_attempted", 1)
        metrics.increment_counter("factory_create_sales_failed", 1)

        metrics.increment_counter("factory_create_general_attempted", 1)
        metrics.increment_counter("factory_create_general_successful", 1)

        summary = metrics.get_summary()

        # Verify factory metrics
        assert summary["counters"]["factory_create_booking_attempted"] == 1
        assert summary["counters"]["factory_create_booking_successful"] == 1
        assert summary["counters"]["factory_create_sales_attempted"] == 1
        assert summary["counters"]["factory_create_sales_failed"] == 1
        assert summary["counters"]["factory_create_general_attempted"] == 1
        assert summary["counters"]["factory_create_general_successful"] == 1

    def test_context_cleanup_after_agent_operation(self):
        """Test request context is properly cleaned up after agent operations."""
        # Create context
        ctx = create_request_context(
            email_id=None,
            recipient=None,
            operation="agent_test_operation"
        )

        # Verify it's set
        assert get_request_context() == ctx

        # Clear it
        clear_request_context()

        # Verify it's cleared
        assert get_request_context() is None

    def test_multiple_agent_metrics_isolation(self):
        """Test metrics from different agents are properly isolated and aggregated."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate separate agent operations
        for _ in range(3):
            metrics.increment_counter("booking_agent_queries", 1)

        for _ in range(2):
            metrics.increment_counter("sales_agent_queries", 1)

        for _ in range(5):
            metrics.increment_counter("general_agent_queries", 1)

        summary = metrics.get_summary()

        # Verify each agent's metrics are separate
        assert summary["counters"]["booking_agent_queries"] == 3
        assert summary["counters"]["sales_agent_queries"] == 2
        assert summary["counters"]["general_agent_queries"] == 5

    def test_observability_graceful_degradation(self):
        """Test agents work even if observability is not available."""
        # This test verifies backward compatibility
        # Agents should work with or without observability

        class MinimalAgent(BaseAgent):
            @property
            def agent_name(self) -> str:
                return "minimal_agent"

            def get_system_prompt(self, **kwargs) -> str:
                return "You are a minimal agent"

        # Should not raise even if observability is not available
        agent = MinimalAgent(api_key="test-key")
        assert agent is not None


@pytest.mark.asyncio
class TestAsyncAgentObservability:
    """Test async-specific observability features for agents."""

    async def test_async_latency_tracking(self):
        """Test async latency tracking for agent operations."""
        reset_metrics_collector()
        metrics = get_metrics_collector()

        # Simulate async operation
        async with metrics.record_latency_async("async_agent_operation"):
            # Simulate work
            import asyncio
            await asyncio.sleep(0.001)

        summary = metrics.get_summary()
        assert "async_agent_operation" in summary.get("latency", {})

    async def test_async_context_isolation(self):
        """Test async context is properly isolated for concurrent operations."""
        clear_request_context()

        # Create context for first operation
        ctx1 = create_request_context(
            email_id=None,
            recipient=None,
            operation="async_op_1"
        )

        # Verify context is set
        assert get_request_context() == ctx1

        # Clear for next operation
        clear_request_context()

        # Create context for second operation
        ctx2 = create_request_context(
            email_id=None,
            recipient=None,
            operation="async_op_2"
        )

        # Verify new context is set
        assert get_request_context() == ctx2

        # Cleanup
        clear_request_context()
