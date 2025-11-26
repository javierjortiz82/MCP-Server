"""Metrics collection for performance monitoring.

Collects latency, throughput, and custom metrics across services.
Thread-safe implementation using contextvars for async operations.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import time
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from demo_agent.logger import logger


@dataclass
class Metric:
    """Single metric measurement.

    Attributes:
        name: Metric name (e.g., "token_bucket.check_quota")
        value: Metric value
        unit: Unit of measurement (e.g., "ms", "ops/sec")
        timestamp: When metric was recorded
        tags: Additional metadata (service, user_key, etc.)
    """

    name: str
    value: float
    unit: str = "ms"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
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
    """Collects and manages performance metrics.

    Provides methods to record latency, throughput, and custom metrics.
    Thread-safe for concurrent operations.

    Metrics tracked:
    - Latency: Operation duration in milliseconds
    - Throughput: Operations per second
    - Counters: Request counts, errors, etc.
    - Gauges: Current values (active connections, queue size)

    Example:
        >>> from demo_agent.observability.metrics import get_metrics_collector
        >>> metrics = get_metrics_collector()
        >>>
        >>> # Record latency using context manager
        >>> async with metrics.record_latency("token_bucket.check_quota"):
        ...     result = await bucket.check_quota(user_key, 100)
        >>>
        >>> # Get metrics summary
        >>> summary = metrics.get_summary()
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: list[Metric] = []
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        logger.info("MetricsCollector initialized")

    @contextmanager
    def record_latency(self, metric_name: str, tags: dict[str, str] | None = None):
        """Context manager to record operation latency (sync).

        Args:
            metric_name: Name of the operation
            tags: Optional metadata tags

        Yields:
            None

        Example:
            >>> metrics = get_metrics_collector()
            >>> with metrics.record_latency("my_operation", tags={"user": "123"}):
            ...     do_something()
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
        self, metric_name: str, tags: dict[str, str] | None = None
    ):
        """Context manager to record operation latency (async).

        Args:
            metric_name: Name of the operation
            tags: Optional metadata tags

        Yields:
            None

        Example:
            >>> metrics = get_metrics_collector()
            >>> async with metrics.record_latency_async("my_async_op"):
            ...     await do_something()
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
            counter_name: Name of the counter
            amount: Amount to increment (default 1)

        Example:
            >>> metrics = get_metrics_collector()
            >>> metrics.increment_counter("requests_total")
            >>> metrics.increment_counter("tokens_consumed", 250)
        """
        if counter_name not in self.counters:
            self.counters[counter_name] = 0
        self.counters[counter_name] += amount
        logger.debug(f"Counter: {counter_name}={self.counters[counter_name]}")

    def set_gauge(self, gauge_name: str, value: float) -> None:
        """Set a gauge metric (current value).

        Args:
            gauge_name: Name of the gauge
            value: Current value

        Example:
            >>> metrics = get_metrics_collector()
            >>> metrics.set_gauge("active_connections", 42)
            >>> metrics.set_gauge("queue_size", 10)
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

    def get_summary(self) -> dict[str, Any]:
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
                'counters': {...},
                'gauges': {...}
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

    def get_metrics_by_name(self, metric_name: str) -> list[Metric]:
        """Get all metrics with specific name.

        Args:
            metric_name: Name of metrics to retrieve

        Returns:
            List of metrics matching the name
        """
        return [m for m in self.metrics if m.name == metric_name]


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector.

    Returns:
        MetricsCollector instance

    Example:
        >>> from demo_agent.observability.metrics import get_metrics_collector
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
