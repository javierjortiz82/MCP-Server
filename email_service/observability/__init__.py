"""Observability module for email service - structured logging, correlation IDs, and metrics.

Provides consistent observability across email service components:
- Structured JSON logging with automatic context enrichment
- Correlation IDs for end-to-end request tracing
- Request/operation context with async-safe propagation
- Metrics collection (latency histograms, event counters, gauges)
- Audit trail logging for all operations

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from email_service.observability.context import (
    RequestContext,
    clear_request_context,
    create_request_context,
    get_request_context,
    set_request_context,
)
from email_service.observability.correlation import (
    CorrelationID,
    generate_correlation_id,
)
from email_service.observability.metrics import (
    MetricsCollector,
    get_metrics_collector,
    reset_metrics_collector,
)
from email_service.observability.structured_logger import (
    StructuredLogger,
    get_structured_logger,
)

__all__ = [
    "RequestContext",
    "get_request_context",
    "set_request_context",
    "clear_request_context",
    "create_request_context",
    "CorrelationID",
    "generate_correlation_id",
    "MetricsCollector",
    "get_metrics_collector",
    "reset_metrics_collector",
    "StructuredLogger",
    "get_structured_logger",
]
