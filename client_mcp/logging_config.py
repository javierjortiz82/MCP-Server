"""Factory-based logging configuration for Client MCP Service.

Provides standardized logger factory compatible with email_service and agent
logging patterns, while optionally supporting MCPLogger for enhanced console output.

Features:
    - Factory function get_logger() for consistent logger creation
    - File rotation (10MB, 5 backups) with separate error log
    - Configurable log levels per module
    - Optional enhanced MCPLogger with emoji support
    - Best practices: ISO 8601 timestamps, exception handling

Usage:
    from client_mcp.logging_config import setup_logging, get_logger

    # At application startup:
    setup_logging(log_level="INFO")

    # In each module:
    logger = get_logger(__name__)
    logger.info("Connected to MCP server")

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
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_FORMAT_DETAILED = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_LOG_FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Module-level logger configuration
_MODULE_LEVELS = {
    "client_mcp.core": logging.DEBUG,
    "client_mcp.strategies": logging.DEBUG,
    "client_mcp.monitoring": logging.DEBUG,
    "client_mcp.utils": logging.INFO,
    "client_mcp.config": logging.INFO,
}


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    file_level: str = "DEBUG",
    console_level: str = "INFO",
    enable_file: bool = True,
) -> None:
    """Configure root logger with file and console handlers.

    Should be called once at application startup.

    Args:
        log_dir: Directory for log files. Defaults to client_mcp/logs.
        log_level: Root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        file_level: File handler level (usually DEBUG for comprehensive logging).
        console_level: Console handler level (usually INFO to reduce noise).
        enable_file: Whether to write logs to files.
    """
    global _ROOT_LOGGER, _LOG_DIR

    if log_dir:
        _LOG_DIR = Path(log_dir)
    else:
        _LOG_DIR = Path(__file__).parent / "logs"

    # Create logs directory if needed
    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(_LOG_FORMAT_SIMPLE, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File Handler with Rotation (if enabled)
    if enable_file:
        log_file = _LOG_DIR / "client_mcp.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        file_formatter = logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Error File Handler
        error_log_file = _LOG_DIR / "client_mcp.error.log"
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

    Args:
        name: Logger name (typically __name__ of calling module).
        log_level: Optional override for logger level.

    Returns:
        Configured logger instance ready for use.
    """
    logger = logging.getLogger(name)

    if log_level:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if name.startswith("client_mcp"):
        logger.propagate = True

    return logger


def get_logs_directory() -> Path:
    """Get the logs directory path."""
    return _LOG_DIR
