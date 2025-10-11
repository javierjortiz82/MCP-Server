"""Unit tests for ToolTracker."""

import pytest
import time
import tempfile
import json
from unittest.mock import MagicMock, patch

from observability.tracker import ToolTracker, get_global_tracker
from observability.metrics import MetricsCollector, ToolMetric


class TestToolTracker:
    """Test suite for ToolTracker class."""

    def setup_method(self):
        """Set up each test with a fresh collector."""
        self.collector = MetricsCollector()

    def test_tracker_initialization_default(self):
        """Test ToolTracker initialization with default collector."""
        tracker = ToolTracker(collector=self.collector)

        assert tracker.collector is not None
        assert tracker._current_query is None

    def test_tracker_initialization_custom_collector(self):
        """Test ToolTracker initialization with custom collector."""
        custom_collector = MetricsCollector()
        tracker = ToolTracker(collector=custom_collector)

        assert tracker.collector is custom_collector

    def test_set_user_query(self):
        """Test setting user query."""
        tracker = ToolTracker(collector=self.collector)

        tracker.set_user_query("find laptops under $1000")

        assert tracker._current_query == "find laptops under $1000"

    def test_track_tool_call_success(self):
        """Test tracking successful tool execution."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call("search", {"query": "laptop"}):
            # Simulate some work
            time.sleep(0.01)

        # Verify metric was recorded
        stats = tracker.get_stats("search")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 0

    def test_track_tool_call_with_exception(self):
        """Test tracking tool execution that raises exception."""
        tracker = ToolTracker(collector=self.collector)

        with pytest.raises(ValueError):
            with tracker.track_tool_call("failing_tool", {"param": "value"}):
                raise ValueError("Tool failed")

        # Metric should still be recorded
        stats = tracker.get_stats("failing_tool")
        assert stats["total_calls"] == 1
        assert stats["successful_calls"] == 0
        assert stats["failed_calls"] == 1

    def test_track_tool_call_with_user_query(self):
        """Test tracking with explicit user query."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call(
            "search", {"query": "laptop"}, user_query="find me a laptop"
        ):
            pass

        # Query should be recorded in metric
        last_metric = tracker.collector.get_last_metric()
        assert last_metric is not None
        assert last_metric.user_query == "find me a laptop"

    def test_track_tool_call_uses_current_query(self):
        """Test that tracking uses current query if not specified."""
        tracker = ToolTracker(collector=self.collector)
        tracker.set_user_query("global query")

        with tracker.track_tool_call("search", {"query": "laptop"}):
            pass

        last_metric = tracker.collector.get_last_metric()
        assert last_metric.user_query == "global query"

    def test_track_tool_call_execution_time_measured(self):
        """Test that execution time is measured."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call("slow_tool", {}):
            time.sleep(0.05)  # 50ms

        last_metric = tracker.collector.get_last_metric()
        # Should be at least 45ms (allowing some variance)
        assert last_metric.execution_time_ms >= 45

    def test_track_with_result_success(self):
        """Test track_with_result context manager."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_with_result("search", {"query": "laptop"}) as ctx:
            # Simulate getting results
            result = [{"id": 1}, {"id": 2}, {"id": 3}]
            ctx["result_size"] = len(result)

        last_metric = tracker.collector.get_last_metric()
        assert last_metric is not None
        assert last_metric.result_size == 3
        assert last_metric.success is True

    def test_track_with_result_with_exception(self):
        """Test track_with_result when exception occurs."""
        tracker = ToolTracker(collector=self.collector)

        with pytest.raises(RuntimeError):
            with tracker.track_with_result("failing_tool", {}) as ctx:
                raise RuntimeError("Failed")

        last_metric = tracker.collector.get_last_metric()
        assert last_metric.success is False
        assert "Failed" in last_metric.error_message

    def test_track_with_result_default_size(self):
        """Test that result_size defaults to 0."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_with_result("search", {}) as ctx:
            # Don't set result_size
            pass

        last_metric = tracker.collector.get_last_metric()
        assert last_metric.result_size == 0

    def test_track_with_result_user_query(self):
        """Test track_with_result with user query."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_with_result(
            "search", {}, user_query="find products"
        ) as ctx:
            ctx["result_size"] = 10

        last_metric = tracker.collector.get_last_metric()
        assert last_metric.user_query == "find products"

    def test_get_stats_specific_tool(self):
        """Test getting stats for specific tool."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call("tool1", {}):
            pass

        with tracker.track_tool_call("tool2", {}):
            pass

        stats = tracker.get_stats("tool1")
        assert stats["total_calls"] == 1

    def test_get_stats_all_tools(self):
        """Test getting stats for all tools."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call("tool1", {}):
            pass

        with tracker.track_tool_call("tool2", {}):
            pass

        stats = tracker.get_stats()
        assert stats["total_metrics_collected"] == 2

    def test_get_most_used_tools(self):
        """Test getting most used tools."""
        tracker = ToolTracker(collector=self.collector)

        # Call tool1 3 times
        for _ in range(3):
            with tracker.track_tool_call("tool1", {}):
                pass

        # Call tool2 1 time
        with tracker.track_tool_call("tool2", {}):
            pass

        most_used = tracker.get_most_used_tools(top_n=5)

        assert len(most_used) == 2
        assert most_used[0] == ("tool1", 3)
        assert most_used[1] == ("tool2", 1)

    def test_get_most_used_tools_limits_results(self):
        """Test that get_most_used_tools respects top_n."""
        tracker = ToolTracker(collector=self.collector)

        for i in range(5):
            with tracker.track_tool_call(f"tool{i}", {}):
                pass

        most_used = tracker.get_most_used_tools(top_n=3)

        assert len(most_used) == 3

    def test_get_slowest_tools(self):
        """Test getting slowest tools."""
        tracker = ToolTracker(collector=self.collector)

        # Slow tool
        with tracker.track_tool_call("slow", {}):
            time.sleep(0.05)

        # Fast tool
        with tracker.track_tool_call("fast", {}):
            time.sleep(0.001)

        slowest = tracker.get_slowest_tools(top_n=5)

        assert len(slowest) == 2
        # Slow should be first
        assert slowest[0][0] == "slow"
        assert slowest[0][1] > slowest[1][1]

    def test_get_error_rate_by_tool(self):
        """Test getting error rate by tool."""
        tracker = ToolTracker(collector=self.collector)

        # Tool with 2 successes, 1 error
        with tracker.track_tool_call("tool1", {}):
            pass

        with tracker.track_tool_call("tool1", {}):
            pass

        with pytest.raises(ValueError):
            with tracker.track_tool_call("tool1", {}):
                raise ValueError("Error")

        error_rates = tracker.get_error_rate_by_tool()

        assert "tool1" in error_rates
        # 1 error out of 3 total = 33.33%
        assert abs(error_rates["tool1"] - 33.33) < 0.1

    def test_export_metrics(self):
        """Test exporting metrics to file."""
        tracker = ToolTracker(collector=self.collector)

        with tracker.track_tool_call("test_tool", {"param": "value"}):
            pass

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            tracker.export_metrics(temp_file)

            # Verify file was created and contains data
            with open(temp_file, "r") as f:
                data = json.load(f)
                assert "raw_metrics" in data
                assert len(data["raw_metrics"]) == 1
                assert data["raw_metrics"][0]["tool_name"] == "test_tool"
        finally:
            import os
            os.unlink(temp_file)

    def test_clear_metrics(self):
        """Test clearing all metrics."""
        tracker = ToolTracker(collector=self.collector)
        tracker.set_user_query("test query")

        with tracker.track_tool_call("tool1", {}):
            pass

        with tracker.track_tool_call("tool2", {}):
            pass

        tracker.clear_metrics()

        # Metrics should be empty
        stats = tracker.get_stats()
        assert stats["total_metrics_collected"] == 0

        # Current query should be cleared
        assert tracker._current_query is None

    def test_multiple_tool_calls_tracked(self):
        """Test tracking multiple tool calls."""
        tracker = ToolTracker(collector=self.collector)

        for i in range(10):
            with tracker.track_tool_call(f"tool{i % 3}", {"index": i}):
                pass

        stats = tracker.get_stats()
        assert stats["total_metrics_collected"] == 10

    def test_error_message_captured(self):
        """Test that error messages are captured."""
        tracker = ToolTracker(collector=self.collector)

        with pytest.raises(RuntimeError):
            with tracker.track_tool_call("error_tool", {}):
                raise RuntimeError("Specific error message")

        last_metric = tracker.collector.get_last_metric()
        assert last_metric.error_message == "Specific error message"


