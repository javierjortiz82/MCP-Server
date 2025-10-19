"""Unit tests for ToolCache."""

import time

from core.tool_cache import (
    CachedTool,
    ToolCache,
    ToolsSnapshot,
    get_global_cache,
)


class TestCachedTool:
    """Test suite for CachedTool dataclass."""

    def test_cached_tool_creation(self):
        """Test CachedTool creation with all fields."""
        tool = CachedTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"},
            callable_wrapper=lambda: None,
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {"type": "object"}
        assert tool.callable_wrapper is not None
        assert tool.cached_at > 0

    def test_cached_tool_without_wrapper(self):
        """Test CachedTool creation without callable wrapper."""
        tool = CachedTool(
            name="simple_tool",
            description="Simple",
            input_schema={},
        )

        assert tool.name == "simple_tool"
        assert tool.callable_wrapper is None

    def test_cached_tool_not_expired(self):
        """Test that recently cached tool is not expired."""
        tool = CachedTool(
            name="test",
            description="test",
            input_schema={},
        )

        assert tool.is_expired(ttl_seconds=300.0) is False

    def test_cached_tool_expired(self):
        """Test that old cached tool is expired."""
        tool = CachedTool(
            name="test",
            description="test",
            input_schema={},
        )

        # Set cached_at to past
        tool.cached_at = time.time() - 400

        assert tool.is_expired(ttl_seconds=300.0) is True

    def test_cached_tool_exactly_at_ttl(self):
        """Test expiration at exactly TTL boundary."""
        tool = CachedTool(
            name="test",
            description="test",
            input_schema={},
        )

        # Set to exactly TTL seconds ago
        tool.cached_at = time.time() - 300

        # Should be expired (> TTL)
        assert tool.is_expired(ttl_seconds=300.0) is True


class TestToolsSnapshot:
    """Test suite for ToolsSnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test ToolsSnapshot creation."""
        tools = [
            CachedTool(name="tool1", description="Tool 1", input_schema={}),
            CachedTool(name="tool2", description="Tool 2", input_schema={}),
        ]
        wrappers = [lambda: "tool1", lambda: "tool2"]

        snapshot = ToolsSnapshot(tools=tools, tool_wrappers=wrappers)

        assert len(snapshot.tools) == 2
        assert len(snapshot.tool_wrappers) == 2
        assert snapshot.cached_at > 0

    def test_snapshot_not_expired(self):
        """Test that recent snapshot is not expired."""
        snapshot = ToolsSnapshot(tools=[], tool_wrappers=[])

        assert snapshot.is_expired(ttl_seconds=300.0) is False

    def test_snapshot_expired(self):
        """Test that old snapshot is expired."""
        snapshot = ToolsSnapshot(tools=[], tool_wrappers=[])
        snapshot.cached_at = time.time() - 400

        assert snapshot.is_expired(ttl_seconds=300.0) is True


