"""Observability module for structured logging, correlation IDs, and metrics.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from demo_agent.observability.context import (
    RequestContext,
    get_request_context,
    set_request_context,
)
from demo_agent.observability.correlation import CorrelationID, generate_correlation_id
from demo_agent.observability.metrics import MetricsCollector, get_metrics_collector
from demo_agent.observability.structured_logger import StructuredLogger, get_structured_logger

__all__ = [
    "RequestContext",
    "get_request_context",
    "set_request_context",
    "CorrelationID",
    "generate_correlation_id",
    "MetricsCollector",
    "get_metrics_collector",
    "StructuredLogger",
    "get_structured_logger",
]
