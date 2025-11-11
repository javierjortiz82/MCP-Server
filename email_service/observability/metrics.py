"""Metrics collection for email service performance monitoring.

Collects latency, throughput, and custom metrics across email service operations.
Thread-safe implementation using contextvars for async operations.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """Single metric measurement.

    Attributes:
        name: Metric name (e.g., "email_send", "smtp_connection")
        value: Metric value (usually latency in ms)
        unit: Unit of measurement (e.g., "ms", "ops/sec")
        timestamp: When metric was recorded
        tags: Additional metadata (email_id, recipient, operation, etc.)
    """

    name: str
    value: float
    unit: str = "ms"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
        }


class MetricsCollector:
    """Collects and manages email service performance metrics.

    Provides methods to record latency, throughput, and custom metrics.
    Thread-safe for concurrent operations.

    Metrics tracked:
    - Latency: Operation duration in milliseconds
    - Throughput: Operations per second
    - Counters: Email counts, errors, retries, etc.
    - Gauges: Current values (queue size, active processes)

    Example:
        >>> from email_service.observability.metrics import get_metrics_collector
        >>> metrics = get_metrics_collector()
        >>>
        >>> # Record latency using context manager
        >>> async with metrics.record_latency_async("email_send", tags={"recipient": "user@example.com"}):
        ...     result = await smtp_client.send_email(...)
        >>>
        >>> # Get metrics summary
        >>> summary = metrics.get_summary()
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[Metric] = []
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        logger.info("MetricsCollector initialized for email_service")

    @contextmanager
    def record_latency(self, metric_name: str, tags: Optional[Dict[str, str]] = None):
        """Context manager to record operation latency (sync).

        Args:
            metric_name: Name of the operation (e.g., "template_render")
            tags: Optional metadata tags (email_id, operation, etc.)

        Yields:
            None

        Example:
            >>> metrics = get_metrics_collector()
            >>> with metrics.record_latency("smtp_connect", tags={"host": "smtp.gmail.com"}):
            ...     client.connect()
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            metric = Metric(
                name=metric_name,
                value=elapsed,
                unit="ms",
                tags=tags or {},
            )
            self.metrics.append(metric)
            logger.debug(f"Metric recorded: {metric_name}={elapsed:.2f}ms")

    @asynccontextmanager
    async def record_latency_async(
        self, metric_name: str, tags: Optional[Dict[str, str]] = None
    ):
        """Context manager to record operation latency (async).

        Args:
            metric_name: Name of the operation (e.g., "email_send")
            tags: Optional metadata tags (recipient, email_id, etc.)

        Yields:
            None

        Example:
            >>> metrics = get_metrics_collector()
            >>> async with metrics.record_latency_async("email_send", tags={"recipient": "user@example.com"}):
            ...     await send_email(...)
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms
            metric = Metric(
                name=metric_name,
                value=elapsed,
                unit="ms",
                tags=tags or {},
            )
            self.metrics.append(metric)
            logger.debug(f"Metric recorded: {metric_name}={elapsed:.2f}ms")

    def increment_counter(self, counter_name: str, amount: int = 1) -> None:
        """Increment a counter metric.

        Args:
            counter_name: Name of the counter (e.g., "emails_sent", "retries")
            amount: Amount to increment (default 1)

        Example:
            >>> metrics = get_metrics_collector()
            >>> metrics.increment_counter("emails_sent")
            >>> metrics.increment_counter("emails_failed", 1)
        """
        if counter_name not in self.counters:
            self.counters[counter_name] = 0
        self.counters[counter_name] += amount
        logger.debug(f"Counter: {counter_name}={self.counters[counter_name]}")

    def set_gauge(self, gauge_name: str, value: float) -> None:
        """Set a gauge metric (current value).

        Args:
            gauge_name: Name of the gauge (e.g., "queue_size", "active_workers")
            value: Current value

        Example:
            >>> metrics = get_metrics_collector()
            >>> metrics.set_gauge("queue_size", 42)
            >>> metrics.set_gauge("active_workers", 5)
        """
        self.gauges[gauge_name] = value
        logger.debug(f"Gauge: {gauge_name}={value}")

    def get_gauge(self, gauge_name: str, default: float = 0.0) -> float:
        """Get current gauge value.

        Args:
            gauge_name: Name of the gauge
            default: Default value if not set

        Returns:
            Current gauge value or default
        """
        return self.gauges.get(gauge_name, default)

    def get_counter(self, counter_name: str, default: int = 0) -> int:
        """Get current counter value.

        Args:
            counter_name: Name of the counter
            default: Default value if not set

        Returns:
            Current counter value or default
        """
        return self.counters.get(counter_name, default)

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary.

        Returns:
            Dictionary with latency stats, counters, and gauges

        Example:
            >>> metrics = get_metrics_collector()
            >>> summary = metrics.get_summary()
            >>> print(summary)
            {
                'latency': {
                    'avg_ms': 15.5,
                    'min_ms': 5.2,
                    'max_ms': 42.1,
                    'p95_ms': 25.0,
                    'p99_ms': 35.0,
                },
                'counters': {'emails_sent': 100, 'emails_failed': 2},
                'gauges': {'queue_size': 42}
            }
        """
        if not self.metrics:
            return {
                "latency": {
                    "count": 0,
                    "avg_ms": 0.0,
                    "min_ms": 0.0,
                    "max_ms": 0.0,
                },
                "counters": self.counters,
                "gauges": self.gauges,
            }

        # Calculate latency statistics
        values = sorted([m.value for m in self.metrics])
        count = len(values)
        avg = sum(values) / count
        min_val = values[0]
        max_val = values[-1]
        p95_idx = int(count * 0.95)
        p99_idx = int(count * 0.99)
        p95 = values[p95_idx] if p95_idx < count else values[-1]
        p99 = values[p99_idx] if p99_idx < count else values[-1]

        return {
            "latency": {
                "count": count,
                "avg_ms": round(avg, 2),
                "min_ms": round(min_val, 2),
                "max_ms": round(max_val, 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(p99, 2),
            },
            "counters": self.counters,
            "gauges": self.gauges,
        }

    def clear(self) -> None:
        """Clear all metrics (useful for tests).

        Example:
            >>> metrics = get_metrics_collector()
            >>> metrics.clear()
        """
        self.metrics.clear()
        self.counters.clear()
        self.gauges.clear()
        logger.debug("All metrics cleared")

    def get_metrics_by_name(self, metric_name: str) -> List[Metric]:
        """Get all metrics with specific name.

        Args:
            metric_name: Name of metrics to retrieve

        Returns:
            List of metrics matching the name
        """
        return [m for m in self.metrics if m.name == metric_name]


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector.

    Returns:
        MetricsCollector instance

    Example:
        >>> from email_service.observability.metrics import get_metrics_collector
        >>> metrics = get_metrics_collector()
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics_collector() -> None:
    """Reset global metrics collector (mainly for testing)."""
    global _metrics_collector
    _metrics_collector = None