class TestToolCache:
    """Test suite for ToolCache class."""

    def test_cache_initialization(self):
        """Test ToolCache initialization."""
        cache = ToolCache(ttl_seconds=600.0)

        assert cache.ttl_seconds == 600.0
        assert len(cache._tools_by_name) == 0
        assert cache._snapshot is None

    def test_cache_default_ttl(self):
        """Test default TTL is 300 seconds."""
        cache = ToolCache()

        assert cache.ttl_seconds == 300.0

    def test_cache_tool(self):
        """Test caching a single tool."""
        cache = ToolCache()

        cache.cache_tool(
            name="search",
            description="Search tool",
            input_schema={"type": "object"},
        )

        assert "search" in cache._tools_by_name
        assert cache._tools_by_name["search"].name == "search"
        assert cache._tools_by_name["search"].description == "Search tool"

    def test_cache_tool_with_wrapper(self):
        """Test caching tool with callable wrapper."""
        cache = ToolCache()

        def wrapper(x):
            return x * 2

        cache.cache_tool(
            name="calc",
            description="Calculator",
            input_schema={},
            callable_wrapper=wrapper,
        )

        cached = cache._tools_by_name["calc"]
        assert cached.callable_wrapper == wrapper

    def test_cache_snapshot(self):
        """Test caching complete snapshot."""
        cache = ToolCache()

        tools_defs = [
            {
                "name": "tool1",
                "description": "Tool 1",
                "inputSchema": {"type": "object"},
            },
            {
                "name": "tool2",
                "description": "Tool 2",
                "inputSchema": {"type": "string"},
            },
        ]
        wrappers = [lambda: "w1", lambda: "w2"]

        cache.cache_snapshot(tools_defs, wrappers)

        assert cache._snapshot is not None
        assert len(cache._snapshot.tools) == 2
        assert len(cache._snapshot.tool_wrappers) == 2
        assert "tool1" in cache._tools_by_name
        assert "tool2" in cache._tools_by_name

    def test_cache_snapshot_clears_existing(self):
        """Test that cache_snapshot clears existing cache."""
        cache = ToolCache()

        # Cache some tools first
        cache.cache_tool("old_tool", "Old", {})

        # Cache new snapshot
        tools_defs = [{"name": "new_tool", "description": "New", "inputSchema": {}}]
        cache.cache_snapshot(tools_defs, [])

        # Old tool should be gone
        assert "old_tool" not in cache._tools_by_name
        assert "new_tool" in cache._tools_by_name

    def test_cache_snapshot_mismatched_wrappers(self):
        """Test snapshot with fewer wrappers than tools."""
        cache = ToolCache()

        tools_defs = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"},
            {"name": "tool3", "description": "Tool 3"},
        ]
        wrappers = [lambda: "w1"]  # Only 1 wrapper for 3 tools

        cache.cache_snapshot(tools_defs, wrappers)

        # Should handle gracefully
        assert len(cache._snapshot.tools) == 3
        assert cache._tools_by_name["tool1"].callable_wrapper is not None
        assert cache._tools_by_name["tool2"].callable_wrapper is None
        assert cache._tools_by_name["tool3"].callable_wrapper is None

    def test_get_tool_valid(self):
        """Test getting a valid cached tool."""
        cache = ToolCache()
        cache.cache_tool("test", "Test tool", {})

        tool = cache.get_tool("test")

        assert tool is not None
        assert tool.name == "test"

    def test_get_tool_not_found(self):
        """Test getting non-existent tool."""
        cache = ToolCache()

        tool = cache.get_tool("nonexistent")

        assert tool is None

    def test_get_tool_expired(self):
        """Test getting expired tool returns None."""
        cache = ToolCache(ttl_seconds=1.0)
        cache.cache_tool("old", "Old tool", {})

        # Make it expired
        cache._tools_by_name["old"].cached_at = time.time() - 2

        tool = cache.get_tool("old")

        assert tool is None
        # Should also be removed from cache
        assert "old" not in cache._tools_by_name

    def test_get_snapshot_valid(self):
        """Test getting valid snapshot."""
        cache = ToolCache()
        tools_defs = [{"name": "tool1", "description": "Tool 1"}]
        cache.cache_snapshot(tools_defs, [])

        snapshot = cache.get_snapshot()

        assert snapshot is not None
        assert len(snapshot.tools) == 1

    def test_get_snapshot_none_when_empty(self):
        """Test getting snapshot when none exists."""
        cache = ToolCache()

        snapshot = cache.get_snapshot()

        assert snapshot is None

    def test_get_snapshot_expired(self):
        """Test getting expired snapshot returns None."""
        cache = ToolCache(ttl_seconds=1.0)
        tools_defs = [{"name": "tool1", "description": "Tool 1"}]
        cache.cache_snapshot(tools_defs, [])

        # Make snapshot expired
        cache._snapshot.cached_at = time.time() - 2

        snapshot = cache.get_snapshot()

        assert snapshot is None
        # Should clear expired data
        assert cache._snapshot is None
        assert len(cache._tools_by_name) == 0

    def test_has_valid_snapshot_true(self):
        """Test has_valid_snapshot returns True when valid."""
        cache = ToolCache()
        tools_defs = [{"name": "tool1", "description": "Tool 1"}]
        cache.cache_snapshot(tools_defs, [])

        assert cache.has_valid_snapshot() is True

    def test_has_valid_snapshot_false(self):
        """Test has_valid_snapshot returns False when no snapshot."""
        cache = ToolCache()

        assert cache.has_valid_snapshot() is False

    def test_get_all_tools(self):
        """Test getting all valid tools."""
        cache = ToolCache()
        cache.cache_tool("tool1", "Tool 1", {})
        cache.cache_tool("tool2", "Tool 2", {})
        cache.cache_tool("tool3", "Tool 3", {})

        tools = cache.get_all_tools()

        assert len(tools) == 3
        tool_names = [t.name for t in tools]
        assert "tool1" in tool_names
        assert "tool2" in tool_names
        assert "tool3" in tool_names

    def test_get_all_tools_filters_expired(self):
        """Test get_all_tools filters out expired tools."""
        cache = ToolCache(ttl_seconds=100.0)
        cache.cache_tool("valid", "Valid tool", {})
        cache.cache_tool("expired", "Expired tool", {})

        # Make one expired
        cache._tools_by_name["expired"].cached_at = time.time() - 200

        tools = cache.get_all_tools()

        assert len(tools) == 1
        assert tools[0].name == "valid"
        # Expired should be removed
        assert "expired" not in cache._tools_by_name

    def test_get_tool_names(self):
        """Test getting all tool names."""
        cache = ToolCache()
        cache.cache_tool("tool1", "Tool 1", {})
        cache.cache_tool("tool2", "Tool 2", {})

        names = cache.get_tool_names()

        assert len(names) == 2
        assert "tool1" in names
        assert "tool2" in names

    def test_get_tool_names_empty(self):
        """Test getting tool names when cache is empty."""
        cache = ToolCache()

        names = cache.get_tool_names()

        assert names == []

    def test_invalidate_tool(self):
        """Test invalidating specific tool."""
        cache = ToolCache()
        cache.cache_tool("tool1", "Tool 1", {})
        cache.cache_tool("tool2", "Tool 2", {})

        cache.invalidate_tool("tool1")

        assert "tool1" not in cache._tools_by_name
        assert "tool2" in cache._tools_by_name

    def test_invalidate_tool_nonexistent(self):
        """Test invalidating non-existent tool doesn't error."""
        cache = ToolCache()

        # Should not raise error
        cache.invalidate_tool("nonexistent")

    def test_invalidate_all(self):
        """Test invalidating all cached data."""
        cache = ToolCache()
        tools_defs = [{"name": "tool1", "description": "Tool 1"}]
        cache.cache_snapshot(tools_defs, [lambda: "w1"])

        cache.invalidate_all()

        assert len(cache._tools_by_name) == 0
        assert cache._snapshot is None

    def test_get_cache_stats(self):
        """Test getting cache statistics."""
        cache = ToolCache(ttl_seconds=300.0)
        tools_defs = [
            {"name": "tool1", "description": "Tool 1"},
            {"name": "tool2", "description": "Tool 2"},
        ]
        cache.cache_snapshot(tools_defs, [])

        stats = cache.get_cache_stats()

        assert stats["total_tools_cached"] == 2
        assert stats["valid_tools"] == 2
        assert stats["expired_tools"] == 0
        assert stats["has_valid_snapshot"] is True
        assert stats["snapshot_age_seconds"] is not None
        assert stats["snapshot_age_seconds"] < 1.0  # Just created
        assert stats["ttl_seconds"] == 300.0

    def test_get_cache_stats_no_snapshot(self):
        """Test cache stats when no snapshot exists."""
        cache = ToolCache()

        stats = cache.get_cache_stats()

        assert stats["total_tools_cached"] == 0
        assert stats["has_valid_snapshot"] is False
        assert stats["snapshot_age_seconds"] is None

    def test_get_cache_stats_with_expired_tools(self):
        """Test cache stats with expired tools."""
        cache = ToolCache(ttl_seconds=1.0)
        cache.cache_tool("valid", "Valid", {})
        cache.cache_tool("expired", "Expired", {})

        # Make one expired
        cache._tools_by_name["expired"].cached_at = time.time() - 2

        stats = cache.get_cache_stats()

        # Before cleanup, both are in cache
        assert stats["total_tools_cached"] == 2
        # After get_all_tools() in get_cache_stats, only valid remains
        assert stats["valid_tools"] == 1
        assert stats["expired_tools"] == 1

    def test_set_ttl(self):
        """Test updating TTL."""
        cache = ToolCache(ttl_seconds=300.0)

        cache.set_ttl(600.0)

        assert cache.ttl_seconds == 600.0

    def test_set_ttl_affects_expiration(self):
        """Test that changing TTL affects expiration checks."""
        cache = ToolCache(ttl_seconds=100.0)
        cache.cache_tool("test", "Test", {})

        # Make it 150 seconds old
        cache._tools_by_name["test"].cached_at = time.time() - 150

        # With TTL=100, it's expired
        tool = cache.get_tool("test")
        assert tool is None

        # Cache again
        cache.cache_tool("test2", "Test 2", {})
        cache._tools_by_name["test2"].cached_at = time.time() - 150

        # Change TTL to 200
        cache.set_ttl(200.0)

        # Now it's valid
        tool2 = cache.get_tool("test2")
        assert tool2 is not None


