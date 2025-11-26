"""Domain-specific exceptions for Demo Agent Service.

Exception Hierarchy:
    DemoAgentError (base)
        ├── AuthenticationError   - Auth/OTP failures
        ├── RateLimitError        - Rate limiting triggered
        ├── QuotaExceededError    - Token quota exhausted
        ├── CaptchaError          - reCAPTCHA validation failed
        └── ValidationError       - Input validation failed

Author: Lab01-MCP Team
Created: 2025-11-03
"""

from typing import Any


class DemoAgentError(Exception):
    """Base exception for all demo agent errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}

    def __str__(self) -> str:
        base = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} (context: {context_str})"
        return base


class AuthenticationError(DemoAgentError):
    """Authentication or OTP verification failed."""

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERR",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, context)


class RateLimitError(DemoAgentError):
    """IP-based or fingerprint-based rate limiting triggered."""

    def __init__(
        self,
        message: str,
        error_code: str = "RATELIMIT_ERR",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, context)


class QuotaExceededError(DemoAgentError):
    """User token quota has been exceeded."""

    def __init__(
        self,
        message: str,
        error_code: str = "QUOTA_ERR",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, context)


class CaptchaError(DemoAgentError):
    """reCAPTCHA verification failed."""

    def __init__(
        self,
        message: str,
        error_code: str = "CAPTCHA_ERR",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, context)


class ValidationError(DemoAgentError):
    """Input validation failed."""

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_ERR",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, error_code, context)
