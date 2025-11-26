"""Correlation ID management for request tracing.

Generates and manages correlation IDs to track requests across services,
databases, and logs. Each request gets a unique correlation ID that is
propagated through the entire request lifecycle.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import contextvars
import uuid

# Context variable for storing correlation ID
_correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


class CorrelationID:
    """Manages correlation IDs for request tracing.

    A correlation ID is a unique identifier assigned to each request
    that allows tracing the request through all services and logs.

    Features:
    - Auto-generates UUIDs if not provided
    - Supports custom format (e.g., batch IDs, transaction IDs)
    - Uses context variables for async-safe storage
    - Integrates with structured logging

    Example:
        >>> from demo_agent.observability.correlation import generate_correlation_id
        >>> corr_id = generate_correlation_id()
        >>> # Use in logs: logger.info("Processing request", correlation_id=corr_id)
    """

    @staticmethod
    def set(correlation_id: str) -> None:
        """Set correlation ID for current context.

        Args:
            correlation_id: Unique identifier for this request
        """
        _correlation_id_var.set(correlation_id)

    @staticmethod
    def get() -> str | None:
        """Get correlation ID from current context.

        Returns:
            Correlation ID or None if not set

        Example:
            >>> corr_id = CorrelationID.get()
            >>> if corr_id:
            ...     logger.info(f"Request: {corr_id}")
        """
        return _correlation_id_var.get()

    @staticmethod
    def generate() -> str:
        """Generate a new correlation ID.

        Returns:
            UUID4 string for new correlation ID

        Example:
            >>> corr_id = CorrelationID.generate()
            >>> CorrelationID.set(corr_id)
        """
        return str(uuid.uuid4())

    @staticmethod
    def get_or_generate() -> str:
        """Get existing correlation ID or generate a new one.

        Returns:
            Existing correlation ID or newly generated UUID4

        Example:
            >>> corr_id = CorrelationID.get_or_generate()
            >>> # Always returns a valid correlation ID
        """
        existing = CorrelationID.get()
        if existing:
            return existing

        new_id = CorrelationID.generate()
        CorrelationID.set(new_id)
        return new_id

    @staticmethod
    def clear() -> None:
        """Clear correlation ID from context.

        Used when request context ends.
        """
        _correlation_id_var.set(None)


def generate_correlation_id() -> str:
    """Generate new correlation ID and set in context.

    This is a convenience function for common use case.

    Returns:
        UUID4 string

    Example:
        >>> from demo_agent.observability.correlation import generate_correlation_id
        >>> corr_id = generate_correlation_id()
        >>> # Correlation ID is now set in context
    """
    return CorrelationID.get_or_generate()