class TestGlobalCache:
    """Test suite for global cache singleton."""

    def test_get_global_cache_creates_instance(self):
        """Test that get_global_cache creates instance."""
        # Reset global cache
        import core.tool_cache

        core.tool_cache._global_cache = None

        cache = get_global_cache()

        assert cache is not None
        assert isinstance(cache, ToolCache)

    def test_get_global_cache_singleton(self):
        """Test that get_global_cache returns same instance."""
        # Reset global cache
        import core.tool_cache

        core.tool_cache._global_cache = None

        cache1 = get_global_cache()
        cache2 = get_global_cache()

        assert cache1 is cache2

    def test_get_global_cache_custom_ttl(self):
        """Test creating global cache with custom TTL."""
        import core.tool_cache

        core.tool_cache._global_cache = None

        cache = get_global_cache(ttl_seconds=600.0)

        assert cache.ttl_seconds == 600.0

    def test_get_global_cache_ignores_ttl_on_existing(self):
        """Test that TTL is ignored if cache already exists."""
        import core.tool_cache

        core.tool_cache._global_cache = None

        cache1 = get_global_cache(ttl_seconds=300.0)
        cache2 = get_global_cache(ttl_seconds=600.0)

        # Should still be 300 (from first call)
        assert cache2.ttl_seconds == 300.0
        assert cache1 is cache2
