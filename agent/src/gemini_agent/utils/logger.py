"""Logging configuration for Gemini Agent.

Implements file logging with rotation and structured format,
following the same pattern as mcp_server.

Includes filters to suppress non-critical warnings from third-party libraries
(e.g., Google Gemini API warnings about thought signatures).
"""

import logging
import logging.handlers

from gemini_agent.config import settings


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

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR). If None, uses .env setting

    Returns:
        Configured logger instance
    """
    # Use level from .env if not provided
    if level is None:
        level = settings.LOG_LEVEL

    # Create logs directory with absolute path
    logs_dir = settings.log_dir_path
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear existing handlers
    logger.handlers.clear()

    # File handler with rotation (using settings from .env)
    log_file = logs_dir / f"{name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )

    # Console handler
    console_handler = logging.StreamHandler()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Apply filter to suppress google.genai.types warnings about thought signatures
    # This only needs to be done once globally, not per logger
    _apply_google_genai_suppression_filter()

    return logger


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
