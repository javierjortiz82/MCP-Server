"""Email service configuration.

Manages SMTP settings, database connection, and worker configuration
loaded from environment variables.

Author: Lab01-MCP Team
Created: 2025-10-14
Version: 1.0.0
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailConfig(BaseSettings):
    """Email service configuration from environment variables.

    All settings can be overridden via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ========================================================================
    # Database Configuration
    # ========================================================================
    DATABASE_URL: str = "postgresql://mcp_user:password@localhost:5434/mcp_db"
    SCHEMA_NAME: str = "test"  # PostgreSQL schema for email_queue table

    # ========================================================================
    # SMTP Configuration
    # ========================================================================
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # SMTP username
    SMTP_PASSWORD: str = ""  # SMTP password or app password
    SMTP_FROM_EMAIL: str = "noreply@lab01.com"
    SMTP_FROM_NAME: str = "Lab01 Bookings"
    SMTP_USE_TLS: bool = True
    SMTP_TIMEOUT: int = 30  # Seconds

    # ========================================================================
    # Email Worker Configuration
    # ========================================================================
    EMAIL_WORKER_POLL_INTERVAL: int = 10  # Seconds between queue polls
    EMAIL_WORKER_BATCH_SIZE: int = 50  # Max emails per batch
    EMAIL_RETRY_MAX_ATTEMPTS: int = 3  # Max retry attempts
    EMAIL_RETRY_BACKOFF_SECONDS: int = 300  # Initial backoff (5 min)

    # ========================================================================
    # Reminder Configuration
    # ========================================================================
    REMINDER_24H_ENABLED: bool = True
    REMINDER_1H_ENABLED: bool = True
    REMINDER_24H_SUBJECT: str = "Recordatorio: Cita mañana"
    REMINDER_1H_SUBJECT: str = "Recordatorio: Cita en 1 hora"

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_TO_FILE: bool = True
    LOG_DIR: str = "./logs"

    # ========================================================================
    # Template Configuration
    # ========================================================================
    TEMPLATE_DIR: str = str(Path(__file__).parent / "templates")

    def validate_smtp_config(self) -> None:
        """Validate SMTP configuration is complete.

        Raises:
            ValueError: If required SMTP settings are missing.
        """
        if not self.SMTP_USER or not self.SMTP_PASSWORD:
            raise ValueError(
                "SMTP credentials not configured. "
                "Set SMTP_USER and SMTP_PASSWORD environment variables."
            )

        if not self.SMTP_FROM_EMAIL:
            raise ValueError("SMTP_FROM_EMAIL is required")

    def get_smtp_config(self) -> dict[str, str | int | bool]:
        """Get SMTP configuration as dictionary.

        Returns:
            Dict with SMTP settings for email client.
        """
        return {
            "host": self.SMTP_HOST,
            "port": self.SMTP_PORT,
            "username": self.SMTP_USER,
            "password": self.SMTP_PASSWORD,
            "from_email": self.SMTP_FROM_EMAIL,
            "from_name": self.SMTP_FROM_NAME,
            "use_tls": self.SMTP_USE_TLS,
            "timeout": self.SMTP_TIMEOUT,
        }


# Global settings instance
settings = EmailConfig()
