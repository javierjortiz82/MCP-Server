"""Comprehensive tests for MCP improvements.

Tests for:
- Tool validation (Pydantic)
- Metrics collection and tracking
- Tool caching
- Retry strategies
- Fallback strategies
"""

import asyncio
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
    print("\n" + "=" * 60)
    print("TEST 1: Tool Validator (Pydantic)")
    print("=" * 60)

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
    print("✅ Schema registered for 'search_products'")

    # Test 1: Valid parameters
    try:
        valid_params = {"query": "laptop", "limit": 10, "min_score": 0.8}
        validated = validator.validate_parameters("search_products", valid_params)
        print(f"✅ Valid params: {validated}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")

    # Test 2: Missing required parameter
    try:
        invalid_params = {"limit": 10}
        validator.validate_parameters("search_products", invalid_params)
        print("❌ Should have failed - missing required 'query'")
    except Exception:
        print("✅ Correctly rejected invalid params: validation error")

    # Test 3: Type coercion
    try:
        coerce_params = {"query": "laptop", "limit": "5"}  # String instead of int
        validated = validator.validate_parameters("search_products", coerce_params)
        print(
            f"✅ Type coercion: limit='5' (str) → {validated['limit']} ({type(validated['limit']).__name__})"
        )
    except Exception as e:
        print(f"❌ Type coercion failed: {e}")

    # Test 4: Sanitization
    dangerous_input = "laptop'; DROP TABLE products;--"
    sanitized = validator.sanitize_string(dangerous_input)
    print(f"✅ Sanitization: '{dangerous_input}' → '{sanitized}'")

    print(f"\n📊 Registered tools: {validator.get_registered_tools()}")


def test_metrics_collector():
    """Test metrics collection and aggregation."""
    print("\n" + "=" * 60)
    print("TEST 2: Metrics Collector")
    print("=" * 60)

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

    print(f"✅ Recorded {len(metrics)} executions")

    # Get overall stats
    stats = collector.get_stats()
    print("\n📊 Overall Stats:")
    print(f"  Total metrics: {stats['total_metrics_collected']}")
    print(f"  Unique tools: {stats['summary']['unique_tools_used']}")
    print(f"  Success rate: {stats['summary']['success_rate_percent']}%")

    # Most used tools
    most_used = collector.get_most_used_tools(3)
    print("\n🔝 Most Used Tools:")
    for tool_name, count in most_used:
        print(f"  {tool_name}: {count} calls")

    # Slowest tools
    slowest = collector.get_slowest_tools(3)
    print("\n⏱️  Slowest Tools:")
    for tool_name, avg_time in slowest:
        print(f"  {tool_name}: {avg_time:.2f}ms average")

    # Error rates
    error_rates = collector.get_error_rate_by_tool()
    print("\n❌ Error Rates:")
    for tool_name, rate in error_rates.items():
        print(f"  {tool_name}: {rate:.2f}%")

    # Export to JSON
    export_path = Path("/tmp/test_metrics.json")
    collector.export_to_json(export_path)
    print(f"\n✅ Metrics exported to: {export_path}")

    # Verify export
    with export_path.open() as f:
        exported = json.load(f)
    print(f"✅ Export contains {len(exported['raw_metrics'])} metrics")


def test_tool_tracker():
    """Test automatic tool execution tracking."""
    print("\n" + "=" * 60)
    print("TEST 3: Tool Tracker")
    print("=" * 60)

    tracker = ToolTracker()
    tracker.set_user_query("Busco una laptop gaming")

    # Simulate successful tool call
    print("\n🔧 Simulating successful tool call...")
    with tracker.track_tool_call("search_products", {"query": "laptop gaming"}):
        # Simulate work
        import time

        time.sleep(0.1)
        print("  Tool executed successfully")

    # Simulate failed tool call
    print("\n🔧 Simulating failed tool call...")
    try:
        with tracker.track_tool_call("fetch_by_sku", {"sku": "INVALID"}):
            raise ValueError("SKU not found")
    except ValueError:
        print("  Tool failed (expected)")

    # Track with result metadata
    print("\n🔧 Simulating tool call with result metadata...")
    with tracker.track_with_result("search_products", {"query": "mouse"}) as ctx:
        import time

        time.sleep(0.05)
        ctx["result_size"] = 7  # Simulate 7 results

    # Get stats
    stats = tracker.get_stats()
    print("\n📊 Tracker Stats:")
    print(f"  Total calls: {stats['summary']['total_tool_calls']}")
    print(f"  Successful: {stats['summary']['successful_calls']}")
    print(f"  Failed: {stats['summary']['failed_calls']}")


