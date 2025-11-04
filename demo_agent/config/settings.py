"""Demo agent configuration with Pydantic v2.

Manages demo limits, rate-limiting, security settings, and database connection
loaded from environment variables or .env file.

All settings can be overridden via environment variables.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""


from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoConfig(BaseSettings):
    """Demo agent configuration.

    Loads settings from environment variables and .env file using Pydantic v2.
    All settings are case-sensitive and strictly validated.

    Attributes:
        DATABASE_URL: PostgreSQL connection string.
        SCHEMA_NAME: PostgreSQL schema name for demo tables.
        GOOGLE_API_KEY: Google API key for Gemini.
        MODEL: Gemini model to use (default: gemini-2.5-flash).
        TEMPERATURE: Model temperature (0.0-2.0).
        MAX_OUTPUT_TOKENS: Maximum output tokens per response.
        DEMO_MAX_TOKENS: Maximum tokens allowed per day in demo.
        DEMO_COOLDOWN_HOURS: Hours to wait before reactivating blocked demo.
        DEMO_WARNING_THRESHOLD: Percentage threshold to show warning (0-100).
        DEMO_AGENT_HOST: Host to bind to.
        DEMO_AGENT_PORT: Port to listen on.
        ENABLE_CAPTCHA: Enable reCAPTCHA v3 verification.
        RECAPTCHA_SECRET_KEY: reCAPTCHA v3 secret key.
        RECAPTCHA_SITE_KEY: reCAPTCHA v3 site key.
        ENABLE_FINGERPRINT: Enable client fingerprinting.
        FINGERPRINT_SCORE_THRESHOLD: Abuse score threshold (0.0-1.0).
        IP_RATE_LIMIT_REQUESTS: Max requests per IP per minute.
        IP_RATE_LIMIT_WINDOW_SEC: Rate limit window in seconds.
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        LOG_TO_FILE: Whether to log to file.
        LOG_DIR: Directory for log files.
        DEBUG_MODE: Enable debug mode.
    """

    model_config = SettingsConfigDict(
        env_file=None,  # Don't load from file in Docker
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ========================================================================
    # Database Configuration
    # ========================================================================
    DATABASE_URL: str = Field(
        default="postgresql://mcp_user:mcp_password@localhost:5434/mcpdb",
        description="PostgreSQL connection string",
    )
    SCHEMA_NAME: str = Field(
        default="test",
        description="PostgreSQL schema name for demo tables",
    )

    # ========================================================================
    # Gemini API Configuration
    # ========================================================================
    GOOGLE_API_KEY: str = Field(
        default="",
        description="Google API key for Gemini",
    )
    MODEL: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model to use",
    )
    TEMPERATURE: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Model temperature (0.0-2.0)",
    )
    MAX_OUTPUT_TOKENS: int = Field(
        default=2048,
        gt=0,
        description="Maximum output tokens per response",
    )

    # ========================================================================
    # Demo Limits Configuration
    # ========================================================================
    DEMO_MAX_TOKENS: int = Field(
        default=5000,
        gt=0,
        description="Maximum tokens per user per day",
    )
    DEMO_COOLDOWN_HOURS: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours to wait before reactivating blocked demo",
    )
    DEMO_WARNING_THRESHOLD: int = Field(
        default=85,
        ge=1,
        le=100,
        description="Percentage threshold to show token warning (1-100)",
    )

    # ========================================================================
    # OTP (One-Time Password) Configuration
    # ========================================================================
    OTP_EXPIRATION_MINUTES: int = Field(
        default=10,
        ge=1,
        le=60,
        description="OTP expiration time in minutes (NIST/OWASP: 5-15 recommended)",
    )
    OTP_RATE_LIMIT_COOLDOWN_SECONDS: int = Field(
        default=60,
        ge=1,
        le=3600,
        description="Seconds to wait between OTP requests per email (rate limiting)",
    )
    OTP_MAX_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum verification attempts per OTP code",
    )

    # ========================================================================
    # Server Configuration
    # ========================================================================
    DEMO_AGENT_HOST: str = Field(
        default="0.0.0.0",
        description="Host to bind to",
    )
    DEMO_AGENT_PORT: int = Field(
        default=8082,
        ge=1,
        le=65535,
        description="Port to listen on",
    )

    # ========================================================================
    # Security Configuration
    # ========================================================================
    ENABLE_CAPTCHA: bool = Field(
        default=True,
        description="Enable reCAPTCHA v3 verification",
    )
    RECAPTCHA_SECRET_KEY: str = Field(
        default="",
        description="reCAPTCHA v3 secret key",
    )
    RECAPTCHA_SITE_KEY: str = Field(
        default="",
        description="reCAPTCHA v3 site key",
    )
    ENABLE_FINGERPRINT: bool = Field(
        default=True,
        description="Enable client fingerprinting for VPN/proxy detection",
    )
    FINGERPRINT_SCORE_THRESHOLD: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Abuse score threshold for fingerprinting (0.0-1.0)",
    )

    # ========================================================================
    # Clerk Authentication Configuration
    # ========================================================================
    CLERK_SECRET_KEY: str = Field(
        default="",
        description="Clerk secret key (sk_test_... or sk_live_...)",
    )
    CLERK_PUBLISHABLE_KEY: str = Field(
        default="",
        description="Clerk publishable key (pk_test_... or pk_live_...)",
    )
    CLERK_WEBHOOK_SECRET: str = Field(
        default="",
        description="Clerk webhook signing secret (whsec_...)",
    )
    CLERK_FRONTEND_API: str = Field(
        default="clerk.accounts.dev",
        description="Clerk frontend API domain (e.g., clerk.odiseo.com or clerk.accounts.dev)",
    )
    ENABLE_CLERK_AUTH: bool = Field(
        default=True,
        description="Enable Clerk authentication (disable for legacy auth only)",
    )

    # ========================================================================
    # Rate Limiting Configuration
    # ========================================================================
    IP_RATE_LIMIT_REQUESTS: int = Field(
        default=100,
        gt=0,
        description="Max requests per IP per minute",
    )
    IP_RATE_LIMIT_WINDOW_SEC: int = Field(
        default=60,
        gt=0,
        description="Rate limit window in seconds",
    )

    # ========================================================================
    # Logging Configuration
    # ========================================================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    LOG_TO_FILE: bool = Field(
        default=True,
        description="Whether to log to file",
    )
    LOG_DIR: str = Field(
        default="logs",
        description="Directory for log files",
    )
    DEBUG_MODE: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    # ========================================================================
    # Validators
    # ========================================================================

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got: {v}")
        return v.upper()

    @field_validator("GOOGLE_API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate Google API key format."""
        if v and not v.startswith("AIza"):
            raise ValueError("GOOGLE_API_KEY must start with 'AIza'")
        return v

    @field_validator("TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("TEMPERATURE must be between 0.0 and 2.0")
        return v

    @field_validator("CLERK_SECRET_KEY")
    @classmethod
    def validate_clerk_secret_key(cls, v: str) -> str:
        """Validate Clerk secret key format."""
        if v and not (v.startswith("sk_test_") or v.startswith("sk_live_")):
            raise ValueError("CLERK_SECRET_KEY must start with 'sk_test_' or 'sk_live_'")
        return v

    @field_validator("CLERK_PUBLISHABLE_KEY")
    @classmethod
    def validate_clerk_publishable_key(cls, v: str) -> str:
        """Validate Clerk publishable key format."""
        if v and not (v.startswith("pk_test_") or v.startswith("pk_live_")):
            raise ValueError("CLERK_PUBLISHABLE_KEY must start with 'pk_test_' or 'pk_live_'")
        return v

    @field_validator("CLERK_WEBHOOK_SECRET")
    @classmethod
    def validate_clerk_webhook_secret(cls, v: str) -> str:
        """Validate Clerk webhook secret format."""
        if v and not v.startswith("whsec_"):
            raise ValueError("CLERK_WEBHOOK_SECRET must start with 'whsec_'")
        return v


# Global config instance (singleton)
config = DemoConfig()
