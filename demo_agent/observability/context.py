"""Request context management for structured logging.

Maintains request-level context (correlation ID, user, IP, etc.)
across async operations using context variables.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import contextvars
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from demo_agent.observability.correlation import CorrelationID

# Context variable for storing request context
_request_context_var: contextvars.ContextVar[Optional["RequestContext"]] = contextvars.ContextVar(
    "request_context", default=None
)


@dataclass
class RequestContext:
    """Context information for a request.

    Stores request-level information that should be included in logs.
    Uses dataclass for efficient storage and type safety.

    Attributes:
        correlation_id: Unique request identifier
        user_key: User identifier (user_id, session_id, or fingerprint)
        ip_address: Client IP address
        user_agent: HTTP User-Agent header
        method: HTTP method (GET, POST, etc.)
        path: Request path
        started_at: Request start time
        extra: Additional custom fields
    """

    correlation_id: str
    user_key: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    method: str | None = None
    path: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging.

        Returns:
            Dictionary representation of context
        """
        return {
            "correlation_id": self.correlation_id,
            "user_key": self.user_key,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "method": self.method,
            "path": self.path,
            "started_at": self.started_at.isoformat(),
            **self.extra,
        }

    def add_field(self, key: str, value: Any) -> None:
        """Add custom field to context.

        Args:
            key: Field name
            value: Field value

        Example:
            >>> ctx = RequestContext(correlation_id="abc-123")
            >>> ctx.add_field("tokens_used", 250)
        """
        self.extra[key] = value

    def get_field(self, key: str, default: Any = None) -> Any:
        """Get custom field from context.

        Args:
            key: Field name
            default: Default value if field not found

        Returns:
            Field value or default
        """
        return self.extra.get(key, default)


def set_request_context(context: RequestContext) -> None:
    """Set request context for current async context.

    Args:
        context: RequestContext object

    Example:
        >>> ctx = RequestContext(
        ...     correlation_id="abc-123",
        ...     user_key="user_123",
        ...     ip_address="203.0.113.42"
        ... )
        >>> set_request_context(ctx)
    """
    _request_context_var.set(context)
    # Also update correlation ID in CorrelationID context
    CorrelationID.set(context.correlation_id)


def get_request_context() -> RequestContext | None:
    """Get request context from current async context.

    Returns:
        RequestContext or None if not set

    Example:
        >>> ctx = get_request_context()
        >>> if ctx:
        ...     logger.info(f"Request: {ctx.correlation_id}")
    """
    return _request_context_var.get()


def create_request_context(
    correlation_id: str | None = None,
    user_key: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> RequestContext:
    """Create and set request context.

    This is a convenience function that creates context and sets it.

    Args:
        correlation_id: Unique request identifier (auto-generated if None)
        user_key: User identifier
        ip_address: Client IP address
        user_agent: HTTP User-Agent header
        method: HTTP method
        path: Request path

    Returns:
        Created and set RequestContext

    Example:
        >>> ctx = create_request_context(
        ...     user_key="user_123",
        ...     ip_address="203.0.113.42",
        ...     method="POST",
        ...     path="/api/demo"
        ... )
    """
    if not correlation_id:
        correlation_id = CorrelationID.generate()

    context = RequestContext(
        correlation_id=correlation_id,
        user_key=user_key,
        ip_address=ip_address,
        user_agent=user_agent,
        method=method,
        path=path,
    )
    set_request_context(context)
    return context


def clear_request_context() -> None:
    """Clear request context from current async context.

    Called when request processing ends.
    """
    _request_context_var.set(None)
    CorrelationID.clear()