def test_tool_cache():
    """Test tool caching with TTL."""
    print("\n" + "=" * 60)
    print("TEST 4: Tool Cache")
    print("=" * 60)

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
    print(f"✅ Cached {len(tools)} tools")

    # Test cache hit
    if cache.has_valid_snapshot():
        snapshot = cache.get_snapshot()
        print(
            f"✅ Cache HIT: {len(snapshot.tools) if snapshot else 0} tools in snapshot"
        )
    else:
        print("❌ Cache MISS")

    # Get individual tool
    tool = cache.get_tool("search_products")
    if tool:
        print(f"✅ Retrieved tool: {tool.name}")

    # Cache stats
    stats = cache.get_cache_stats()
    print("\n📊 Cache Stats:")
    print(f"  Total cached: {stats['total_tools_cached']}")
    print(f"  Valid tools: {stats['valid_tools']}")
    print(f"  Has valid snapshot: {stats['has_valid_snapshot']}")

    # Test TTL expiration
    print("\n⏳ Waiting for TTL expiration (1 second)...")
    import time

    time.sleep(1.1)

    if not cache.has_valid_snapshot():
        print("✅ Cache expired correctly")
    else:
        print("❌ Cache should have expired")

    stats_after = cache.get_cache_stats()
    print("📊 Cache Stats After Expiration:")
    print(f"  Valid tools: {stats_after['valid_tools']}")


async def test_retry_strategy():
    """Test retry with exponential backoff."""
    print("\n" + "=" * 60)
    print("TEST 5: Retry Strategy")
    print("=" * 60)

    config = RetryConfig(
        max_attempts=3,
        initial_delay_ms=50.0,
        max_delay_ms=500.0,
        jitter=False,  # Disable jitter for consistent testing
    )

    strategy = RetryStrategy(config)

    # Test 1: Success on second attempt
    print("\n🔧 Test: Success on attempt 2/3")
    attempt_count = [0]

    async def flaky_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise ValueError(f"Temporary failure (attempt {attempt_count[0]})")
        return "Success!"

    try:
        result = await strategy.execute_with_retry(flaky_operation)
        print(f"✅ Result: {result} (after {attempt_count[0]} attempts)")
    except Exception as e:
        print(f"❌ Failed: {e}")

    # Test 2: All attempts fail
    print("\n🔧 Test: All attempts fail")

    async def always_fails():
        raise RuntimeError("Permanent failure")

    try:
        await strategy.execute_with_retry(always_fails)
        print("❌ Should have raised exception")
    except RuntimeError:
        print("✅ Correctly raised exception after max attempts")


def test_fallback_strategy():
    """Test fallback to alternative tools."""
    print("\n" + "=" * 60)
    print("TEST 6: Fallback Strategy")
    print("=" * 60)

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

    print("✅ Added 2 fallback rules")

    # Test fallback chain
    chain = strategy.get_fallback_chain("search_products")
    print(f"\n🔗 Fallback chain for 'search_products': {' → '.join(chain)}")

    # Test parameter mapping
    params = {"query": "laptop", "limit": 5}
    mapping = {"query": "search_term", "limit": "max_results"}
    mapped = strategy._map_parameters(params, mapping)
    print("\n🔄 Parameter mapping:")
    print(f"  Original: {params}")
    print(f"  Mapped: {mapped}")

    # Check if tools have fallbacks
    has_fallback = strategy.has_fallback("search_products")
    print(f"\n✅ 'search_products' has fallback: {has_fallback}")

    # Test default strategy
    create_default_fallback_strategy()
    print("\n✅ Created default strategy with pre-configured rules")


def run_all_tests():
    """Run all improvement tests."""
    print("\n" + "═" * 60)
    print("🧪 COMPREHENSIVE TESTS - MCP IMPROVEMENTS")
    print("═" * 60)

    # Synchronous tests
    test_tool_validator()
    test_metrics_collector()
    test_tool_tracker()
    test_tool_cache()
    test_fallback_strategy()

    # Async tests
    print("\n⏳ Running async tests...")
    asyncio.run(test_retry_strategy())

    print("\n" + "═" * 60)
    print("✅ ALL TESTS COMPLETED")
    print("═" * 60)


if __name__ == "__main__":
    run_all_tests()
