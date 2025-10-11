"""Execution strategies for resilience and error handling."""

from .fallback import FallbackStrategy
from .retry import RetryStrategy

__all__ = ["RetryStrategy", "FallbackStrategy"]
