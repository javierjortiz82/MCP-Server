"""Request/operation context management for structured logging.

Provides contextvars-based request context for async-safe propagation of request
metadata (user info, IP address, operation metadata) across async task boundaries.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from email_service.observability.correlation import CorrelationID

# Global context variable for storing request context
_request_context_var: ContextVar[Optional["RequestContext"]] = ContextVar(
    "request_context", default=None
)


@dataclass
class RequestContext:
    """Request/operation context for structured logging.

    Encapsulates metadata about the current request/operation for automatic
    inclusion in all log messages and metrics. Uses dataclass for clean, efficient storage.

    Attributes:
        correlation_id: UUID4 for request tracing
        email_id: Email record ID (if applicable)
        recipient: Recipient email address
        operation: Current operation name
        started_at: Timestamp when context created
        custom_fields: Additional metadata as key-value pairs

    Example:
        >>> ctx = RequestContext(
        ...     correlation_id="trace-123",
        ...     email_id=456,
        ...     recipient="user@example.com",
        ...     operation="send_email"
        ... )
        >>> ctx.to_dict()
        {'correlation_id': 'trace-123', 'email_id': 456, 'recipient': 'user@example.com', ...}
    """

    correlation_id: Optional[str] = None
    email_id: Optional[int] = None
    recipient: Optional[str] = None
    operation: Optional[str] = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    custom_fields: dict[str, Any] = field(default_factory=dict)

    def add_field(self, key: str, value: Any) -> None:
        """Add a custom field to context.

        Args:
            key: Field name
            value: Field value

        Example:
            >>> ctx.add_field("smtp_host", "smtp.gmail.com")
            >>> ctx.get_field("smtp_host")
            'smtp.gmail.com'
        """
        self.custom_fields[key] = value

    def get_field(self, key: str, default: Any = None) -> Any:
        """Get a custom field from context.

        Args:
            key: Field name
            default: Default value if key not found

        Returns:
            Field value or default

        Example:
            >>> ctx.get_field("retry_count", 0)
            0
        """
        return self.custom_fields.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for logging.

        Returns:
            dict: Context as flat dictionary

        Example:
            >>> ctx = RequestContext(correlation_id="trace-123", email_id=456)
            >>> ctx.to_dict()
            {'correlation_id': 'trace-123', 'email_id': 456, 'started_at': ..., ...}
        """
        return {
            "correlation_id": self.correlation_id,
            "email_id": self.email_id,
            "recipient": self.recipient,
            "operation": self.operation,
            "started_at": self.started_at.isoformat(),
            **self.custom_fields,
        }


def create_request_context(
    email_id: Optional[int] = None,
    recipient: Optional[str] = None,
    operation: Optional[str] = None,
    **kwargs,
) -> RequestContext:
    """Create and set a new request context.

    Generates new correlation ID if not already set, creates RequestContext,
    sets it in contextvars, and returns it.

    Args:
        email_id: Email record ID
        recipient: Recipient email address
        operation: Operation name
        **kwargs: Additional custom fields

    Returns:
        RequestContext: Created context

    Example:
        >>> ctx = create_request_context(
        ...     email_id=123,
        ...     recipient="user@example.com",
        ...     operation="send_otp"
        ... )
        >>> get_request_context() == ctx
        True
    """
    correlation_id = CorrelationID.get_or_generate()

    ctx = RequestContext(
        correlation_id=correlation_id,
        email_id=email_id,
        recipient=recipient,
        operation=operation,
        custom_fields=kwargs,
    )

    set_request_context(ctx)
    return ctx


def set_request_context(context: Optional[RequestContext]) -> None:
    """Set the request context for current async context.

    Args:
        context: RequestContext to set or None to clear

    Example:
        >>> ctx = RequestContext(correlation_id="trace-123")
        >>> set_request_context(ctx)
        >>> get_request_context() == ctx
        True
    """
    _request_context_var.set(context)


def get_request_context() -> Optional[RequestContext]:
    """Get the current request context.

    Returns:
        RequestContext | None: Current context or None if not set

    Example:
        >>> ctx = create_request_context(email_id=123)
        >>> get_request_context().email_id
        123
    """
    return _request_context_var.get()


def clear_request_context() -> None:
    """Clear the request context from current async context.

    Also clears the correlation ID.

    Example:
        >>> create_request_context(email_id=123)
        >>> clear_request_context()
        >>> get_request_context() is None
        True
    """
    _request_context_var.set(None)
    CorrelationID.clear()
