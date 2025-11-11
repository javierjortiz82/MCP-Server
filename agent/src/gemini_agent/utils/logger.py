"""Logging configuration for Gemini Agent.

This module provides backward compatibility with the legacy setup_logging API
while delegating to the new factory-based logging system in logging_config.py.

Implements file logging with rotation and structured format,
following the same pattern as mcp_server and email_service.

Includes filters to suppress non-critical warnings from third-party libraries
(e.g., Google Gemini API warnings about thought signatures).

NOTE: For new code, prefer importing directly from logging_config:
    from gemini_agent.logging_config import setup_logging, get_logger
"""

import logging
import logging.handlers

from gemini_agent.config import settings

# Import logging_config only when needed to avoid circular imports
# (logging_config is imported inside functions that use it)


class SuppressGoogleGenAIThinkingWarning(logging.Filter):
    """Filter to suppress 'thought_signature' warnings from google.genai.types.

    Gemini 2.5+ models return thought signatures in responses when thinking mode
    is enabled. The google.genai library generates warnings about "non-text parts"
    which are not actionable for the user. This filter suppresses only those
    specific warnings while preserving other important logs.

    Example warning being suppressed:
        WARNING:google_genai.types: There are non-text parts in the response:
        ['thought_signature'], returning concatenated parsed result from text parts.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter logic: suppress only thought_signature related warnings.

        Args:
            record: LogRecord to filter

        Returns:
            False to suppress the record, True to allow it through
        """
        # Only suppress warnings from google_genai.types about non-text parts
        if record.name == "google_genai.types" and record.levelno == logging.WARNING:
            message = record.getMessage()
            if "non-text parts" in message or "thought_signature" in message:
                return False  # Suppress this warning
        return True  # Allow all other logs through


def setup_logging(name: str = "gemini_agent", level: str | None = None) -> logging.Logger:
    """Configure logging with file rotation and console output.

    This function provides backward compatibility with existing code while
    delegating to the new factory-based logging_config module.

    Args:
        name: Logger name (for the returned logger instance)
        level: Logging level (DEBUG, INFO, WARNING, ERROR). If None, uses .env setting

    Returns:
        Configured logger instance

    Note:
        This function sets up the factory-based root logger (once per application)
        and returns a named logger instance. Subsequent calls reuse the root
        configuration to avoid duplicate handlers.

        For new code, prefer:
            from gemini_agent.logging_config import setup_logging, get_logger
    """
    # Import here to avoid circular imports
    from gemini_agent import logging_config

    # Use level from .env if not provided
    if level is None:
        level = settings.LOG_LEVEL

    # Use log_dir_path from settings if available
    log_dir = getattr(settings, "log_dir_path", None)

    # Initialize the factory-based logging system (safe to call multiple times)
    logging_config.setup_logging(
        log_dir=log_dir,
        log_level=level,
        file_level="DEBUG",
        console_level=level,
        enable_file=settings.LOG_TO_FILE if hasattr(settings, "LOG_TO_FILE") else True,
    )

    # Apply filter to suppress google.genai.types warnings about thought signatures
    _apply_google_genai_suppression_filter()

    # Return a named logger instance using the factory
    return logging_config.get_logger(name, log_level=level)


def _apply_google_genai_suppression_filter() -> None:
    """Apply the thought signature suppression filter to google.genai.types logger.

    This function is idempotent - it safely applies the filter even if called multiple times.
    The filter is applied to the root logger to catch all google.genai library messages.
    """
    root_logger = logging.getLogger()

    # Check if filter is already applied (avoid duplicate filters)
    if any(isinstance(f, SuppressGoogleGenAIThinkingWarning) for f in root_logger.filters):
        return  # Filter already applied

    # Apply filter to root logger (catches google.genai.types and all subloggers)
    root_logger.addFilter(SuppressGoogleGenAIThinkingWarning())
