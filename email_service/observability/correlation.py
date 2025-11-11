"""Correlation ID management for distributed request tracing.

Provides contextvars-based correlation ID storage for end-to-end request tracking
across async operations without task-local storage leaks.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from contextvars import ContextVar
from uuid import uuid4

# Global context variable for storing correlation ID
_correlation_id_var: ContextVar[str | None] = ContextVar(
    "correlation_id", default=None
)


class CorrelationID:
    """Context-safe correlation ID management.

    Uses contextvars to maintain correlation IDs across async task boundaries.
    Each task/request gets its own correlation ID that can be used for tracing.

    Example:
        >>> CorrelationID.set("request-123")
        >>> request_id = CorrelationID.get()  # "request-123"
        >>> new_id = CorrelationID.get_or_generate()  # Returns "request-123"
        >>> CorrelationID.clear()
    """

    @staticmethod
    def generate() -> str:
        """Generate a new UUID4-based correlation ID.

        Returns:
            str: New UUID4 correlation ID

        Example:
            >>> corr_id = CorrelationID.generate()
            >>> len(corr_id)
            36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        """
        return str(uuid4())

    @staticmethod
    def set(correlation_id: str) -> None:
        """Set the correlation ID for current context.

        Args:
            correlation_id: UUID4 or custom correlation ID string

        Example:
            >>> CorrelationID.set("trace-abc123")
        """
        _correlation_id_var.set(correlation_id)

    @staticmethod
    def get() -> str | None:
        """Get the current correlation ID.

        Returns:
            str | None: Current correlation ID or None if not set

        Example:
            >>> CorrelationID.set("trace-xyz")
            >>> CorrelationID.get()
            'trace-xyz'
        """
        return _correlation_id_var.get()

    @staticmethod
    def get_or_generate() -> str:
        """Get existing correlation ID or generate new one.

        Returns:
            str: Existing correlation ID or newly generated UUID4

        Example:
            >>> CorrelationID.set("trace-123")
            >>> CorrelationID.get_or_generate()
            'trace-123'  # Returns existing

            >>> CorrelationID.clear()
            >>> CorrelationID.get_or_generate()
            'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'  # New UUID4
        """
        existing = _correlation_id_var.get()
        if existing:
            return existing

        new_id = CorrelationID.generate()
        _correlation_id_var.set(new_id)
        return new_id

    @staticmethod
    def clear() -> None:
        """Clear the correlation ID from current context.

        Example:
            >>> CorrelationID.set("trace-123")
            >>> CorrelationID.clear()
            >>> CorrelationID.get()
            None
        """
        _correlation_id_var.set(None)


def generate_correlation_id() -> str:
    """Convenience function to generate and set a new correlation ID.

    Generates a new UUID4, sets it in the context, and returns it.

    Returns:
        str: Generated correlation ID

    Example:
        >>> corr_id = generate_correlation_id()
        >>> CorrelationID.get() == corr_id
        True
    """
    new_id = CorrelationID.generate()
    CorrelationID.set(new_id)
    return new_id
