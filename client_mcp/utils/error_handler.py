"""Standardized error handling utilities for the client MCP.

This module provides decorators and utilities for consistent error handling
across the entire codebase, following enterprise best practices.
"""

import logging
import traceback
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorContext(Enum):
    """Define error contexts for different layers of the application."""

    SERVICE = "service"
    API = "api"
    DATABASE = "database"
    TOOL = "tool"
    UTILITY = "utility"


class ApplicationError(Exception):
    """Base exception class for application-specific errors."""

    def __init__(
        self,
        message: str,
        context: ErrorContext | None = None,
        details: dict | None = None,
    ):
        """Initialize application error with context.

        Args:
            message: Error message
            context: Error context (service, api, database, etc.)
            details: Additional error details
        """
        super().__init__(message)
        self.context = context
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert error to dictionary for API responses."""
        return {
            "error": self.__class__.__name__,
            "message": str(self),
            "context": self.context.value if self.context else None,
            "details": self.details,
        }


class ValidationError(ApplicationError):
    """Raised when input validation fails."""

    pass


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""

    pass


class ExternalServiceError(ApplicationError):
    """Raised when an external service call fails."""

    pass


class DatabaseError(ApplicationError):
    """Raised when a database operation fails."""

    pass


def handle_service_errors[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for service layer error handling.

    Service layer should log and re-raise with context.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)  # type: ignore[misc]
        except ApplicationError:
            # Application errors pass through
            raise
        except Exception as e:
            logger.exception(f"Service error in {func.__name__}: {e}")
            raise ApplicationError(
                f"Service operation failed: {e}",
                context=ErrorContext.SERVICE,
                details={"function": func.__name__, "original_error": str(e)},
            ) from e

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ApplicationError:
            # Application errors pass through
            raise
        except Exception as e:
            logger.exception(f"Service error in {func.__name__}: {e}")
            raise ApplicationError(
                f"Service operation failed: {e}",
                context=ErrorContext.SERVICE,
                details={"function": func.__name__, "original_error": str(e)},
            ) from e

    # Return appropriate wrapper based on function type
    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def handle_api_errors[T](func: Callable[..., T]) -> Callable[..., T | dict[str, Any]]:
    """Decorator for API layer error handling.

    API layer should catch, log, and return user-friendly error.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T | dict[str, Any]:
        try:
            return await func(*args, **kwargs)  # type: ignore[misc]
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {e}")
            # Return user-friendly validation error
            return {"error": "Invalid input", "message": str(e), "details": e.details}
        except ResourceNotFoundError as e:
            logger.error(f"Resource not found in {func.__name__}: {e}")
            return {"error": "Not found", "message": str(e)}
        except ApplicationError as e:
            logger.error(f"Application error in {func.__name__}: {e}")
            return {"error": "Operation failed", "message": str(e)}
        except Exception:
            logger.exception(f"Unexpected error in {func.__name__}")
            # Never expose internal errors to users
            return {
                "error": "Internal error",
                "message": "An unexpected error occurred",
            }

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T | dict[str, Any]:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Validation error in {func.__name__}: {e}")
            return {"error": "Invalid input", "message": str(e), "details": e.details}
        except ResourceNotFoundError as e:
            logger.error(f"Resource not found in {func.__name__}: {e}")
            return {"error": "Not found", "message": str(e)}
        except ApplicationError as e:
            logger.error(f"Application error in {func.__name__}: {e}")
            return {"error": "Operation failed", "message": str(e)}
        except Exception:
            logger.exception(f"Unexpected error in {func.__name__}")
            return {
                "error": "Internal error",
                "message": "An unexpected error occurred",
            }

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def handle_database_errors[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for database layer error handling.

    Database layer should wrap database-specific errors.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Check for known database errors
            error_str = str(e)
            if "psycopg2" in error_str or "connection" in error_str.lower():
                logger.exception(f"Database error in {func.__name__}: {e}")
                raise DatabaseError(
                    "Database operation failed",
                    context=ErrorContext.DATABASE,
                    details={"function": func.__name__, "error_type": type(e).__name__},
                ) from e
            # Re-raise non-database errors
            raise

    return wrapper


def handle_tool_errors[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for tool execution error handling.

    Tool layer should provide detailed error context for debugging.
    Re-raises exceptions, does not return error dicts.
    """

    @wraps(func)
    async def async_wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)  # type: ignore[misc]
        except ValidationError as e:
            logger.error(f"Tool validation failed in {func.__name__}: {e}")
            raise ValidationError(
                f"Invalid tool parameters: {e}",
                context=ErrorContext.TOOL,
                details={"tool": func.__name__, "validation_error": str(e)},
            ) from e
        except Exception as e:
            logger.exception(f"Tool execution failed in {func.__name__}")
            raise ApplicationError(
                f"Tool execution failed: {e}",
                context=ErrorContext.TOOL,
                details={"tool": func.__name__, "error_type": type(e).__name__},
            ) from e

    @wraps(func)
    def sync_wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.error(f"Tool validation failed in {func.__name__}: {e}")
            raise ValidationError(
                f"Invalid tool parameters: {e}",
                context=ErrorContext.TOOL,
                details={"tool": func.__name__, "validation_error": str(e)},
            ) from e
        except Exception as e:
            logger.exception(f"Tool execution failed in {func.__name__}")
            raise ApplicationError(
                f"Tool execution failed: {e}",
                context=ErrorContext.TOOL,
                details={"tool": func.__name__, "error_type": type(e).__name__},
            ) from e

    import asyncio

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


def handle_utility_errors[T](func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for utility function error handling.

    Utility functions should re-raise with wrapped exceptions.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Utility error in {func.__name__}: {e}")
            raise ApplicationError(
                f"Utility operation failed in {func.__name__}: {e}",
                context=ErrorContext.UTILITY,
                details={
                    "function": func.__name__,
                    "traceback": traceback.format_exc(),
                },
            ) from e

    return wrapper


def safe_fallback(default_value: Any = None):
    """Decorator that returns a default value on error.

    Use sparingly - only for non-critical operations where failure is acceptable.

    Args:
        default_value: Value to return on error
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T | Any]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T | Any:
            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            except Exception as e:
                logger.warning(
                    f"Function {func.__name__} failed, returning default: {e}"
                )
                return default_value

        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T | Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Function {func.__name__} failed, returning default: {e}"
                )
                return default_value

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator
