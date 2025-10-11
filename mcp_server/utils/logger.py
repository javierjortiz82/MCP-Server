"""
Logging configuration for MCP server.
Implements file logging with rotation and structured format.
"""

import logging
import logging.handlers

from config import settings


def setup_logging(name: str = "mcp_server", level: str | None = None) -> logging.Logger:
    """
    Configure logging with file rotation and console output.

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

    return logger
