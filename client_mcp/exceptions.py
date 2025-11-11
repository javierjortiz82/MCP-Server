"""Domain-specific exceptions for Client MCP Service.

This module provides a hierarchy of custom exceptions for different error domains
in the MCP client system. These exceptions enable precise error handling and better
error reporting across the application.

Exception Hierarchy:
    ClientError (base)
        ├── ConnectionError      - MCP server connection failures
        ├── TimeoutError         - Operation timeout
        ├── ConfigError          - Configuration loading/validation failures
        ├── StrategyError        - Retry/fallback strategy failures
        ├── ValidationError      - Input/output validation failures
        ├── ToolError            - Tool execution failures
        └── ServerError          - MCP server-side errors

This module complements the existing ErrorContext-based error handling in
utils/error_handler.py by providing more specific exception types.

Usage Example:
    >>> from client_mcp.exceptions import ConnectionError, StrategyError
    >>> try:
    ...     client = MCPClient()
    ...     await client.connect()
    ... except ConnectionError as e:
    ...     logger.error(f"Failed to connect to MCP server: {e}")
    ... except StrategyError as e:
    ...     logger.error(f"Strategy execution failed: {e}")

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from typing import Any, Optional


class ClientError(Exception):
    """Base exception for all client MCP-related errors.

    This is the root exception class for the client system. All domain-specific
    exceptions inherit from this class.

    Attributes:
        message: Error description
        error_code: Optional error code for categorization
        context: Optional context dictionary with additional information
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ClientError.

        Args:
            message: Human-readable error message
            error_code: Optional error code (e.g., "CONN_001")
            context: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}

    def __str__(self) -> str:
        """String representation of the error."""
        base = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} (context: {context_str})"
        return base


class ConnectionError(ClientError):
    """MCP server connection has failed.

    This exception is raised when:
    - Cannot connect to MCP server
    - Connection is lost during operation
    - Connection negotiation fails
    - WebSocket/transport layer fails

    Example:
        >>> raise ConnectionError(
        ...     message="Failed to connect to MCP server",
        ...     error_code="CONN_001",
        ...     context={"host": "localhost", "port": 8080, "reason": "Connection refused"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CONN_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ConnectionError."""
        super().__init__(message, error_code, context)


class TimeoutError(ClientError):
    """Operation timeout has occurred.

    This exception is raised when:
    - Tool execution exceeds timeout
    - Server response takes too long
    - Connection handshake times out
    - Retry strategy times out

    Example:
        >>> raise TimeoutError(
        ...     message="Tool execution timeout",
        ...     error_code="TIMEOUT_001",
        ...     context={"tool": "get_services", "timeout_seconds": 30}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "TIMEOUT_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize TimeoutError."""
        super().__init__(message, error_code, context)


class ConfigError(ClientError):
    """Configuration loading or validation has failed.

    This exception is raised when:
    - Configuration files are missing or invalid
    - Environment variables are not set
    - Pydantic validation fails
    - Settings have invalid values
    - Configuration schema is violated

    Example:
        >>> raise ConfigError(
        ...     message="Missing required configuration",
        ...     error_code="CONFIG_001",
        ...     context={"required_var": "MCP_SERVER_URL", "env": "production"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIG_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ConfigError."""
        super().__init__(message, error_code, context)


class StrategyError(ClientError):
    """Retry or fallback strategy execution has failed.

    This exception is raised when:
    - Retry strategy exhausts all attempts
    - Fallback strategy fails
    - Strategy configuration is invalid
    - Strategy decision cannot be made

    Example:
        >>> raise StrategyError(
        ...     message="Retry strategy exhausted",
        ...     error_code="STRAT_001",
        ...     context={"strategy": "exponential_backoff", "attempts": 5}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "STRAT_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize StrategyError."""
        super().__init__(message, error_code, context)


class ValidationError(ClientError):
    """Input or output validation has failed.

    This exception is raised when:
    - Input parameters are invalid
    - Output from server doesn't match schema
    - Required fields are missing
    - Type validation fails
    - Data constraints are violated

    Example:
        >>> raise ValidationError(
        ...     message="Invalid tool parameters",
        ...     error_code="VAL_001",
        ...     context={"tool": "search", "missing_field": "query"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ValidationError."""
        super().__init__(message, error_code, context)


class ToolError(ClientError):
    """Tool execution has failed.

    This exception is raised when:
    - Tool returns an error
    - Tool is not available or not found
    - Tool parameters are invalid
    - Tool execution times out
    - Tool returns invalid output

    Example:
        >>> raise ToolError(
        ...     message="Tool execution failed",
        ...     error_code="TOOL_001",
        ...     context={"tool": "search_products", "reason": "Database unavailable"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "TOOL_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ToolError."""
        super().__init__(message, error_code, context)


class ServerError(ClientError):
    """MCP server-side error has occurred.

    This exception is raised when:
    - Server returns HTTP 5xx error
    - Server returns RPC error
    - Server is unavailable or down
    - Server response is invalid
    - Server-side resource is exhausted

    Example:
        >>> raise ServerError(
        ...     message="MCP server internal error",
        ...     error_code="SERVER_001",
        ...     context={"status_code": 500, "reason": "Database connection lost"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "SERVER_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ServerError."""
        super().__init__(message, error_code, context)
