"""Tool execution tracker with automatic metrics collection.

This module provides a context manager for tracking MCP tool executions
and automatically recording metrics without manual instrumentation.
"""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from .metrics import MetricsCollector, ToolMetric, get_global_collector


class ToolTracker:
    """Tracker for automatic MCP tool execution monitoring.

    Provides context manager for transparent tracking of tool calls,
    automatically measuring execution time, success/failure, and errors.

    Example:
        tracker = ToolTracker()

        with tracker.track_tool_call("search_products", {"query": "laptop"}):
            result = await mcp_client.call_tool("search_products", {...})
    """

    def __init__(self, collector: MetricsCollector | None = None):
        """Initialize tool tracker.

        Args:
            collector: Optional custom metrics collector.
                      If None, uses global singleton.
        """
        self.collector = collector or get_global_collector()
        self._current_query: str | None = None

    def set_user_query(self, query: str) -> None:
        """Set the current user query for tracking context.

        Args:
            query: Original user query that triggered tool execution
        """
        self._current_query = query

    @contextmanager
    def track_tool_call(
        self, tool_name: str, parameters: dict[str, Any], user_query: str | None = None
    ) -> Generator[None, None, None]:
        """Track a tool execution with automatic metrics collection.

        Args:
            tool_name: Name of the tool being executed
            parameters: Tool parameters
            user_query: Optional user query that triggered this call

        Yields:
            None (context manager for execution tracking)

        Example:
            with tracker.track_tool_call("search", {"query": "laptop"}):
                result = await call_tool("search", {"query": "laptop"})
        """
        start_time = time.perf_counter()
        error_message = None
        success = False
        result_size = 0

        try:
            yield
            success = True

        except Exception as e:
            error_message = str(e)
            raise  # Re-raise exception after recording

        finally:
            # Calculate execution time
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # Create and record metric
            metric = ToolMetric(
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                success=success,
                parameters=parameters,
                result_size=result_size,
                error_message=error_message,
                user_query=user_query or self._current_query,
            )

            self.collector.record_execution(metric)

    @contextmanager
    def track_with_result(
        self, tool_name: str, parameters: dict[str, Any], user_query: str | None = None
    ) -> Generator[dict[str, Any], None, None]:
        """Track a tool execution and capture result metadata.

        This version allows tracking result size by yielding a mutable dict
        where the caller can store the result.

        Args:
            tool_name: Name of the tool being executed
            parameters: Tool parameters
            user_query: Optional user query that triggered this call

        Yields:
            Dictionary to store result metadata (result_size, etc.)

        Example:
            with tracker.track_with_result("search", {"q": "laptop"}) as ctx:
                result = await call_tool("search", {"q": "laptop"})
                ctx["result_size"] = len(result) if isinstance(result, list) else 1
        """
        start_time = time.perf_counter()
        error_message = None
        success = False

        # Context dict for caller to populate
        result_context: dict[str, Any] = {"result_size": 0}

        try:
            yield result_context
            success = True

        except Exception as e:
            error_message = str(e)
            raise

        finally:
            end_time = time.perf_counter()
            execution_time_ms = (end_time - start_time) * 1000

            # Extract result size from context
            result_size = result_context.get("result_size", 0)

            metric = ToolMetric(
                tool_name=tool_name,
                execution_time_ms=execution_time_ms,
                success=success,
                parameters=parameters,
                result_size=result_size,
                error_message=error_message,
                user_query=user_query or self._current_query,
            )

            self.collector.record_execution(metric)

    def get_stats(self, tool_name: str | None = None) -> dict[str, Any]:
        """Get execution statistics.

        Args:
            tool_name: Optional tool name to filter stats

        Returns:
            Statistics dictionary
        """
        return self.collector.get_stats(tool_name)

    def get_most_used_tools(self, top_n: int = 5) -> list[tuple[str, int]]:
        """Get most frequently used tools.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, call_count) tuples
        """
        return self.collector.get_most_used_tools(top_n)

    def get_slowest_tools(self, top_n: int = 5) -> list[tuple[str, float]]:
        """Get slowest tools by average execution time.

        Args:
            top_n: Number of top tools to return

        Returns:
            List of (tool_name, avg_time_ms) tuples
        """
        return self.collector.get_slowest_tools(top_n)

    def get_error_rate_by_tool(self) -> dict[str, float]:
        """Get error rate percentage for each tool.

        Returns:
            Dictionary mapping tool name to error rate percentage
        """
        return self.collector.get_error_rate_by_tool()

    def export_metrics(self, file_path: str) -> None:
        """Export all collected metrics to JSON file.

        Args:
            file_path: Path to export file
        """
        self.collector.export_to_json(file_path)

    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.collector.clear()
        self._current_query = None


# Global singleton instance
_global_tracker: ToolTracker | None = None


def get_global_tracker() -> ToolTracker:
    """Get or create global tool tracker instance.

    Returns:
        Global ToolTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = ToolTracker()
    return _global_tracker
