"""Configuration settings for MCP Server using Pydantic BaseSettings v2.

This module uses Pydantic BaseSettings to manage configuration from environment
variables and .env files, following best practices for 2025.

Migration from dataclasses to Pydantic v2 for:
- Type validation and conversion
- Better .env file handling
- Field validators
- Computed properties
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for MCP Server.

    All settings can be overridden via environment variables or .env file.
    Type validation and conversion is handled automatically by Pydantic.
    """

    # ============================================================================
    # Pydantic Configuration
    # ============================================================================
    model_config = SettingsConfigDict(
        # Path to .env file (relative to project root)
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow DATABASE_URL or database_url
        extra="ignore",  # Ignore extra fields in .env
    )

    # ============================================================================
    # Database Configuration
    # ============================================================================
    DATABASE_URL: str = Field(
        ...,  # Required field
        description="PostgreSQL connection URL",
        examples=["postgresql://user:pass@localhost:5434/mcpdb"],
    )

    SCHEMA_NAME: str = Field(
        default="test",
        description="PostgreSQL schema name to use",
    )

    # ============================================================================
    # Google GenAI Configuration
    # ============================================================================
    GOOGLE_API_KEY: str = Field(
        ...,  # Required field
        description="Google API key for Gemini AI embeddings",
    )

    EMBEDDING_MODEL: str = Field(
        default="gemini-embedding-001",
        description="Gemini embedding model to use",
    )

    # ============================================================================
    # Data Configuration
    # ============================================================================
    PRODUCTS_JSON_PATH: str = Field(
        default="./data/products.json",
        description="Path to products JSON file",
    )

    BATCH_SIZE: int = Field(
        default=8,
        gt=0,
        description="Batch size for processing operations",
    )

    PGVECTOR_IVF_LISTS: int = Field(
        default=100,
        gt=0,
        description="Number of IVF lists for pgvector (more = faster search, more memory)",
    )

    # ============================================================================
    # Logging Configuration
    # ============================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
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

    LOG_DIR: str = Field(
        default="logs",
        description="Directory for log files (relative to mcp_server/)",
    )

    # ============================================================================
    # Google Calendar API Configuration (Booking System)
    # ============================================================================
    GOOGLE_CALENDAR_ENABLED: bool = Field(
        default=False,
        description="Enable Google Calendar integration for bookings",
    )

    GOOGLE_CALENDAR_CREDENTIALS_PATH: str = Field(
        default="credentials/service-account.json",
        description="Path to Google service account JSON credentials",
    )

    GOOGLE_CALENDAR_ID: str = Field(
        default="primary",
        description="Google Calendar ID for bookings (default: primary)",
    )

    GOOGLE_CALENDAR_TIMEZONE: str = Field(
        default="America/New_York",
        description="Timezone for Google Calendar events",
    )

    # ============================================================================
    # Booking Configuration
    # ============================================================================
    BOOKING_DEFAULT_DURATION_MINUTES: int = Field(
        default=60,
        gt=0,
        le=480,  # Max 8 hours
        description="Default appointment duration in minutes",
    )

    BOOKING_SLOT_INTERVAL_MINUTES: int = Field(
        default=30,
        gt=0,
        description="Time slot interval for availability checks",
    )

    BOOKING_ADVANCE_BOOKING_DAYS: int = Field(
        default=30,
        gt=0,
        description="Maximum days in advance for booking",
    )

    BOOKING_MIN_ADVANCE_HOURS: int = Field(
        default=2,
        ge=0,
        description="Minimum hours in advance required for booking",
    )

    BOOKING_MAX_DAILY_APPOINTMENTS: int = Field(
        default=10,
        gt=0,
        description="Maximum appointments per day",
    )

    # ============================================================================
    # Agent Memory Configuration (Persistent Context Management)
    # ============================================================================
    MEMORY_ENABLED: bool = Field(
        default=True,
        description="Enable persistent memory system for multi-agent context",
    )

    MEMORY_TTL_DAYS: int = Field(
        default=90,
        gt=0,
        description="Default TTL for memory blocks in days",
    )

    MEMORY_MAX_HISTORY_TURNS: int = Field(
        default=10,
        gt=0,
        le=50,
        description="Maximum conversation turns to keep in short-term memory",
    )

    MEMORY_SEMANTIC_EXTRACTION_ENABLED: bool = Field(
        default=True,
        description="Enable LLM-based semantic memory extraction (Memory Blocks)",
    )

    MEMORY_AUTO_CLEANUP_ENABLED: bool = Field(
        default=True,
        description="Enable automatic cleanup of expired memory blocks",
    )

    MEMORY_PRIORITY_THRESHOLD: int = Field(
        default=5,
        ge=0,
        le=10,
        description="Minimum priority score (0-10) to persist memory block",
    )

    # ============================================================================
    # Session Lifecycle Configuration (GDPR Compliance & Performance)
    # ============================================================================
    SESSION_SOFT_ARCHIVE_DAYS: int = Field(
        default=90,
        gt=0,
        description="Days of inactivity before soft archiving session (exclude from queries)",
    )

    SESSION_HARD_DELETE_DAYS: int = Field(
        default=365,
        gt=0,
        description="Days after archiving before permanently deleting session",
    )

    SESSION_PRESERVE_WITH_EMAIL_DAYS: int = Field(
        default=180,
        gt=0,
        description="Keep sessions with customer_email longer (for CRM continuity)",
    )

    SESSION_ANONYMOUS_DELETE_DAYS: int = Field(
        default=30,
        gt=0,
        description="Delete anonymous sessions (no email) faster (low business value)",
    )

    # ============================================================================
    # Field Validators
    # ============================================================================
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got: {v}")
        return v.upper()

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate DATABASE_URL format."""
        if not v:
            raise ValueError("DATABASE_URL cannot be empty")
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL must start with 'postgresql://'")
        return v

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_google_api_key(cls, v: str) -> str:
        """Validate GOOGLE_API_KEY is not empty."""
        if not v or v.strip() == "":
            raise ValueError("GOOGLE_API_KEY cannot be empty")
        return v.strip()

    # ============================================================================
    # Computed Properties
    # ============================================================================
    @property
    def log_max_bytes(self) -> int:
        """Get max log file size in bytes."""
        return self.LOG_MAX_SIZE_MB * 1024 * 1024

    @property
    def log_dir_path(self) -> Path:
        """Get absolute path to logs directory."""
        return Path(__file__).parent.parent / self.LOG_DIR

    @property
    def products_path(self) -> Path:
        """Get absolute path to products JSON file."""
        products_path = Path(self.PRODUCTS_JSON_PATH)
        if not products_path.is_absolute():
            # Resolve relative to project root
            return Path(__file__).parent.parent / products_path
        return products_path

    # ============================================================================
    # Helper Methods
    # ============================================================================
    def validate_settings(self) -> bool:
        """Validate all required settings are present.

        Returns:
            bool: True if all settings are valid

        Raises:
            ValueError: If any setting is invalid
        """
        # Pydantic automatically validates on initialization
        # This method is kept for backward compatibility
        return True

    def get_database_config(self) -> dict[str, str]:
        """Get database configuration as dictionary.

        Returns:
            dict: Database configuration parameters
        """
        return {
            "database_url": self.DATABASE_URL,
            "schema_name": self.SCHEMA_NAME,
        }

    def get_embedding_config(self) -> dict[str, str]:
        """Get embedding configuration as dictionary.

        Returns:
            dict: Embedding configuration parameters
        """
        return {
            "api_key": self.GOOGLE_API_KEY,
            "model": self.EMBEDDING_MODEL,
        }

    def get_logging_config(self) -> dict[str, str | int]:
        """Get logging configuration as dictionary.

        Returns:
            dict: Logging configuration parameters
        """
        return {
            "level": self.LOG_LEVEL,
            "max_size_mb": self.LOG_MAX_SIZE_MB,
            "backup_count": self.LOG_BACKUP_COUNT,
            "log_dir": self.LOG_DIR,
        }

    def get_calendar_config(self) -> dict[str, str | bool]:
        """Get Google Calendar configuration as dictionary.

        Returns:
            dict: Google Calendar configuration parameters
        """
        return {
            "enabled": self.GOOGLE_CALENDAR_ENABLED,
            "credentials_path": self.GOOGLE_CALENDAR_CREDENTIALS_PATH,
            "calendar_id": self.GOOGLE_CALENDAR_ID,
            "timezone": self.GOOGLE_CALENDAR_TIMEZONE,
        }

    def get_booking_config(self) -> dict[str, int]:
        """Get booking configuration as dictionary.

        Returns:
            dict: Booking configuration parameters
        """
        return {
            "default_duration_minutes": self.BOOKING_DEFAULT_DURATION_MINUTES,
            "slot_interval_minutes": self.BOOKING_SLOT_INTERVAL_MINUTES,
            "advance_booking_days": self.BOOKING_ADVANCE_BOOKING_DAYS,
            "min_advance_hours": self.BOOKING_MIN_ADVANCE_HOURS,
            "max_daily_appointments": self.BOOKING_MAX_DAILY_APPOINTMENTS,
        }

    def get_memory_config(self) -> dict[str, bool | int]:
        """Get memory system configuration as dictionary.

        Returns:
            dict: Memory configuration parameters
        """
        return {
            "enabled": self.MEMORY_ENABLED,
            "ttl_days": self.MEMORY_TTL_DAYS,
            "max_history_turns": self.MEMORY_MAX_HISTORY_TURNS,
            "semantic_extraction_enabled": self.MEMORY_SEMANTIC_EXTRACTION_ENABLED,
            "auto_cleanup_enabled": self.MEMORY_AUTO_CLEANUP_ENABLED,
            "priority_threshold": self.MEMORY_PRIORITY_THRESHOLD,
        }

    def get_session_lifecycle_config(self) -> dict[str, int]:
        """Get session lifecycle configuration as dictionary.

        Returns:
            dict: Session lifecycle configuration parameters
        """
        return {
            "soft_archive_days": self.SESSION_SOFT_ARCHIVE_DAYS,
            "hard_delete_days": self.SESSION_HARD_DELETE_DAYS,
            "preserve_with_email_days": self.SESSION_PRESERVE_WITH_EMAIL_DAYS,
            "anonymous_delete_days": self.SESSION_ANONYMOUS_DELETE_DAYS,
        }


# ============================================================================
# Global Settings Instance (Singleton)
# ============================================================================
settings = Settings()
