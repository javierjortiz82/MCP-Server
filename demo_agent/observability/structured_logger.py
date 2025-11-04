"""Structured logging with context integration.

Integrates structured logging with correlation IDs and request context.
Automatically includes request context in all log records.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import json
import logging
from typing import Any, Dict, Optional

from demo_agent.observability.context import get_request_context
from demo_agent.observability.correlation import CorrelationID


class StructuredLogFormatter(logging.Formatter):
    """Formats logs as JSON with structured context.

    Automatically includes:
    - Correlation ID
    - Request context (user_key, IP, etc.)
    - Timestamp
    - Log level
    - Message
    - Additional fields

    Example:
        >>> handler = logging.StreamHandler()
        >>> formatter = StructuredLogFormatter()
        >>> handler.setFormatter(formatter)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: LogRecord to format

        Returns:
            JSON-formatted log string
        """
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID
        corr_id = CorrelationID.get()
        if corr_id:
            log_data["correlation_id"] = corr_id

        # Add request context
        ctx = get_request_context()
        if ctx:
            log_data["context"] = {
                "user_key": ctx.user_key,
                "ip_address": ctx.ip_address,
                "method": ctx.method,
                "path": ctx.path,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "getMessage",
                ]:
                    if not key.startswith("_"):
                        log_data[key] = value

        return json.dumps(log_data)


class StructuredLogger:
    """Structured logger with context integration.

    Wraps Python's logging module to automatically include
    correlation IDs and request context in logs.

    Example:
        >>> from demo_agent.observability.structured_logger import get_structured_logger
        >>> logger = get_structured_logger(__name__)
        >>> logger.info("Processing request", user_key="user_123")
    """

    def __init__(self, name: str):
        """Initialize structured logger.

        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)
        self.name = name

    def _add_context(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Add request context to log kwargs.

        Args:
            kwargs: Additional log fields

        Returns:
            Updated kwargs with context
        """
        # Add correlation ID if not already present
        if "correlation_id" not in kwargs:
            corr_id = CorrelationID.get()
            if corr_id:
                kwargs["correlation_id"] = corr_id

        # Add request context fields if not already present
        ctx = get_request_context()
        if ctx:
            if "user_key" not in kwargs and ctx.user_key:
                kwargs["user_key"] = ctx.user_key
            if "ip_address" not in kwargs and ctx.ip_address:
                kwargs["ip_address"] = ctx.ip_address
            if "method" not in kwargs and ctx.method:
                kwargs["method"] = ctx.method
            if "path" not in kwargs and ctx.path:
                kwargs["path"] = ctx.path

        return kwargs

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.error(message, extra=kwargs)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.exception(message, extra=kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log
        """
        kwargs = self._add_context(kwargs)
        self.logger.critical(message, extra=kwargs)


# Global structured logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_structured_logger(name: str) -> StructuredLogger:
    """Get or create structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Example:
        >>> from demo_agent.observability.structured_logger import get_structured_logger
        >>> logger = get_structured_logger(__name__)
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]