class TestGlobalTracker:
    """Test suite for global tracker singleton."""

    def test_get_global_tracker_creates_instance(self):
        """Test that get_global_tracker creates instance."""
        import observability.tracker
        observability.tracker._global_tracker = None

        tracker = get_global_tracker()

        assert tracker is not None
        assert isinstance(tracker, ToolTracker)

    def test_get_global_tracker_singleton(self):
        """Test that get_global_tracker returns same instance."""
        import observability.tracker
        observability.tracker._global_tracker = None

        tracker1 = get_global_tracker()
        tracker2 = get_global_tracker()

        assert tracker1 is tracker2

    def test_global_tracker_shares_metrics(self):
        """Test that global tracker shares metrics across calls."""
        import observability.tracker
        observability.tracker._global_tracker = None

        tracker1 = get_global_tracker()

        with tracker1.track_tool_call("shared_tool", {}):
            pass

        tracker2 = get_global_tracker()
        stats = tracker2.get_stats("shared_tool")

        assert stats["total_calls"] == 1


class TestToolTrackerIntegration:
    """Integration tests for ToolTracker."""

    def setup_method(self):
        """Set up each test with a fresh collector."""
        self.collector = MetricsCollector()

    def test_realistic_usage_pattern(self):
        """Test realistic usage pattern with multiple tools."""
        tracker = ToolTracker(collector=self.collector)
        tracker.set_user_query("find gaming laptops under $2000")

        # Simulate search
        with tracker.track_with_result("search_products", {"query": "laptop"}) as ctx:
            results = [{"id": i} for i in range(10)]
            ctx["result_size"] = len(results)

        # Simulate detail fetch
        with tracker.track_tool_call("fetch_by_sku", {"sku": "LAPTOP-001"}):
            pass

        # Verify stats
        stats = tracker.get_stats()
        assert stats["total_metrics_collected"] == 2
        assert stats["summary"]["successful_calls"] == 2

        most_used = tracker.get_most_used_tools(top_n=5)
        assert len(most_used) == 2

    def test_error_handling_pattern(self):
        """Test error handling with retry pattern."""
        tracker = ToolTracker(collector=self.collector)

        # First attempt fails
        with pytest.raises(ValueError):
            with tracker.track_tool_call("unreliable_tool", {"retry": 1}):
                raise ValueError("Network error")

        # Second attempt fails
        with pytest.raises(ValueError):
            with tracker.track_tool_call("unreliable_tool", {"retry": 2}):
                raise ValueError("Network error")

        # Third attempt succeeds
        with tracker.track_tool_call("unreliable_tool", {"retry": 3}):
            pass

        stats = tracker.get_stats("unreliable_tool")
        assert stats["total_calls"] == 3
        assert stats["successful_calls"] == 1
        assert stats["failed_calls"] == 2

        error_rates = tracker.get_error_rate_by_tool()
        # 2 errors out of 3 = 66.67%
        assert abs(error_rates["unreliable_tool"] - 66.67) < 0.1
