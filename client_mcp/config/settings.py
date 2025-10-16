"""Configuration settings for the MCP client using Pydantic BaseSettings v2.

This module uses Pydantic BaseSettings to manage configuration from environment variables
and .env files, following best practices for 2025.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration settings for the MCP client.

    All settings can be overridden via environment variables or .env file.
    Type validation and conversion is handled automatically by Pydantic.
    """

    # ============================================================================
    # Pydantic Configuration
    # ============================================================================
    model_config = SettingsConfigDict(
        # Path to .env file (relative to this file's parent directory)
        env_file=str(Path(__file__).parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow GOOGLE_API_KEY or google_api_key
        extra="ignore",  # Ignore extra fields in .env
    )

    # ============================================================================
    # Google GenAI Configuration
    # ============================================================================
    GOOGLE_API_KEY: str | None = Field(
        default=None,
        description="Google API key for Gemini AI",
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
        description="Maximum output tokens (2048 allows complete multi-category responses)",
    )

    TOP_K: int = Field(
        default=40,
        ge=1,
        le=100,
        description="Control diversity (1-100)",
    )

    TOP_P: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling (0.0-1.0)",
    )

    # ============================================================================
    # MCP Server Configuration
    # ============================================================================
    MCP_HOST: str = Field(
        default="localhost",
        description="MCP server host",
    )

    MCP_PORT: int = Field(
        default=8009,
        gt=0,
        lt=65536,
        description="MCP server port",
    )

    @property
    def mcp_base_url(self) -> str:
        """Computed MCP base URL from host and port.

        Returns:
            str: Complete MCP endpoint URL
        """
        return f"http://{self.MCP_HOST}:{self.MCP_PORT}/mcp"

    # ============================================================================
    # Application Configuration
    # ============================================================================
    DEBUG_MODE: bool = Field(
        default=False,
        description="Enable debug mode",
    )

    ENABLE_LOGGING: bool = Field(
        default=True,
        description="Enable logging",
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Log level (DEBUG, INFO, WARNING, ERROR)",
    )

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got: {v}")
        return v.upper()

    # ============================================================================
    # Tool Configuration
    # ============================================================================
    MAX_FUNCTION_CALLS: int = Field(
        default=5,
        gt=0,
        description="Maximum function calls per request",
    )

    TOOL_TIMEOUT: int = Field(
        default=30,
        gt=0,
        description="Tool execution timeout in seconds",
    )

    # ============================================================================
    # Validation Configuration
    # ============================================================================
    ENABLE_VALIDATION: bool = Field(
        default=True,
        description="Enable Pydantic parameter validation",
    )

    SANITIZE_INPUTS: bool = Field(
        default=True,
        description="Enable input sanitization",
    )

    # ============================================================================
    # Cache Configuration
    # ============================================================================
    ENABLE_CACHE: bool = Field(
        default=True,
        description="Enable tool caching",
    )

    CACHE_TTL_SECONDS: float = Field(
        default=300.0,
        gt=0,
        description="Cache TTL in seconds (300 = 5 minutes)",
    )

    # ============================================================================
    # Metrics and Observability Configuration
    # ============================================================================
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable automatic metrics collection",
    )

    METRICS_EXPORT_PATH: str = Field(
        default="data/execution_metrics.json",
        description="Path to export metrics JSON file",
    )

    # ============================================================================
    # Retry Configuration
    # ============================================================================
    ENABLE_RETRY: bool = Field(
        default=True,
        description="Enable automatic retry on failures",
    )

    RETRY_MAX_ATTEMPTS: int = Field(
        default=3,
        gt=0,
        description="Maximum retry attempts",
    )

    RETRY_INITIAL_DELAY_MS: float = Field(
        default=100.0,
        gt=0,
        description="Initial retry delay in milliseconds",
    )

    RETRY_MAX_DELAY_MS: float = Field(
        default=5000.0,
        gt=0,
        description="Maximum retry delay in milliseconds",
    )

    RETRY_EXPONENTIAL_BASE: float = Field(
        default=2.0,
        gt=1.0,
        description="Exponential backoff base",
    )

    RETRY_JITTER: bool = Field(
        default=True,
        description="Enable jitter to prevent thundering herd",
    )

    # ============================================================================
    # Fallback Configuration
    # ============================================================================
    ENABLE_FALLBACK: bool = Field(
        default=True,
        description="Enable fallback to alternative tools",
    )

    FALLBACK_MAX_DEPTH: int = Field(
        default=2,
        ge=0,
        description="Maximum fallback depth",
    )

    # ============================================================================
    # Thinking Configuration (Gemini 2.5+)
    # ============================================================================
    ENABLE_THINKING: bool = Field(
        default=True,
        description="Enable thinking mode (Gemini 2.5+ only)",
    )

    THINKING_BUDGET: int = Field(
        default=1024,
        description="Tokens for thinking (-1=auto, 0=off, >0=fixed)",
    )

    INCLUDE_THOUGHTS: bool = Field(
        default=False,
        description="Include thought summaries in responses",
    )

    # ============================================================================
    # Rate Limiting Configuration
    # ============================================================================
    ENABLE_RATE_LIMITING: bool = Field(
        default=True,
        description="Enable rate limiting",
    )

    GEMINI_RPM_LIMIT: int = Field(
        default=15,
        gt=0,
        description="Requests per minute (Free tier)",
    )

    GEMINI_RPD_LIMIT: int = Field(
        default=1500,
        gt=0,
        description="Requests per day (Free tier)",
    )

    MAX_CONCURRENT_REQUESTS: int = Field(
        default=3,
        gt=0,
        description="Simultaneous requests",
    )

    # ============================================================================
    # Context Caching Configuration (Gemini 1.5+)
    # ============================================================================
    ENABLE_CONTEXT_CACHING: bool = Field(
        default=True,
        description="Enable context caching for system instructions (Gemini 1.5+)",
    )

    CACHE_TTL_MINUTES: int = Field(
        default=60,
        ge=1,
        le=1440,  # Max 24 hours
        description="Context cache TTL in minutes (default: 60 = 1 hour)",
    )

    # ============================================================================
    # Pagination Configuration
    # ============================================================================
    PAGINATION_PAGE_SIZE: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Number of products to show per page (default: 4)",
    )

    # ============================================================================
    # Multi-Agent System Configuration
    # ============================================================================
    ENABLE_AGENT_ROUTING: bool = Field(
        default=False,
        description="Enable multi-agent routing (sales, booking, general)",
    )

    ROUTER_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=0.5,
        description="Temperature for intent classification (0.0 = deterministic)",
    )

    # ============================================================================
    # Pagination Persistence Configuration
    # ============================================================================
    PAGINATION_PERSISTENCE_ENABLED: bool = Field(
        default=False,
        description="Enable PostgreSQL persistence for pagination contexts",
    )

    PAGINATION_DB_HOST: str = Field(
        default="localhost",
        description="PostgreSQL host for pagination persistence",
    )

    PAGINATION_DB_PORT: int = Field(
        default=5434,
        gt=0,
        lt=65536,
        description="PostgreSQL port for pagination persistence",
    )

    PAGINATION_DB_NAME: str = Field(
        default="mcpdb",
        description="PostgreSQL database name for pagination persistence",
    )

    PAGINATION_DB_USER: str = Field(
        default="mcp_user",
        description="PostgreSQL user for pagination persistence",
    )

    PAGINATION_DB_PASSWORD: str | None = Field(
        default=None,
        description="PostgreSQL password for pagination persistence",
    )

    PAGINATION_TTL_HOURS: int = Field(
        default=24,
        ge=1,
        le=168,  # Max 7 days
        description="Pagination context TTL in hours (default: 24 = 1 day)",
    )

    # ============================================================================
    # SalesAgent Function Calling Configuration
    # ============================================================================
    FUNCTION_CALL_MAX_ITERATIONS: int = Field(
        default=10,
        gt=0,
        le=50,
        description="Maximum iterations for function calling loop in SalesAgent",
    )

    # ============================================================================
    # SalesAgent Tool Configuration
    # ============================================================================
    SEARCH_TOOL_NAMES: str = Field(
        default="search_products,fuzzy_search_smart",
        description="Comma-separated list of search tool names for pagination tracking",
    )

    # ============================================================================
    # SalesAgent Pagination Keywords (Internationalization)
    # ============================================================================
    PAGINATION_KEYWORDS_ES: str = Field(
        default="más,siguiente,muéstrame,opciones",
        description="Spanish keywords for detecting pagination requests",
    )

    PAGINATION_KEYWORDS_EN: str = Field(
        default="more,next,show,additional,options",
        description="English keywords for detecting pagination requests",
    )

    # ============================================================================
    # SalesAgent Error Handling & Fallback Messages
    # ============================================================================
    FALLBACK_ERROR_MESSAGE_ES: str = Field(
        default="No pude generar una respuesta final. Las herramientas se ejecutaron pero no pude procesar el resultado.",
        description="Spanish fallback error message when function calling exhausts iterations",
    )

    FALLBACK_ERROR_MESSAGE_EN: str = Field(
        default="I couldn't generate a final response. Tools were executed but I couldn't process the result.",
        description="English fallback error message",
    )

    CACHE_ERROR_PATTERNS: str = Field(
        default="403,PERMISSION_DENIED,CachedContent",
        description="Error patterns indicating cache expiry (comma-separated)",
    )

    RATE_LIMIT_ERROR_PATTERNS: str = Field(
        default="429,quota,rate limit",
        description="Error patterns indicating rate limiting (comma-separated)",
    )

    # ============================================================================
    # Helper Methods (backward compatibility)
    # ============================================================================

    def get_api_key(self) -> str:
        """Get the Google API key with secure input handling.

        Returns:
            str: The API key

        Raises:
            ValueError: If no valid API key is provided
        """
        import getpass
        import re

        if not self.GOOGLE_API_KEY:
            # Use getpass for masked input (prevents terminal history leakage)
            self.GOOGLE_API_KEY = getpass.getpass(
                "🔑 Introduce tu GOOGLE_API_KEY: "
            ).strip()

            if not self.GOOGLE_API_KEY:
                raise ValueError("❌ API key es requerida para continuar")

            # Basic format validation (Google API keys start with "AIza" and are ~39 chars)
            if not re.match(r"^AIza[0-9A-Za-z_-]{35}$", self.GOOGLE_API_KEY):
                print("⚠️  API key format looks unusual. Verify it's correct.")

        return self.GOOGLE_API_KEY

    def validate_settings(self) -> bool:
        """Validate all required settings.

        Returns:
            bool: True if all settings are valid
        """
        try:
            self.get_api_key()
            return True
        except ValueError:
            return False


    def get_retry_config(self) -> dict[str, float | int | bool]:
        """Get retry configuration as dictionary.

        Returns:
            dict: Retry configuration parameters
        """
        return {
            "max_attempts": self.RETRY_MAX_ATTEMPTS,
            "initial_delay_ms": self.RETRY_INITIAL_DELAY_MS,
            "max_delay_ms": self.RETRY_MAX_DELAY_MS,
            "exponential_base": self.RETRY_EXPONENTIAL_BASE,
            "jitter": self.RETRY_JITTER,
        }

    def get_cache_config(self) -> dict[str, float | bool]:
        """Get cache configuration as dictionary.

        Returns:
            dict: Cache configuration parameters
        """
        return {"enabled": self.ENABLE_CACHE, "ttl_seconds": self.CACHE_TTL_SECONDS}

    def get_metrics_config(self) -> dict[str, str | bool]:
        """Get metrics configuration as dictionary.

        Returns:
            dict: Metrics configuration parameters
        """
        return {"enabled": self.ENABLE_METRICS, "export_path": self.METRICS_EXPORT_PATH}

    def get_validation_config(self) -> dict[str, bool]:
        """Get validation configuration as dictionary.

        Returns:
            dict: Validation configuration parameters
        """
        return {
            "enabled": self.ENABLE_VALIDATION,
            "sanitize_inputs": self.SANITIZE_INPUTS,
        }

    def get_fallback_config(self) -> dict[str, int | bool]:
        """Get fallback configuration as dictionary.

        Returns:
            dict: Fallback configuration parameters
        """
        return {"enabled": self.ENABLE_FALLBACK, "max_depth": self.FALLBACK_MAX_DEPTH}


# ============================================================================
# Global Settings Instance (Singleton)
# ============================================================================
settings = Settings()
