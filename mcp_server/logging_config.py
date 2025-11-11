"""Factory-based logging for MCP Server Service.

Provides standardized logger factory with file rotation and error logging.

Usage:
    from mcp_server.logging_config import setup_logging, get_logger

    setup_logging(log_level="INFO")
    logger = get_logger(__name__)
    logger.info("MCP server started")

Author: Lab01-MCP Team
Created: 2025-11-03
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

_ROOT_LOGGER: Optional[logging.Logger] = None
_LOG_DIR = Path(__file__).parent / "logs"
_LOG_FORMAT_DETAILED = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_LOG_FORMAT_SIMPLE = "%(asctime)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_MODULE_LEVELS = {
    "mcp_server.server": logging.DEBUG,
    "mcp_server.mcp_handlers": logging.DEBUG,
    "mcp_server.tools": logging.DEBUG,
}


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: str = "INFO",
    file_level: str = "DEBUG",
    console_level: str = "INFO",
    enable_file: bool = True,
) -> None:
    """Configure root logger with file handlers."""
    global _ROOT_LOGGER, _LOG_DIR

    if log_dir:
        _LOG_DIR = Path(log_dir)
    else:
        _LOG_DIR = Path(__file__).parent / "logs"

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(_LOG_FORMAT_SIMPLE, datefmt=_DATE_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    if enable_file:
        log_file = _LOG_DIR / "mcp_server.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, file_level.upper(), logging.DEBUG))
        file_formatter = logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        error_log_file = _LOG_DIR / "mcp_server.error.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(_LOG_FORMAT_DETAILED, datefmt=_DATE_FORMAT)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)

    for module_name, level in _MODULE_LEVELS.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(level)

    _ROOT_LOGGER = root_logger


def get_logger(name: str, log_level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance for a module."""
    logger = logging.getLogger(name)

    if log_level:
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if name.startswith("mcp_server"):
        logger.propagate = True

    return logger


def get_logs_directory() -> Path:
    """Get the logs directory path."""
    return _LOG_DIR
