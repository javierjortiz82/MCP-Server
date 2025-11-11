"""Centralized logging configuration for Gemini Agent Service.

Provides robust logger factory with file rotation, multiple handlers,
and consistent formatting across all agent components.

Features:
    - Dual output: Console (stdout/stderr) + File handlers
    - Automatic log file rotation (10MB main, 5MB error, configurable via env)
    - Configurable log levels per module and environment
    - Structured logging with context helpers
    - Separate error log file for ERROR+ levels
    - Best practices: ISO 8601 timestamps, proper exception handling
    - Performance optimized for async operations

Configuration via Environment:
    LOG_LEVEL: Root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    LOG_DIR: Directory for log files (default: agent/logs)
    LOG_TO_FILE: Enable/disable file logging (default: true)
    LOG_FILE_LEVEL: File handler level (default: DEBUG)
    LOG_CONSOLE_LEVEL: Console handler level (default: INFO)

Example:
    from gemini_agent.logging_config import setup_logging, get_logger

    # At application startup (once):
    setup_logging(log_level="INFO")

    # In each module:
    logger = get_logger(__name__)
    logger.info("Agent initialized")
    logger.debug("Detailed debug info")
    logger.error("Error occurred", exc_info=True)

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Global configuration
_ROOT_LOGGER: Optional[logging.Logger] = None
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_FORMAT_DETAILED = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_LOG_FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level logger configuration
_MODULE_LEVELS = {
    "gemini_agent.base_agent": logging.DEBUG,
    "gemini_agent.agent": logging.DEBUG,
    "multi_agent.agent_factory": logging.DEBUG,
    "multi_agent.agent_router": logging.DEBUG,
    "multi_agent.booking_agent": logging.DEBUG,
    "multi_agent.sales_agent": logging.DEBUG,
    "multi_agent.general_agent": logging.DEBUG,
    "multi_agent.prompt_manager": logging.DEBUG,
    "gemini_agent.config": logging.INFO,
    "gemini_agent.utils": logging.INFO,
}


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    file_level: str = "DEBUG",
    console_level: str = "INFO",
    enable_file: bool = True,
) -> None:
    """Configure root logger with file and console handlers.

    Should be called once at application startup (e.g., in main function or
    FastAPI app initialization).

    This function:
    - Creates log directory if needed
    - Sets up console handler (stdout)
    - Sets up file handler with rotation (main log)
    - Sets up separate error file handler (ERROR+ only)
    - Configures module-specific log levels

    Args:
        log_dir: Directory for log files. Defaults to agent/logs.
        log_level: Root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        file_level: File handler level (usually DEBUG for comprehensive logging).
        console_level: Console handler level (usually INFO to reduce noise).
        enable_file: Whether to write logs to files.

    Example:
        >>> setup_logging(log_level="INFO", console_level="WARNING")
        # Only show warnings and errors on console, everything in files
    """
    global _ROOT_LOGGER, _LOG_DIR

    if log_dir:
        _LOG_DIR = Path(log_dir)
    else:
        _LOG_DIR = Path(__file__).parent.parent.parent / "logs"

    # Create logs directory if needed
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all levels, handlers filter

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler (stdout for INFO+, stderr for WARNING+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(_LOG_FORMAT_SIMPLE, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File Handler with Rotation (if enabled)
    if enable_file:
        log_file = _LOG_DIR / "gemini_agent.log"

        # RotatingFileHandler: 10MB per file, keep 5 backups
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,  # Keep gemini_agent.log.1 to .5
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        file_formatter = logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error File Handler (separate errors to gemini_agent.error.log)
        error_log_file = _LOG_DIR / "gemini_agent.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)

    # Set module-specific levels
    for module_name, level in _MODULE_LEVELS.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(level)

    _ROOT_LOGGER = root_logger


def get_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance for a module.

    Gets or creates a logger with consistent formatting. Call setup_logging()
    once at application startup for full configuration.

    Args:
        name: Logger name (typically __name__ of calling module).
        log_level: Optional override for logger level (DEBUG, INFO, WARNING, ERROR).
                   If provided, sets logger-specific level.

    Returns:
        Configured logger instance ready for use.

    Example:
        >>> from gemini_agent.logging_config import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Agent processing request #123")
        >>> logger.debug("Detailed debug information")
        >>> logger.error("Error occurred", exc_info=True)
    """
    logger = logging.getLogger(name)

    # Set logger-specific level if provided
    if log_level:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Enable log propagation for agent modules
    if name.startswith(("gemini_agent", "multi_agent")):
        logger.propagate = True

    return logger


def get_logs_directory() -> Path:
    """Get the logs directory path.

    Returns:
        Path object pointing to agent/logs directory.
    """
    return _LOG_DIR


def log_context(
    logger: logging.Logger,
    operation: str,
    agent_name: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Format a log context string with metadata.

    Helper for structured logging with contextual information about
    agent operations and user interactions.

    Args:
        logger: Logger instance.
        operation: Operation name (e.g., "generate_response", "route_intent").
        agent_name: Agent identifier if applicable (e.g., "BookingAgent").
        user_id: User ID if applicable.
        session_id: Session ID if applicable.
        **kwargs: Additional context key-value pairs.

    Returns:
        Formatted context string for logging.

    Example:
        >>> msg = log_context(
        ...     logger,
        ...     "route_intent",
        ...     agent_name="AgentRouter",
        ...     user_id="user_123",
        ...     intent="booking"
        ... )
        >>> logger.info(f"Processing: {msg}")
        # Output: Processing: [AgentRouter|user_123] route_intent (intent=booking)
    """
    context_parts = [operation]

    if agent_name:
        context_parts.insert(0, agent_name)

    if user_id:
        context_parts.append(f"→{user_id}")

    context = " | ".join(context_parts)

    if session_id or kwargs:
        extra_parts = []
        if session_id:
            extra_parts.append(f"session={session_id}")
        extra_parts.extend(f"{k}={v}" for k, v in kwargs.items())
        extra = ", ".join(extra_parts)
        context = f"{context} ({extra})"

    return context
