"""Demo agent logging configuration.

Provides consistent logging across the demo service with file and console output.
Follows the same pattern as email_service and mcp_server.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from demo_agent.config.settings import config


def setup_logging(module_name: str = "demo_agent") -> logging.Logger:
    """Set up logging for the demo service.

    Configures both console and file logging with appropriate formatters.

    Args:
        module_name: Logger name (typically module name or service name)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(module_name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Avoid duplicate handlers if logger already configured
    if logger.hasHandlers():
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_handler.setFormatter(detailed_formatter)
    logger.addHandler(console_handler)

    # File handler (if enabled)
    if config.LOG_TO_FILE:
        log_dir = Path(config.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / "demo_agent.log"

        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            file_handler.setLevel(getattr(logging, config.LOG_LEVEL))
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
        except OSError as e:
            logger.warning(f"Could not open log file {log_file}: {e}")

    return logger


# Create module-level logger
logger = setup_logging()
