"""Demo agent logging configuration.

Provides consistent logging across the demo service with file and console output.
Follows the same pattern as email_service and mcp_server.

SECURITY UPDATE (CWE-532 fix): Added sensitive data sanitization to prevent
exposure of credentials, tokens, and PII in logs.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 2.0.0 (Security-Hardened)
"""

import logging
import logging.handlers
import re
import sys
from pathlib import Path
from typing import Any, Dict

from demo_agent.config.settings import config


# Sensitive data patterns for sanitization (CWE-532 mitigation)
SENSITIVE_PATTERNS = {
    # JWT tokens (header.payload.signature format)
    'jwt': (
        r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
        '[JWT_REDACTED]'
    ),
    # Bearer tokens in Authorization headers
    'bearer_token': (
        r'Bearer\s+[A-Za-z0-9_\-\.]+',
        'Bearer [TOKEN_REDACTED]'
    ),
    # API keys (common formats)
    'api_key_generic': (
        r'\b(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_\-]{20,})',
        r'api_key=[API_KEY_REDACTED]'
    ),
    # Google API keys (AIza...)
    'google_api_key': (
        r'\bAIza[A-Za-z0-9_\-]{35}',
        '[GOOGLE_API_KEY_REDACTED]'
    ),
    # Clerk secret keys
    'clerk_secret': (
        r'\bsk_(?:test|live)_[A-Za-z0-9]{40,}',
        '[CLERK_SECRET_REDACTED]'
    ),
    # Webhook secrets
    'webhook_secret': (
        r'\bwhsec_[A-Za-z0-9]{40,}',
        '[WEBHOOK_SECRET_REDACTED]'
    ),
    # Email addresses (partial masking: u***@example.com)
    'email': (
        r'\b([a-zA-Z0-9._%+-])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        r'\1***@\2'
    ),
    # IPv4 addresses (partial masking: 192.168.***.xxx)
    'ipv4': (
        r'\b(\d{1,3}\.\d{1,3}\.)\d{1,3}\.\d{1,3}\b',
        r'\1***.***.***'
    ),
    # IPv6 addresses (partial masking)
    'ipv6': (
        r'\b([0-9a-fA-F:]{3,}):([0-9a-fA-F:]+)',
        r'\1:[REDACTED]'
    ),
    # Password fields in key-value pairs
    'password': (
        r'(?i)(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']+)',
        r'password=[PASSWORD_REDACTED]'
    ),
    # Database connection strings
    'db_connection': (
        r'postgresql://([^:]+):([^@]+)@',
        r'postgresql://[USER]:[PASSWORD]@'
    ),
    # Credit card numbers (PCI DSS - should never be in logs!)
    'credit_card': (
        r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
        '[CC_REDACTED]'
    ),
    # Social Security Numbers (SSN) - should never be in logs!
    'ssn': (
        r'\b\d{3}-\d{2}-\d{4}\b',
        '[SSN_REDACTED]'
    ),
}


def sanitize_for_logging(message: Any) -> str:
    """Sanitize sensitive data from log messages.

    SECURITY (CWE-532 mitigation): Masks or redacts sensitive information
    before logging to prevent credential exposure and PII leaks.

    Sanitizes:
    - JWT tokens and Bearer tokens
    - API keys (Google, Clerk, etc.)
    - Email addresses (partial masking)
    - IP addresses (partial masking)
    - Passwords and database credentials
    - Credit cards and SSNs (should never appear!)

    Args:
        message: Log message (string, dict, or other type)

    Returns:
        Sanitized string safe for logging

    Examples:
        >>> sanitize_for_logging("User token: eyJhbGc...")
        "User token: [JWT_REDACTED]"

        >>> sanitize_for_logging("Email: john.doe@example.com")
        "Email: j***@example.com"
    """
    # Convert message to string
    if isinstance(message, dict):
        # Recursively sanitize dict values
        sanitized = {}
        for key, value in message.items():
            # Sanitize key names that might contain sensitive data
            safe_key = sanitize_for_logging(str(key))
            # Sanitize values
            if isinstance(value, (dict, list)):
                sanitized[safe_key] = sanitize_for_logging(value)
            else:
                sanitized[safe_key] = sanitize_for_logging(str(value))
        message = str(sanitized)
    elif isinstance(message, list):
        message = str([sanitize_for_logging(item) for item in message])
    else:
        message = str(message)

    # Apply all sanitization patterns
    for pattern_name, (regex, replacement) in SENSITIVE_PATTERNS.items():
        message = re.sub(regex, replacement, message, flags=re.IGNORECASE)

    return message


class SensitiveDataFilter(logging.Filter):
    """Logging filter that sanitizes sensitive data from log records.

    SECURITY (CWE-532 mitigation): Applied to all log handlers to ensure
    no sensitive data (credentials, tokens, PII) is written to logs.

    This filter modifies log records in-place before they are formatted
    and written to output (console, file, etc.).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Sanitize sensitive data from log record.

        Args:
            record: Log record to sanitize

        Returns:
            True (always allows log record, but sanitizes it first)
        """
        # Sanitize the main log message
        if hasattr(record, 'msg') and record.msg:
            record.msg = sanitize_for_logging(record.msg)

        # Sanitize positional arguments
        if hasattr(record, 'args') and record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(sanitize_for_logging(arg) for arg in record.args)
            elif isinstance(record.args, dict):
                record.args = {
                    k: sanitize_for_logging(v) for k, v in record.args.items()
                }

        # Sanitize exception info (if present)
        if record.exc_info:
            # Exception messages might contain sensitive data
            if record.exc_info[1]:
                exc_message = str(record.exc_info[1])
                # Store sanitized version in record
                record.exc_text = sanitize_for_logging(exc_message)

        return True  # Always allow the record (just sanitize it)


def setup_logging(module_name: str = "demo_agent") -> logging.Logger:
    """Set up logging for the demo service.

    Configures both console and file logging with appropriate formatters.
    SECURITY (CWE-532 fix): Applies SensitiveDataFilter to all handlers
    to prevent credential and PII exposure in logs.

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

    # Create sensitive data filter (applies to all handlers)
    sensitive_filter = SensitiveDataFilter()

    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler with sensitive data filtering
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, config.LOG_LEVEL))
    console_handler.setFormatter(detailed_formatter)
    console_handler.addFilter(sensitive_filter)  # SECURITY: Sanitize console output
    logger.addHandler(console_handler)

    # File handler (if enabled) with sensitive data filtering
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
            file_handler.addFilter(sensitive_filter)  # SECURITY: Sanitize file output
            logger.addHandler(file_handler)
        except OSError as e:
            logger.warning(f"Could not open log file {log_file}: {e}")

    return logger


# Create module-level logger
logger = setup_logging()
