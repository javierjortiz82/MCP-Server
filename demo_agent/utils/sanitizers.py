"""Input/Output Sanitization Utilities.

Provides sanitization functions to prevent XSS, injection attacks, and
information disclosure vulnerabilities.

SECURITY: All user-controlled data should pass through these sanitizers
before being stored, displayed, or included in responses.

Author: Lab01-MCP Team
Created: 2025-11-07
Version: 1.0.0 (Security-Hardened)
"""

import html
import re
from typing import Any

# Maximum lengths for various fields (DoS prevention)
MAX_INPUT_LENGTH = 10000  # User queries
MAX_NAME_LENGTH = 100
MAX_EMAIL_LENGTH = 254
MAX_MESSAGE_LENGTH = 5000


def sanitize_html(text: str) -> str:
    """Sanitize HTML to prevent XSS attacks.

    SECURITY (CWE-79 fix): Escapes HTML special characters to prevent
    script injection in web contexts.

    Args:
        text: Input text that may contain HTML.

    Returns:
        HTML-escaped text safe for display.

    Examples:
        >>> sanitize_html("<script>alert('XSS')</script>")
        "&lt;script&gt;alert('XSS')&lt;/script&gt;"

        >>> sanitize_html("Hello <b>World</b>")
        "Hello &lt;b&gt;World&lt;/b&gt;"
    """
    if not text or not isinstance(text, str):
        return ""

    # HTML escape: < > & " '
    return html.escape(text, quote=True)


