"""Centralized OTP and Session Configuration.

This module provides a single source of truth for all session and OTP timeout values.
All values are read from environment variables and can be configured without
changing source code.

Configuration Hierarchy:
1. Environment variables (.env file)
2. Default values (fallback if env var not set)

Usage:
    from mcp_server.config.otp_session_config import OTPSessionConfig

    timeout = OTPSessionConfig.SESSION_IDLE_TIMEOUT_MINUTES  # 1
    otp_exp = OTPSessionConfig.OTP_EXPIRATION_MINUTES  # 10

Author: Lab01-MCP Team
Created: 2025-11-19
Version: 1.0.0
"""

import os
from typing import Final


class OTPSessionConfig:
    """Centralized configuration for OTP and session timeouts.

    All values can be overridden via environment variables.
    """

    # ========================================================================
    # SESSION TIMEOUT CONFIGURATION (minutes)
    # ========================================================================
    # Idle timeout: Session expires if user is inactive for this duration
    SESSION_IDLE_TIMEOUT_MINUTES: Final[int] = int(
        os.getenv("SESSION_IDLE_TIMEOUT_MINUTES", "1")
    )

    # TTL (Time-To-Live): Session expires after this total duration from creation
    SESSION_TTL_MINUTES: Final[int] = int(
        os.getenv("SESSION_TTL_MINUTES", "60")
    )

    # Absolute timeout: Session never lasts longer than this
    SESSION_ABSOLUTE_TIMEOUT_MINUTES: Final[int] = int(
        os.getenv("SESSION_ABSOLUTE_TIMEOUT_MINUTES", "480")
    )

    # ========================================================================
    # OTP CONFIGURATION
    # ========================================================================
    # OTP expiration time in minutes (NIST/OWASP compliant: 5-15 minutes)
    OTP_EXPIRATION_MINUTES: Final[int] = int(
        os.getenv("OTP_EXPIRATION_MINUTES", "10")
    )

    # Rate limiting: Minimum seconds between OTP requests for same email
    # Note: Environment variable is OTP_RATE_LIMIT_SECONDS but defaults to 60
    # (compatible with OTP_RATE_LIMIT_COOLDOWN_SECONDS for backward compatibility)
    OTP_RATE_LIMIT_SECONDS: Final[int] = int(
        os.getenv("OTP_RATE_LIMIT_SECONDS",
                 os.getenv("OTP_RATE_LIMIT_COOLDOWN_SECONDS", "60"))
    )

    # Maximum verification attempts per OTP code
    OTP_MAX_ATTEMPTS: Final[int] = int(
        os.getenv("OTP_MAX_ATTEMPTS", "3")
    )

    # Maximum OTP codes per email before lockout
    OTP_MAX_CODES_PER_EMAIL: Final[int] = int(
        os.getenv("OTP_MAX_CODES_PER_EMAIL", "5")
    )

    # ========================================================================
    # DERIVED VALUES (calculated from above, do not override)
    # ========================================================================

    @classmethod
    def SESSION_IDLE_TIMEOUT_SECONDS(cls) -> int:
        """Convert session idle timeout to seconds."""
        return cls.SESSION_IDLE_TIMEOUT_MINUTES * 60

    @classmethod
    def SESSION_TTL_SECONDS(cls) -> int:
        """Convert session TTL to seconds."""
        return cls.SESSION_TTL_MINUTES * 60

    @classmethod
    def SESSION_ABSOLUTE_TIMEOUT_SECONDS(cls) -> int:
        """Convert session absolute timeout to seconds."""
        return cls.SESSION_ABSOLUTE_TIMEOUT_MINUTES * 60

    @classmethod
    def OTP_EXPIRATION_SECONDS(cls) -> int:
        """Convert OTP expiration to seconds."""
        return cls.OTP_EXPIRATION_MINUTES * 60

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    @classmethod
    def get_session_timeout_display(cls, language: str = "es") -> str:
        """Get human-readable session timeout for display to users.

        Args:
            language: User language ("es" for Spanish, "en" for English)

        Returns:
            str: Formatted timeout text (e.g., "1 minute", "1 minuto")
        """
        timeout_min = cls.SESSION_IDLE_TIMEOUT_MINUTES

        if language == "en":
            return f"{timeout_min} minute{'s' if timeout_min != 1 else ''}"
        else:  # Spanish
            return f"{timeout_min} minuto{'s' if timeout_min != 1 else ''}"

    @classmethod
    def get_otp_timeout_display(cls, language: str = "es") -> str:
        """Get human-readable OTP timeout for display to users.

        Args:
            language: User language ("es" for Spanish, "en" for English)

        Returns:
            str: Formatted timeout text (e.g., "10 minutes", "10 minutos")
        """
        timeout_min = cls.OTP_EXPIRATION_MINUTES

        if language == "en":
            return f"{timeout_min} minute{'s' if timeout_min != 1 else ''}"
        else:  # Spanish
            return f"{timeout_min} minuto{'s' if timeout_min != 1 else ''}"

    @classmethod
    def get_config_summary(cls) -> dict:
        """Get a dictionary of all configuration values for logging/debugging.

        Returns:
            dict: Configuration summary
        """
        return {
            "session": {
                "idle_timeout_minutes": cls.SESSION_IDLE_TIMEOUT_MINUTES,
                "idle_timeout_seconds": cls.SESSION_IDLE_TIMEOUT_SECONDS(),
                "ttl_minutes": cls.SESSION_TTL_MINUTES,
                "ttl_seconds": cls.SESSION_TTL_SECONDS(),
                "absolute_timeout_minutes": cls.SESSION_ABSOLUTE_TIMEOUT_MINUTES,
                "absolute_timeout_seconds": cls.SESSION_ABSOLUTE_TIMEOUT_SECONDS(),
            },
            "otp": {
                "expiration_minutes": cls.OTP_EXPIRATION_MINUTES,
                "expiration_seconds": cls.OTP_EXPIRATION_SECONDS(),
                "rate_limit_seconds": cls.OTP_RATE_LIMIT_SECONDS,
                "max_attempts": cls.OTP_MAX_ATTEMPTS,
                "max_codes_per_email": cls.OTP_MAX_CODES_PER_EMAIL,
            }
        }
