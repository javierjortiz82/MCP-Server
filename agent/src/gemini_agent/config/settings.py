"""Configuration settings for Gemini Agent using Pydantic BaseSettings v2.

This module uses Pydantic BaseSettings to manage configuration from environment
variables and .env files, following best practices for 2025.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for Gemini Agent.

    All settings can be overridden via environment variables or .env file.
    Type validation and conversion is handled automatically by Pydantic.
    """

    # ============================================================================
    # Pydantic Configuration
    # ============================================================================
    model_config = SettingsConfigDict(
        # Path to .env file (agent service configuration)
        # Path: settings.py -> config -> gemini_agent -> src -> agent -> .env
        env_file=str(Path(__file__).parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow GOOGLE_API_KEY or google_api_key
        extra="ignore",  # Ignore extra fields in .env
    )

    # ============================================================================
    # Google GenAI Configuration
    # ============================================================================
    GOOGLE_API_KEY: str = Field(
        ...,  # Required field
        description="Google API key for Gemini AI",
    )

    MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use for generation",
    )

    # ============================================================================
    # Generation Parameters
    # ============================================================================
    TEMPERATURE: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )

    TOP_K: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Top-K sampling parameter (1-100)",
    )

    TOP_P: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-P (nucleus) sampling (0.0-1.0)",
    )

    MAX_OUTPUT_TOKENS: int = Field(
        default=8192,
        gt=0,
        description="Maximum output tokens",
    )

    # ============================================================================
    # Service Configuration
    # ============================================================================
    AGENT_PORT: int = Field(
        default=8000,
        gt=0,
        lt=65536,
        description="Agent service port",
    )

    AGENT_HOST: str = Field(
        default="0.0.0.0",  # nosec B104 - Intentional for Docker networking
        description="Agent service host (0.0.0.0 for Docker, localhost for local)",
    )

    # ============================================================================
    # Logging Configuration
    # ============================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    LOG_TO_FILE: bool = Field(
        default=True,
        description="Enable file logging",
    )

    LOG_DIR: str = Field(
        default="logs",
        description="Directory for log files (relative to agent/)",
    )

    LOG_MAX_SIZE_MB: int = Field(
        default=10,
        gt=0,
        description="Maximum log file size in megabytes",
    )

    LOG_BACKUP_COUNT: int = Field(
        default=5,
        gt=0,
        description="Number of backup log files to keep",
    )

    # ============================================================================
    # Performance Configuration
    # ============================================================================
    REQUEST_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds",
    )

    MAX_CONCURRENT_REQUESTS: int = Field(
        default=10,
        gt=0,
        description="Maximum concurrent requests",
    )

    ENABLE_RATE_LIMITING: bool = Field(
        default=False,
        description="Enable request rate limiting",
    )

    # ============================================================================
    # Retry Configuration
    # ============================================================================
    RETRY_MAX_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for API calls",
    )

    RETRY_INITIAL_DELAY_MS: int = Field(
        default=1000,
        ge=100,
        le=60000,
        description="Initial retry delay in milliseconds",
    )

    # ============================================================================
    # Error Pattern Configuration
    # ============================================================================
    CACHE_ERROR_PATTERNS: str = Field(
        default="CacheError,RESOURCE_EXHAUSTED,cache",
        description="Cache error patterns to detect (comma-separated)",
    )

    RATE_LIMIT_ERROR_PATTERNS: str = Field(
        default="429,RATE_LIMIT_EXCEEDED,quota",
        description="Rate limit error patterns to detect (comma-separated)",
    )

    # ============================================================================
    # CORS Configuration
    # ============================================================================
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Allowed CORS origins (comma-separated)",
    )

    # ============================================================================
    # Field Validators
    # ============================================================================
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values.

        Args:
            cls: Class reference (Pydantic validator requirement)
            v: Log level string to validate

        Returns:
            Validated and uppercased log level string

        Raises:
            ValueError: If log level is not in allowed values
        """
        _ = cls  # Pydantic required parameter
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got: {v}")
        return v.upper()

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_google_api_key(cls, v: str) -> str:
        """Validate GOOGLE_API_KEY is not empty.

        Args:
            cls: Class reference (Pydantic validator requirement)
            v: API key string to validate

        Returns:
            Validated and stripped API key string

        Raises:
            ValueError: If API key is empty or contains only whitespace
        """
        _ = cls  # Pydantic required parameter
        if not v or not v.strip():
            raise ValueError("GOOGLE_API_KEY cannot be empty")
        return v.strip()

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, v: str) -> str:
        """Validate ALLOWED_ORIGINS format.

        Args:
            cls: Class reference (Pydantic validator requirement)
            v: Comma-separated list of allowed origins to validate

        Returns:
            Validated and stripped origins string

        Raises:
            ValueError: If origins string is empty or contains only whitespace
        """
        _ = cls  # Pydantic required parameter
        if not v or not v.strip():
            raise ValueError("ALLOWED_ORIGINS cannot be empty")
        return v.strip()

    # ============================================================================
    # Computed Properties
    # ============================================================================
    @property
    def log_dir_path(self) -> Path:
        """Get absolute path to logs directory."""
        return Path(__file__).parent.parent.parent.parent / self.LOG_DIR

    @property
    def log_max_bytes(self) -> int:
        """Get max log file size in bytes."""
        return self.LOG_MAX_SIZE_MB * 1024 * 1024

    @property
    def allowed_origins_list(self) -> list[str]:
        """Get list of allowed CORS origins."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # ============================================================================
    # Helper Methods
    # ============================================================================
    def get_generation_config(self) -> dict[str, float | int]:
        """Get generation configuration as dictionary.

        Returns:
            dict: Generation configuration parameters
        """
        return {
            "temperature": self.TEMPERATURE,
            "top_k": self.TOP_K,
            "top_p": self.TOP_P,
            "max_output_tokens": self.MAX_OUTPUT_TOKENS,
        }

    def get_logging_config(self) -> dict[str, str | int | bool]:
        """Get logging configuration as dictionary.

        Returns:
            dict: Logging configuration parameters
        """
        return {
            "level": self.LOG_LEVEL,
            "to_file": self.LOG_TO_FILE,
            "log_dir": self.LOG_DIR,
            "max_size_mb": self.LOG_MAX_SIZE_MB,
            "backup_count": self.LOG_BACKUP_COUNT,
        }

    def get_service_config(self) -> dict[str, str | int]:
        """Get service configuration as dictionary.

        Returns:
            dict: Service configuration parameters
        """
        return {
            "host": self.AGENT_HOST,
            "port": self.AGENT_PORT,
            "timeout": self.REQUEST_TIMEOUT,
            "max_concurrent": self.MAX_CONCURRENT_REQUESTS,
        }


# ============================================================================
# Global Settings Instance (Singleton)
# ============================================================================
settings = Settings()