def sanitize_user_input(text: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """Sanitize user input for safe processing and storage.

    SECURITY: Removes dangerous characters, normalizes whitespace,
    enforces length limits.

    Args:
        text: User input text.
        max_length: Maximum allowed length (DoS prevention).

    Returns:
        Sanitized text.

    Examples:
        >>> sanitize_user_input("  Hello\\n\\nWorld  ")
        "Hello World"

        >>> sanitize_user_input("Test\\x00null\\rbyte")
        "Testnullbyte"
    """
    if not text or not isinstance(text, str):
        return ""

    # Remove null bytes (string termination attacks)
    text = text.replace("\x00", "")

    # Remove other control characters except newline and tab
    text = "".join(char for char in text if ord(char) >= 0x20 or char in "\n\t")

    # Normalize whitespace (collapse multiple spaces/newlines)
    text = re.sub(r"\s+", " ", text)

    # Trim
    text = text.strip()

    # Enforce length limit
    if len(text) > max_length:
        text = text[:max_length]

    return text


def sanitize_error_message(error: Exception, include_details: bool = False) -> str:
    """Sanitize exception messages to prevent information disclosure.

    SECURITY (CWE-209 fix): Prevents leaking sensitive information
    (database errors, file paths, stack traces) to users.

    Args:
        error: Exception object.
        include_details: Whether to include detailed error info (dev mode only).

    Returns:
        Safe error message for user display.

    Examples:
        >>> sanitize_error_message(ValueError("Database password: secret123"))
        "An error occurred. Please try again."

        >>> sanitize_error_message(FileNotFoundError("/etc/passwd not found"))
        "An error occurred. Please try again."
    """
    if not include_details:
        # Production: Generic message only
        return "An error occurred. Please try again."

    # Development: Sanitized error details
    error_str = str(error)

    # Remove potential sensitive patterns
    patterns_to_redact = [
        (r"password[=:]\s*\S+", "password=[REDACTED]"),
        (r"token[=:]\s*\S+", "token=[REDACTED]"),
        (r"key[=:]\s*\S+", "key=[REDACTED]"),
        (r"secret[=:]\s*\S+", "secret=[REDACTED]"),
        (r"/home/\w+", "/home/[USER]"),
        (r"/root/\w+", "/root/[REDACTED]"),
        (r"C:\\Users\\\w+", "C:\\Users\\[USER]"),
        (r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]"),
    ]

    for pattern, replacement in patterns_to_redact:
        error_str = re.sub(pattern, replacement, error_str, flags=re.IGNORECASE)

    # Limit length
    if len(error_str) > 200:
        error_str = error_str[:200] + "..."

    return sanitize_html(error_str)


def sanitize_response_data(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize API response data to prevent XSS and information disclosure.

    SECURITY: Recursively sanitizes all string values in response objects
    before sending to clients.

    Args:
        data: Response dictionary.

    Returns:
        Sanitized response dictionary.

    Examples:
        >>> sanitize_response_data({"message": "<script>alert(1)</script>"})
        {"message": "&lt;script&gt;alert(1)&lt;/script&gt;"}
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Sanitize string values (but don't escape JSON structure)
            # Only sanitize user-controlled fields
            if key in ["message", "error", "name", "display_name", "full_name", "response"]:
                sanitized[key] = sanitize_html(value)
            else:
                sanitized[key] = value
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_response_data(value)
        elif isinstance(value, list):
            # Sanitize lists
            sanitized[key] = [
                sanitize_response_data(item) if isinstance(item, dict)
                else sanitize_html(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            # Numbers, bools, None - pass through
            sanitized[key] = value

    return sanitized


def sanitize_sql_identifier(identifier: str) -> str:
    """Sanitize SQL identifiers (table/column names) for safe query construction.

    SECURITY (CWE-89 defense-in-depth): While we use parameterized queries,
    this provides additional protection for dynamic table/column names.

    WARNING: This should NOT be used as a replacement for parameterized queries!
    Only use for identifiers that cannot be parameterized (table names, etc.).

    Args:
        identifier: SQL identifier (table or column name).

    Returns:
        Sanitized identifier or raises ValueError if invalid.

    Examples:
        >>> sanitize_sql_identifier("users")
        "users"

        >>> sanitize_sql_identifier("demo_users")
        "demo_users"

        >>> sanitize_sql_identifier("users; DROP TABLE--")
        ValueError: Invalid SQL identifier
    """
    if not identifier or not isinstance(identifier, str):
        raise ValueError("SQL identifier must be a non-empty string")

    # SQL identifiers: alphanumeric + underscore, must start with letter/underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$", identifier):
        raise ValueError(
            f"Invalid SQL identifier '{identifier}'. "
            "Must be alphanumeric + underscore, max 64 chars."
        )

    # Reject SQL keywords (basic list, not exhaustive)
    sql_keywords = {
        "select", "insert", "update", "delete", "drop", "create",
        "alter", "truncate", "exec", "execute", "union", "where"
    }

    if identifier.lower() in sql_keywords:
        raise ValueError(f"SQL identifier cannot be a reserved keyword: {identifier}")

    return identifier


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and injection attacks.

    SECURITY (CWE-22 fix): Removes path traversal sequences and
    dangerous characters.

    Args:
        filename: Filename from user input.

    Returns:
        Sanitized filename safe for file operations.

    Examples:
        >>> sanitize_filename("../../etc/passwd")
        "etc_passwd"

        >>> sanitize_filename("test<script>.txt")
        "testscript.txt"
    """
    if not filename or not isinstance(filename, str):
        return "untitled"

    # Remove path separators (prevent path traversal)
    filename = filename.replace("/", "_").replace("\\", "_")

    # Remove dangerous characters
    filename = re.sub(r"[^\w\s.-]", "", filename)

    # Remove leading/trailing dots and spaces
    filename = filename.strip(". ")

    # Collapse multiple dots (prevent ../ sequences)
    filename = re.sub(r"\.{2,}", ".", filename)

    # Ensure not empty after sanitization
    if not filename:
        filename = "untitled"

    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
        filename = name[:250] + ("." + ext if ext else "")

    return filename


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate.
        max_length: Maximum length (including suffix).
        suffix: Suffix to add when truncated.

    Returns:
        Truncated text.

    Examples:
        >>> truncate_text("Hello World", 8)
        "Hello..."

        >>> truncate_text("Short", 10)
        "Short"
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix
