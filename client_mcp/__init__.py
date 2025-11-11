"""Client MCP module.

This package provides a standardized MCP client with connection pooling,
retry strategies, tool caching, and comprehensive error handling.

Exceptions:
    ClientError: Base exception for all client errors
    ConnectionError: Connection to MCP server failed
    TimeoutError: Operation timeout
    ConfigError: Configuration error
    StrategyError: Retry/fallback strategy failed
    ValidationError: Input/output validation failed
    ToolError: Tool execution failed
    ServerError: MCP server error
"""

from client_mcp.exceptions import (
    ClientError,
    ConfigError,
    ConnectionError,
    ServerError,
    StrategyError,
    TimeoutError,
    ToolError,
    ValidationError,
)

__all__ = [
    "ClientError",
    "ConfigError",
    "ConnectionError",
    "ServerError",
    "StrategyError",
    "TimeoutError",
    "ToolError",
    "ValidationError",
]
