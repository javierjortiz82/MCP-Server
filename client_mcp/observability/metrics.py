"""Metrics collection for MCP tool executions.

This module tracks execution metrics for MCP tools including:
- Execution time
- Success/failure rates
- Parameter usage
- Error tracking
"""

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ToolMetric:
    """Metric for a single tool execution."""

    tool_name: str
    execution_time_ms: float
    success: bool
    parameters: dict[str, Any]
    result_size: int  # Number of items if list, 1 if dict, 0 if None
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: str | None = None
    user_query: str | None = None  # Original user query that triggered this

    def to_dict(self) -> dict[str, Any]:
        """Convert metric to dictionary with serializable types."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collector for MCP tool execution metrics.

    Provides real-time metrics collection, aggregation, and export capabilities.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self._metrics: list[ToolMetric] = []
        self._aggregated_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_execution_time_ms": 0.0,
                "avg_execution_time_ms": 0.0,
                "min_execution_time_ms": float("inf"),
                "max_execution_time_ms": 0.0,
                "errors": [],
            }
        )

    def record_execution(self, metric: ToolMetric) -> None:
        """Record a tool execution metric.

        Args:
            metric: Tool execution metric to record
        """
        self._metrics.append(metric)
        self._update_aggregated_stats(metric)

    def _update_aggregated_stats(self, metric: ToolMetric) -> None:
        """Update aggregated statistics with new metric.

        Args:
            metric: New metric to include in stats
        """
        stats = self._aggregated_stats[metric.tool_name]

        stats["total_calls"] += 1

        if metric.success:
            stats["successful_calls"] += 1
        else:
            stats["failed_calls"] += 1
            if metric.error_message:
                stats["errors"].append(
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "error": metric.error_message,
                        "parameters": metric.parameters,
                    }
                )

        # Update execution time stats
        exec_time = metric.execution_time_ms
        stats["total_execution_time_ms"] += exec_time
        stats["avg_execution_time_ms"] = (
            stats["total_execution_time_ms"] / stats["total_calls"]
        )
        stats["min_execution_time_ms"] = min(stats["min_execution_time_ms"], exec_time)
        stats["max_execution_time_ms"] = max(stats["max_execution_time_ms"], exec_time)

    def get_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """Get statistics for a specific tool or all tools.

        Args:
            tool_name: Tool name to get stats for, or None for all tools

        Returns:
            Dictionary with statistics
        """
        if tool_name:
            return dict(self._aggregated_stats.get(tool_name, {}))

        return {
            "total_metrics_collected": len(self._metrics),
            "tools": dict(self._aggregated_stats),
            "summary": self._generate_summary(),
        }

    def _generate_summary(self) -> dict[str, Any]:
        """Generate overall summary statistics.

        Returns:
            Summary statistics across all tools
        """
        total_calls = sum(
            stats["total_calls"] for stats in self._aggregated_stats.values()
        )
        total_success = sum(
            stats["successful_calls"] for stats in self._aggregated_stats.values()
        )
        total_failures = sum(
            stats["failed_calls"] for stats in self._aggregated_stats.values()
        )

        success_rate = (total_success / total_calls * 100) if total_calls > 0 else 0.0

        return {
            "total_tool_calls": total_calls,
            "successful_calls": total_success,
            "failed_calls": total_failures,
            "success_rate_percent": round(success_rate, 2),
            "unique_tools_used": len(self._aggregated_stats),
        }

    def get_most_used_tools(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Get the most frequently used tools.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, call_count) tuples, sorted by count descending
        """
        tool_counts = [
            (tool_name, stats["total_calls"])
            for tool_name, stats in self._aggregated_stats.items()
        ]

        return sorted(tool_counts, key=lambda x: x[1], reverse=True)[:top_n]

    def get_slowest_tools(self, top_n: int = 5) -> list[tuple[str, float]]:
        """Get the slowest tools by average execution time.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, avg_time_ms) tuples, sorted by time descending
        """
        tool_times = [
            (tool_name, stats["avg_execution_time_ms"])
            for tool_name, stats in self._aggregated_stats.items()
        ]

        return sorted(tool_times, key=lambda x: x[1], reverse=True)[:top_n]

    def get_error_rate_by_tool(self) -> dict[str, float]:
        """Get error rate percentage for each tool.

        Returns:
            Dictionary mapping tool name to error rate percentage
        """
        error_rates = {}

        for tool_name, stats in self._aggregated_stats.items():
            total = stats["total_calls"]
            failures = stats["failed_calls"]
            error_rate = (failures / total * 100) if total > 0 else 0.0
            error_rates[tool_name] = round(error_rate, 2)

        return error_rates

    def export_to_json(self, file_path: Path | str) -> None:
        """Export all metrics to JSON file.

        Args:
            file_path: Path to export file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        export_data = {
            "exported_at": datetime.now().isoformat(),
            "summary": self._generate_summary(),
            "tools_stats": dict(self._aggregated_stats),
            "raw_metrics": [metric.to_dict() for metric in self._metrics],
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

    def clear(self) -> None:
        """Clear all collected metrics and statistics."""
        self._metrics.clear()
        self._aggregated_stats.clear()

    def get_metrics_count(self) -> int:
        """Get total number of metrics collected.

        Returns:
            Number of metrics
        """
        return len(self._metrics)

    def get_last_metric(self) -> ToolMetric | None:
        """Get the most recently collected metric.

        Returns:
            Last metric if any metrics exist, None otherwise
        """
        return self._metrics[-1] if self._metrics else None


# Global singleton instance
_global_collector: MetricsCollector | None = None


def get_global_collector() -> MetricsCollector:
    """Get or create global metrics collector instance.

    Returns:
        Global MetricsCollector instance
    """
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector
