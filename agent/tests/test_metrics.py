#!/usr/bin/env python3
"""Agent Metrics - Demo and Validation.

This script demonstrates the observability features of BaseAgent,
showing how to track and analyze agent performance metrics.

Usage:
    python test_metrics.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
agent_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(agent_src))

import contextlib

from multi_agent import AgentFactory


def print_header(text: str, char: str = "="):
    """Print fancy header."""
    print("\n" + char * 80)
    print(f"  {text}")
    print(char * 80)


def print_metrics(metrics: dict):
    """Print metrics in a formatted way."""
    print("\n📊 Agent Metrics:")
    print(f"  Total Requests:      {metrics['total_requests']}")
    print(f"  Successful:          {metrics['successful_requests']}")
    print(f"  Failed:              {metrics['failed_requests']}")
    print(f"  Success Rate:        {metrics['success_rate']:.1f}%")
    print(f"  Avg Response Time:   {metrics['avg_response_time_ms']:.2f}ms")
    print(f"  Avg History Size:    {metrics['avg_history_size']:.1f}")
    print(f"  Current History:     {metrics['current_history_size']}")

    if metrics["errors"]:
        print("\n  Errors:")
        for error_type, count in metrics["errors"].items():
            print(f"    {error_type}: {count}")


async def demo_basic_metrics():
    """Demo 1: Basic metrics tracking."""
    print_header("DEMO 1: Basic Metrics Tracking", "=")

    print("\n📋 Creating agent and checking initial metrics...")

    agent = await AgentFactory.create("general", auto_initialize=False)

    # Check initial metrics
    metrics = agent.get_metrics()
    print("\n✅ Initial metrics (should be all zeros):")
    print_metrics(metrics)

    # Validate
    assert metrics["total_requests"] == 0
    assert metrics["successful_requests"] == 0
    assert metrics["failed_requests"] == 0
    assert metrics["success_rate"] == 0.0

    print("\n✅ DEMO 1 PASSED: Initial metrics are correct")


async def demo_error_tracking():
    """Demo 2: Error tracking."""
    print_header("DEMO 2: Error Tracking", "=")

    print("\n📋 Creating agent and triggering an error...")

    agent = await AgentFactory.create("general", auto_initialize=False)

    # Try to generate response without initialization (will fail)
    try:
        await agent.generate_response("test query")
    except RuntimeError as e:
        print(f"  Expected error caught: {type(e).__name__}")

    # Check metrics
    metrics = agent.get_metrics()
    print("\n📊 Metrics after error:")
    print_metrics(metrics)

    # Validate
    assert metrics["total_requests"] == 1
    assert metrics["failed_requests"] == 1
    assert metrics["success_rate"] == 0.0
    assert "RuntimeError" in metrics["errors"]

    print("\n✅ DEMO 2 PASSED: Errors are tracked correctly")


async def demo_reset_metrics():
    """Demo 3: Reset metrics."""
    print_header("DEMO 3: Reset Metrics", "=")

    print("\n📋 Creating agent, tracking metrics, then resetting...")

    agent = await AgentFactory.create("general", auto_initialize=False)

    # Trigger some errors
    for _ in range(3):
        with contextlib.suppress(RuntimeError):
            await agent.generate_response("test")

    metrics_before = agent.get_metrics()
    print("\n📊 Metrics before reset:")
    print_metrics(metrics_before)

    # Reset
    agent.reset_metrics()

    metrics_after = agent.get_metrics()
    print("\n📊 Metrics after reset:")
    print_metrics(metrics_after)

    # Validate
    assert metrics_before["total_requests"] == 3
    assert metrics_after["total_requests"] == 0
    assert metrics_after["errors"] == {}

    print("\n✅ DEMO 3 PASSED: Metrics reset works correctly")


async def demo_metrics_api():
    """Demo 4: Complete metrics API."""
    print_header("DEMO 4: Complete Metrics API", "=")

    print("\n📋 Demonstrating all metrics features...")

    agent = await AgentFactory.create("booking", auto_initialize=False)

    # 1. Check initial metrics
    print("\n1️⃣  Getting initial metrics...")
    metrics = agent.get_metrics()
    assert "total_requests" in metrics
    assert "success_rate" in metrics
    assert "avg_response_time_ms" in metrics
    print("  ✅ get_metrics() returns expected fields")

    # 2. Trigger requests
    print("\n2️⃣  Triggering multiple requests (will fail - not initialized)...")
    for i in range(5):
        with contextlib.suppress(RuntimeError):
            await agent.generate_response(f"query {i}")

    metrics = agent.get_metrics()
    assert metrics["total_requests"] == 5
    assert metrics["failed_requests"] == 5
    print(f"  ✅ Tracked {metrics['total_requests']} requests")

    # 3. Reset metrics
    print("\n3️⃣  Resetting metrics...")
    agent.reset_metrics()
    metrics = agent.get_metrics()
    assert metrics["total_requests"] == 0
    print("  ✅ reset_metrics() works")

    # 4. Cleanup (should also reset metrics)
    print("\n4️⃣  Testing cleanup (should reset metrics)...")
    for _ in range(2):
        with contextlib.suppress(RuntimeError):
            await agent.generate_response("test")

    await agent.cleanup()
    metrics = agent.get_metrics()
    assert metrics["total_requests"] == 0
    print("  ✅ cleanup() resets metrics")

    print("\n✅ DEMO 4 PASSED: All metrics API features work")


async def demo_metrics_summary():
    """Demo 5: Metrics summary display."""
    print_header("DEMO 5: Metrics Summary Display", "=")

    print("\n📋 Simulating real-world usage with metrics...")

    agent = await AgentFactory.create("sales", auto_initialize=False)

    # Simulate some activity
    print("\n🔄 Simulating 10 requests (all will fail - not initialized)...")
    for i in range(10):
        with contextlib.suppress(RuntimeError):
            await agent.generate_response(f"Query #{i + 1}")

    # Display metrics
    print("\n" + "=" * 80)
    print("  📊 FINAL METRICS SUMMARY")
    print("=" * 80)

    metrics = agent.get_metrics()
    print_metrics(metrics)

    print("\n" + "=" * 80)

    # Insights
    print("\n💡 Insights:")
    if metrics["failed_requests"] > 0:
        print(f"  ⚠️  {metrics['failed_requests']} requests failed")
        print(f"  📝 Most common error: {next(iter(metrics['errors'].keys()))}")

    if metrics["avg_response_time_ms"] > 0:
        print(f"  ⏱️  Average response time: {metrics['avg_response_time_ms']:.2f}ms")

    print("\n✅ DEMO 5 PASSED: Metrics summary displayed")


async def main():
    """Run all metrics demos."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  AGENT OBSERVABILITY - METRICS DEMO".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    print("\n🎯 Demonstrating BaseAgent metrics features...")

    results = []

    # Run demos
    try:
        await demo_basic_metrics()
        results.append(("Basic Metrics Tracking", True))
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append(("Basic Metrics Tracking", False))

    try:
        await demo_error_tracking()
        results.append(("Error Tracking", True))
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append(("Error Tracking", False))

    try:
        await demo_reset_metrics()
        results.append(("Reset Metrics", True))
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append(("Reset Metrics", False))

    try:
        await demo_metrics_api()
        results.append(("Complete Metrics API", True))
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append(("Complete Metrics API", False))

    try:
        await demo_metrics_summary()
        results.append(("Metrics Summary Display", True))
    except Exception as e:
        print(f"❌ FAILED: {e}")
        results.append(("Metrics Summary Display", False))

    # Summary
    print_header("DEMO SUMMARY", "=")

    for demo_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {demo_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL DEMOS PASSED - Metrics system working correctly!")
        print("\n📚 Usage Example:")
        print("""
# Create and use agent
agent = await AgentFactory.create("booking")
await agent.generate_response("Book appointment")

# Get metrics
metrics = agent.get_metrics()
print(f"Success rate: {metrics['success_rate']:.1f}%")
print(f"Avg latency: {metrics['avg_response_time_ms']:.0f}ms")

# Reset if needed
agent.reset_metrics()

# Cleanup
await agent.cleanup()
        """)
        return 0
    else:
        print("\n❌ SOME DEMOS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
