"""Tool cache for autodiscovered MCP tools and schemas.

This module provides caching mechanisms for MCP tool discovery to avoid
repeated network calls and improve performance.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CachedTool:
    """Cached MCP tool with metadata."""

    name: str
    description: str
    input_schema: dict[str, Any]
    callable_wrapper: Callable[..., Any] | None = None
    cached_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if cache entry is expired.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired, False otherwise
        """
        return (time.time() - self.cached_at) > ttl_seconds


@dataclass
class ToolsSnapshot:
    """Snapshot of all discovered tools at a point in time."""

    tools: list[CachedTool]
    tool_wrappers: list[Callable[..., Any]]
    cached_at: float = field(default_factory=time.time)

    def is_expired(self, ttl_seconds: float) -> bool:
        """Check if snapshot is expired.

        Args:
            ttl_seconds: Time-to-live in seconds

        Returns:
            True if expired, False otherwise
        """
        return (time.time() - self.cached_at) > ttl_seconds


class ToolCache:
    """Cache for MCP tool discovery and schemas.

    Provides in-memory caching with TTL (time-to-live) to reduce
    redundant network calls to MCP server for tool discovery.

    Example:
        cache = ToolCache(ttl_seconds=300)  # 5 minutes TTL

        # First call - hits MCP server
        if not cache.has_valid_snapshot():
            tools = await mcp_client.list_tools()
            cache.cache_snapshot(tools, wrappers)

        # Subsequent calls - uses cache
        snapshot = cache.get_snapshot()
    """

    def __init__(self, ttl_seconds: float = 300.0):
        """Initialize tool cache.

        Args:
            ttl_seconds: Time-to-live for cache entries (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._tools_by_name: dict[str, CachedTool] = {}
        self._snapshot: ToolsSnapshot | None = None

    def cache_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        callable_wrapper: Callable[..., Any] | None = None,
    ) -> None:
        """Cache a single tool.

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON Schema for tool parameters
            callable_wrapper: Optional callable wrapper function
        """
        cached_tool = CachedTool(
            name=name,
            description=description,
            input_schema=input_schema,
            callable_wrapper=callable_wrapper,
        )
        self._tools_by_name[name] = cached_tool

    def cache_snapshot(
        self,
        tools_definitions: list[dict[str, Any]],
        tool_wrappers: list[Callable[..., Any]],
    ) -> None:
        """Cache a complete snapshot of all discovered tools.

        Args:
            tools_definitions: List of tool definitions from MCP server
            tool_wrappers: List of callable wrappers for tools
        """
        # Clear existing cache
        self._tools_by_name.clear()

        # Cache individual tools
        cached_tools: list[CachedTool] = []

        for i, tool_def in enumerate(tools_definitions):
            wrapper = tool_wrappers[i] if i < len(tool_wrappers) else None

            cached_tool = CachedTool(
                name=tool_def["name"],
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {}),
                callable_wrapper=wrapper,
            )

            cached_tools.append(cached_tool)
            self._tools_by_name[cached_tool.name] = cached_tool

        # Create snapshot
        self._snapshot = ToolsSnapshot(tools=cached_tools, tool_wrappers=tool_wrappers)

    def get_tool(self, name: str) -> CachedTool | None:
        """Get a cached tool by name.

        Args:
            name: Tool name

        Returns:
            CachedTool if found and valid, None otherwise
        """
        tool = self._tools_by_name.get(name)

        if tool and not tool.is_expired(self.ttl_seconds):
            return tool

        # Remove expired tool
        if tool:
            del self._tools_by_name[name]

        return None

    def get_snapshot(self) -> ToolsSnapshot | None:
        """Get cached snapshot of all tools.

        Returns:
            ToolsSnapshot if valid, None if expired or not cached
        """
        if self._snapshot and not self._snapshot.is_expired(self.ttl_seconds):
            return self._snapshot

        # Clear expired snapshot
        if self._snapshot:
            self._snapshot = None
            self._tools_by_name.clear()

        return None

    def has_valid_snapshot(self) -> bool:
        """Check if cache has a valid snapshot.

        Returns:
            True if valid snapshot exists, False otherwise
        """
        return self.get_snapshot() is not None

    def get_all_tools(self) -> list[CachedTool]:
        """Get all cached tools that are still valid.

        Returns:
            List of valid CachedTool instances
        """
        valid_tools: list[CachedTool] = []
        expired_names: list[str] = []

        for name, tool in self._tools_by_name.items():
            if tool.is_expired(self.ttl_seconds):
                expired_names.append(name)
            else:
                valid_tools.append(tool)

        # Clean up expired tools
        for name in expired_names:
            del self._tools_by_name[name]

        return valid_tools

    def get_tool_names(self) -> list[str]:
        """Get list of all cached tool names.

        Returns:
            List of tool names
        """
        return list(self._tools_by_name.keys())

    def invalidate_tool(self, name: str) -> None:
        """Invalidate a specific tool in cache.

        Args:
            name: Tool name to invalidate
        """
        if name in self._tools_by_name:
            del self._tools_by_name[name]

    def invalidate_all(self) -> None:
        """Invalidate all cached tools and snapshot."""
        self._tools_by_name.clear()
        self._snapshot = None

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_tools = len(self._tools_by_name)
        valid_tools = len(self.get_all_tools())
        expired_tools = total_tools - valid_tools

        snapshot_age = time.time() - self._snapshot.cached_at if self._snapshot else None

        return {
            "total_tools_cached": total_tools,
            "valid_tools": valid_tools,
            "expired_tools": expired_tools,
            "has_valid_snapshot": self.has_valid_snapshot(),
            "snapshot_age_seconds": snapshot_age,
            "ttl_seconds": self.ttl_seconds,
        }

    def set_ttl(self, ttl_seconds: float) -> None:
        """Update TTL for cache entries.

        Args:
            ttl_seconds: New time-to-live in seconds
        """
        self.ttl_seconds = ttl_seconds


# Global singleton instance
_global_cache: ToolCache | None = None


def get_global_cache(ttl_seconds: float = 300.0) -> ToolCache:
    """Get or create global tool cache instance.

    Args:
        ttl_seconds: Time-to-live for cache (default: 5 minutes)

    Returns:
        Global ToolCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = ToolCache(ttl_seconds=ttl_seconds)
    return _global_cache
