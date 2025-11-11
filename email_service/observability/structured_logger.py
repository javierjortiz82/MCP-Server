"""Structured logging with context integration for email service.

Integrates structured logging with correlation IDs and request context.
Automatically includes request context in all log records as JSON.

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import json
import logging
from typing import Any, Dict, Optional

from email_service.observability.context import get_request_context
from email_service.observability.correlation import CorrelationID


class StructuredLogFormatter(logging.Formatter):
    """Formats logs as JSON with structured context.

    Automatically includes:
    - Correlation ID
    - Request context (email_id, recipient, operation, etc.)
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
                "email_id": ctx.email_id,
                "recipient": ctx.recipient,
                "operation": ctx.operation,
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
    """Structured logger with context integration for email service.

    Wraps Python's logging module to automatically include
    correlation IDs and request context in logs.

    Example:
        >>> from email_service.observability.structured_logger import get_structured_logger
        >>> logger = get_structured_logger(__name__)
        >>> logger.info("Sending email", recipient="user@example.com", email_id=123)
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
            if "email_id" not in kwargs and ctx.email_id:
                kwargs["email_id"] = ctx.email_id
            if "recipient" not in kwargs and ctx.recipient:
                kwargs["recipient"] = ctx.recipient
            if "operation" not in kwargs and ctx.operation:
                kwargs["operation"] = ctx.operation

        return kwargs

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> logger.debug("SMTP connection established", smtp_host="smtp.gmail.com")
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.debug(message)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> logger.info("Email sent successfully", recipient="user@example.com", email_id=123)
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.info(message)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> logger.warning("Email delivery delayed", email_id=123, retry_count=3)
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.warning(message)

    def error(self, message: str, **kwargs) -> None:
        """Log error message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> logger.error("SMTP authentication failed", email_id=123, smtp_host="smtp.gmail.com")
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.error(message)

    def exception(self, message: str, **kwargs) -> None:
        """Log exception with context and full traceback.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> try:
            ...     await send_email(...)
            ... except Exception:
            ...     logger.exception("Email sending failed", email_id=123)
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.exception(message)

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message with context.

        Args:
            message: Log message
            **kwargs: Additional fields to include in log

        Example:
            >>> logger.critical("Database connection lost", error="timeout")
        """
        kwargs = self._add_context(kwargs)
        for key, value in kwargs.items():
            setattr(self.logger, key, value)
        self.logger.critical(message)


# Global structured logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_structured_logger(name: str) -> StructuredLogger:
    """Get or create structured logger.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance

    Example:
        >>> from email_service.observability.structured_logger import get_structured_logger
        >>> logger = get_structured_logger(__name__)
        >>> logger.info("Processing email queue")
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]
