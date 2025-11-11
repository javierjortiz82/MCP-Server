"""Logging configuration for SQL service.

Implements file logging with rotation and structured format,
following the same pattern as other services in Lab01-MCP.

Features:
    - Dual output: Console + File handlers
    - Automatic log file rotation (configurable size and backups)
    - Configurable log levels per environment
    - Structured logging with timestamps and line numbers
    - Consistent format across all SQL service scripts

Author: Lab01-MCP Team
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(
    name: str = "sql_service",
    level: str | None = None,
    log_to_file: bool = True,
    log_dir: str | Path | None = None,
    max_size_mb: int | None = None,
    backup_count: int | None = None,
) -> logging.Logger:
    """Configure logging with file rotation and console output.

    Args:
        name: Logger name (e.g., "populate", "sql_service")
        level: Logging level (DEBUG, INFO, WARNING, ERROR). If None, uses .env or defaults to INFO
        log_to_file: Enable file logging (default: True)
        log_dir: Directory for log files. If None, uses SQL/logs
        max_size_mb: Maximum log file size in MB. If None, uses .env or defaults to 10MB
        backup_count: Number of backup files. If None, uses .env or defaults to 5

    Returns:
        Configured logger instance

    Example:
        from utils.logger import setup_logging

        logger = setup_logging("populate")
        logger.info("Starting data population")
        logger.debug("Processing record #123")
        logger.error("Failed to connect to database")
    """
    # Get configuration from environment variables with fallback defaults
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO").upper()

    if max_size_mb is None:
        max_size_mb = int(os.getenv("LOG_MAX_SIZE_MB", "10"))

    if backup_count is None:
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))

    # Determine logs directory (absolute path)
    if log_dir is None:
        # Default: SQL/logs/
        # Path(__file__) = /home/javort/Lab01-MCP/SQL/utils/logger.py
        # .parent = /home/javort/Lab01-MCP/SQL/utils
        # .parent.parent = /home/javort/Lab01-MCP/SQL
        logs_dir = Path(__file__).parent.parent / "logs"
    else:
        logs_dir = Path(log_dir)
        if not logs_dir.is_absolute():
            logs_dir = Path(__file__).parent.parent / logs_dir

    # Create logs directory if it doesn't exist
    logs_dir.mkdir(exist_ok=True, parents=True)

    # Configure logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # ============================================================================
    # Console Handler (for development and debugging)
    # ============================================================================
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Simple format for console
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # ============================================================================
    # File Handler with Rotation (for production and auditing)
    # ============================================================================
    if log_to_file:
        log_file = logs_dir / f"{name}.log"
        max_bytes = max_size_mb * 1024 * 1024

        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Detailed format for file (includes line numbers)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger (avoid duplicate logs)
    logger.propagate = False

    return logger


def get_logger(name: str = "sql_service") -> logging.Logger:
    """Get or create a logger instance.

    Convenience function for getting a logger with default configuration.

    Args:
        name: Logger name

    Returns:
        Logger instance (creates if not exists)

    Example:
        from utils.logger import get_logger

        logger = get_logger(__name__)
        logger.info("SQL operation completed")
    """
    # Check if logger already configured
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Not configured yet, set up with defaults
        return setup_logging(name)
    return logger
