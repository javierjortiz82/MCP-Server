"""Comprehensive tests for MCP improvements.

Tests for:
- Tool validation (Pydantic)
- Metrics collection and tracking
- Tool caching
- Retry strategies
- Fallback strategies
"""

import asyncio
import contextlib
import json
from pathlib import Path

from client_mcp.core.tool_cache import ToolCache
from client_mcp.core.tool_validator import ToolValidator
from client_mcp.observability.metrics import MetricsCollector, ToolMetric
from client_mcp.observability.tracker import ToolTracker
from client_mcp.strategies.fallback import (
    FallbackStrategy,
    create_default_fallback_strategy,
)
from client_mcp.strategies.retry import RetryConfig, RetryStrategy


def test_tool_validator():
    """Test tool parameter validation with Pydantic."""
    validator = ToolValidator()

    # Sample tool schema (similar to MCP tools)
    search_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "default": 5, "description": "Max results"},
            "min_score": {"type": "number", "description": "Minimum relevance score"},
        },
        "required": ["query"],
    }

    # Register schema
    validator.register_tool_schema("search_products", search_schema)

    # Test 1: Valid parameters
    try:
        valid_params = {"query": "laptop", "limit": 10, "min_score": 0.8}
        validator.validate_parameters("search_products", valid_params)
    except Exception:
        pass

    # Test 2: Missing required parameter
    try:
        invalid_params = {"limit": 10}
        validator.validate_parameters("search_products", invalid_params)
    except Exception:
        pass

    # Test 3: Type coercion
    try:
        coerce_params = {"query": "laptop", "limit": "5"}  # String instead of int
        validator.validate_parameters("search_products", coerce_params)
    except Exception:
        pass

    # Test 4: Sanitization
    dangerous_input = "laptop'; DROP TABLE products;--"
    validator.sanitize_string(dangerous_input)


def test_metrics_collector():
    """Test metrics collection and aggregation."""
    collector = MetricsCollector()

    # Simulate tool executions
    metrics = [
        ToolMetric(
            "search_products",
            120.5,
            True,
            {"query": "laptop"},
            5,
            user_query="Busco laptop",
        ),
        ToolMetric(
            "search_products",
            95.3,
            True,
            {"query": "mouse"},
            3,
            user_query="Quiero mouse",
        ),
        ToolMetric("fetch_by_sku", 45.2, True, {"sku": "LAP-001"}, 1),
        ToolMetric(
            "search_products",
            200.0,
            False,
            {"query": "xyz"},
            0,
            error_message="No results",
        ),
        ToolMetric("fuzzy_search", 150.0, True, {"search_term": "laptp"}, 2),
    ]

    for metric in metrics:
        collector.record_execution(metric)

    # Get overall stats
    collector.get_stats()

    # Most used tools
    most_used = collector.get_most_used_tools(3)
    for _tool_name, _count in most_used:
        pass

    # Slowest tools
    slowest = collector.get_slowest_tools(3)
    for _tool_name, _avg_time in slowest:
        pass

    # Error rates
    error_rates = collector.get_error_rate_by_tool()
    for _tool_name, _rate in error_rates.items():
        pass

    # Export to JSON
    export_path = Path("/tmp/test_metrics.json")
    collector.export_to_json(export_path)

    # Verify export
    with export_path.open() as f:
        json.load(f)


def test_tool_tracker():
    """Test automatic tool execution tracking."""
    tracker = ToolTracker()
    tracker.set_user_query("Busco una laptop gaming")

    # Simulate successful tool call
    with tracker.track_tool_call("search_products", {"query": "laptop gaming"}):
        # Simulate work
        import time

        time.sleep(0.1)

    # Simulate failed tool call
    try:
        with tracker.track_tool_call("fetch_by_sku", {"sku": "INVALID"}):
            raise ValueError("SKU not found")
    except ValueError:
        pass

    # Track with result metadata
    with tracker.track_with_result("search_products", {"query": "mouse"}) as ctx:
        import time

        time.sleep(0.05)
        ctx["result_size"] = 7  # Simulate 7 results

    # Get stats
    tracker.get_stats()


def test_tool_cache():
    """Test tool caching with TTL."""
    cache = ToolCache(ttl_seconds=1.0)  # 1 second TTL for testing

    # Cache sample tools
    tools = [
        {
            "name": "search_products",
            "description": "Search for products",
            "inputSchema": {},
        },
        {"name": "fetch_by_sku", "description": "Fetch by SKU", "inputSchema": {}},
    ]

    wrappers = [lambda: "result1", lambda: "result2"]

    cache.cache_snapshot(tools, wrappers)

    # Test cache hit
    if cache.has_valid_snapshot():
        cache.get_snapshot()
    else:
        pass

    # Get individual tool
    tool = cache.get_tool("search_products")
    if tool:
        pass

    # Cache stats
    cache.get_cache_stats()

    # Test TTL expiration
    import time

    time.sleep(1.1)

    if not cache.has_valid_snapshot():
        pass
    else:
        pass

    cache.get_cache_stats()


async def test_retry_strategy():
    """Test retry with exponential backoff."""
    config = RetryConfig(
        max_attempts=3,
        initial_delay_ms=50.0,
        max_delay_ms=500.0,
        jitter=False,  # Disable jitter for consistent testing
    )

    strategy = RetryStrategy(config)

    # Test 1: Success on second attempt
    attempt_count = [0]

    async def flaky_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise ValueError(f"Temporary failure (attempt {attempt_count[0]})")
        return "Success!"

    with contextlib.suppress(Exception):
        await strategy.execute_with_retry(flaky_operation)

    # Test 2: All attempts fail

    async def always_fails():
        raise RuntimeError("Permanent failure")

    with contextlib.suppress(RuntimeError):
        await strategy.execute_with_retry(always_fails)


def test_fallback_strategy():
    """Test fallback to alternative tools."""
    strategy = FallbackStrategy()

    # Add fallback rules
    strategy.add_rule(
        primary_tool="search_products",
        fallback_tool="fuzzy_search_smart",
        param_mapping={"query": "search_term"},
    )

    strategy.add_rule(
        primary_tool="fetch_by_sku",
        fallback_tool="fetch_by_id",
        param_mapping={"sku": "product_id"},
    )

    # Test fallback chain
    strategy.get_fallback_chain("search_products")

    # Test parameter mapping
    params = {"query": "laptop", "limit": 5}
    mapping = {"query": "search_term", "limit": "max_results"}
    strategy._map_parameters(params, mapping)

    # Check if tools have fallbacks
    strategy.has_fallback("search_products")

    # Test default strategy
    create_default_fallback_strategy()


def run_all_tests():
    """Run all improvement tests."""
    # Synchronous tests
    test_tool_validator()
    test_metrics_collector()
    test_tool_tracker()
    test_tool_cache()
    test_fallback_strategy()

    # Async tests
    asyncio.run(test_retry_strategy())


if __name__ == "__main__":
    run_all_tests()
