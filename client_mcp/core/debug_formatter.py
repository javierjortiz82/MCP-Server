"""Debug information formatter for tool execution metrics.

This module provides formatting utilities for displaying tool execution
metrics and debug information in a user-friendly way.
"""

import hashlib
import json

from observability.metrics import ToolMetric


class DebugFormatter:
    """Formatter for tool execution debug information.

    This class handles formatting of debug information about tool executions,
    including metric hashing to prevent duplicates.

    Attributes:
        shown_debug_hashes: Set of hashes for already shown debug info
    """

    def __init__(self):
        """Initialize debug formatter."""
        self.shown_debug_hashes: set[str] = set()

    def reset(self) -> None:
        """Reset shown debug hashes for new query."""
        self.shown_debug_hashes.clear()

    def get_metric_hash(self, metric: ToolMetric) -> str:
        """Generate hash for metric to detect duplicates.

        Args:
            metric: Tool execution metric

        Returns:
            Hash string identifying unique tool call

        Example:
            >>> formatter = DebugFormatter()
            >>> metric = ToolMetric(tool_name="search", parameters={"q": "test"}, ...)
            >>> hash1 = formatter.get_metric_hash(metric)
            >>> hash2 = formatter.get_metric_hash(metric)
            >>> hash1 == hash2
            True
        """
        # Create deterministic hash based on tool name and parameters
        metric_data = {
            "tool_name": metric.tool_name,
            "parameters": sorted(metric.parameters.items()),  # Sort for consistency
            "user_query": metric.user_query,
        }
        metric_json = json.dumps(metric_data, sort_keys=True)
        return hashlib.md5(metric_json.encode()).hexdigest()

    def format_debug_info(self, metric: ToolMetric) -> str:
        """Format debug information about tool execution.

        Args:
            metric: Tool execution metric to format

        Returns:
            Formatted debug string with tool details

        Example:
            >>> formatter = DebugFormatter()
            >>> metric = ToolMetric(
            ...     tool_name="search_products",
            ...     parameters={"query": "laptop"},
            ...     success=True,
            ...     result_size=5,
            ...     execution_time_ms=120.5
            ... )
            >>> info = formatter.format_debug_info(metric)
            >>> "search_products" in info
            True
        """
        # Format parameters as readable string
        params_str = ", ".join(f"{k}={repr(v)}" for k, v in metric.parameters.items())

        # Format status with emoji
        status = (
            "✅ Éxito"
            if metric.success
            else f"❌ Error: {metric.error_message}"
        )

        # Handle fallback case
        result_msg = f"{metric.result_size} producto(s) encontrado(s)"
        if metric.result_size == 0 and metric.success:
            result_msg = "0 (fallback encontró resultados - ver respuesta arriba)"

        return f"""
---
🔧 **DEBUG INFO**
• Tool invocado: `{metric.tool_name}`
• Parámetros: `{params_str}`
• Resultados: {result_msg}
• Tiempo de ejecución: {metric.execution_time_ms:.2f}ms
• Estado: {status}"""

    def format_fallback_debug_info(
        self, primary: ToolMetric, fallback: ToolMetric
    ) -> str:
        """Format combined debug info for fallback scenario.

        Args:
            primary: Primary tool metric (failed with 0 results)
            fallback: Fallback tool metric (succeeded with results)

        Returns:
            Formatted debug string combining both tools

        Example:
            >>> formatter = DebugFormatter()
            >>> primary = ToolMetric(tool_name="search", result_size=0, ...)
            >>> fallback = ToolMetric(tool_name="fuzzy_search", result_size=5, ...)
            >>> info = formatter.format_fallback_debug_info(primary, fallback)
            >>> "fallback" in info
            True
        """
        # Calculate total execution time
        total_time_ms = primary.execution_time_ms + fallback.execution_time_ms

        # Format tool chain
        tool_chain = (
            f"`{primary.tool_name}` ➜ `{fallback.tool_name}` (fallback automático)"
        )

        # Format results
        results_msg = f"0 → {fallback.result_size} (fallback exitoso)"

        # Get primary query parameter for context
        primary_query = primary.parameters.get("query", "N/A")

        return f"""
---
🔧 **DEBUG INFO**
• Tool invocado: {tool_chain}
• Query: '{primary_query}'
• Resultados: {results_msg}
• Tiempo total: {total_time_ms:.2f}ms
• Estado: ✅ Éxito"""

    def should_show_metric(self, metric: ToolMetric) -> bool:
        """Check if metric should be shown (not already displayed).

        Args:
            metric: Tool execution metric

        Returns:
            True if metric should be shown, False if already displayed
        """
        metric_hash = self.get_metric_hash(metric)
        if metric_hash in self.shown_debug_hashes:
            return False

        self.shown_debug_hashes.add(metric_hash)
        return True

    def should_show_fallback(
        self, primary: ToolMetric, fallback: ToolMetric
    ) -> bool:
        """Check if fallback metrics should be shown.

        Args:
            primary: Primary tool metric
            fallback: Fallback tool metric

        Returns:
            True if fallback should be shown, False if already displayed
        """
        combined_hash = self.get_metric_hash(primary) + self.get_metric_hash(
            fallback
        )
        if combined_hash in self.shown_debug_hashes:
            return False

        self.shown_debug_hashes.add(combined_hash)
        return True
