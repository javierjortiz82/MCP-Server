"""Retry strategy with exponential backoff for tool execution.

This module provides retry mechanisms for handling transient failures
in MCP tool execution with configurable backoff strategies.
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_ms: float = 100.0
    max_delay_ms: float = 5000.0
    exponential_base: float = 2.0
    jitter: bool = True


class RetryStrategy:
    """Retry strategy with exponential backoff.

    Implements retry logic for transient failures with:
    - Exponential backoff
    - Configurable max attempts
    - Optional jitter to prevent thundering herd
    - Selective retry based on exception type

    Example:
        strategy = RetryStrategy(max_attempts=3)

        result = await strategy.execute_with_retry(
            lambda: mcp_client.call_tool("search", {"query": "laptop"})
        )
    """

    def __init__(self, config: RetryConfig | None = None, logger: logging.Logger | None = None):
        """Initialize retry strategy.

        Args:
            config: Retry configuration (uses defaults if None)
            logger: Optional logger for retry events
        """
        self.config = config or RetryConfig()
        self.logger = logger or logging.getLogger(__name__)

    async def execute_with_retry(
        self,
        func: Callable[[], Any],
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> Any:
        """Execute function with retry logic.

        Args:
            func: Async callable to execute
            retryable_exceptions: Tuple of exception types to retry on

        Returns:
            Result from successful execution

        Raises:
            Last exception if all retries exhausted
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                # Execute function
                result = await func()
                return result

            except retryable_exceptions as e:
                last_exception = e

                # Don't retry on last attempt
                if attempt == self.config.max_attempts:
                    self.logger.error(f"All {self.config.max_attempts} retry attempts failed. Last error: {e}")
                    break

                # Calculate backoff delay
                delay_ms = self._calculate_backoff(attempt)

                self.logger.warning(
                    f"Attempt {attempt}/{self.config.max_attempts} failed: {e}. Retrying in {delay_ms:.0f}ms..."
                )

                # Wait before retry
                await asyncio.sleep(delay_ms / 1000.0)

        # Raise last exception if all retries failed
        if last_exception:
            raise last_exception

        # Should never reach here
        raise RuntimeError("Retry logic completed without success or exception")

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate backoff delay for given attempt.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in milliseconds
        """
        # Exponential backoff: initial_delay * (base ^ (attempt - 1))
        delay = self.config.initial_delay_ms * (self.config.exponential_base ** (attempt - 1))

        # Cap at max delay
        delay = min(delay, self.config.max_delay_ms)

        # Add jitter if enabled (random ±25%)
        if self.config.jitter:
            import random

            jitter_factor = random.uniform(0.75, 1.25)
            delay *= jitter_factor

        return delay

    def is_retryable_error(self, exception: Exception) -> bool:
        """Determine if an exception is retryable.

        Args:
            exception: Exception to check

        Returns:
            True if retryable, False otherwise
        """
        # Network/timeout errors are retryable
        retryable_patterns = [
            "timeout",
            "connection",
            "network",
            "temporary",
            "transient",
            "unavailable",
        ]

        error_message = str(exception).lower()

        return any(pattern in error_message for pattern in retryable_patterns)


async def retry_with_backoff[T](
    func: Callable[[], T],
    max_attempts: int = 3,
    initial_delay_ms: float = 100.0,
    max_delay_ms: float = 5000.0,
) -> T:
    """Convenience function for simple retry with exponential backoff.

    Args:
        func: Async callable to execute
        max_attempts: Maximum retry attempts
        initial_delay_ms: Initial delay in milliseconds
        max_delay_ms: Maximum delay in milliseconds

    Returns:
        Result from successful execution

    Raises:
        Last exception if all retries exhausted

    Example:
        result = await retry_with_backoff(
            lambda: client.call_tool("search", {"query": "laptop"}),
            max_attempts=3
        )
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay_ms=initial_delay_ms,
        max_delay_ms=max_delay_ms,
    )

    strategy = RetryStrategy(config)

    return await strategy.execute_with_retry(func)
