"""Booking Agent Configuration and Thresholds.

This module defines configuration for the BookingAgent, including function
calling limits, prompt size constraints, and token estimation ratios.

These values were previously hardcoded and are now configurable to allow
fine-tuning of agent behavior without code changes.

Author: Lab01-MCP Team
Created: 2025-10-16
Version: 1.0.0
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class BookingAgentSettings(BaseSettings):
    """Configuration settings for BookingAgent.

    All settings can be overridden via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ============================================================================
    # Function Calling Configuration
    # ============================================================================
    BOOKING_MAX_FUNCTION_CALL_ITERATIONS: int = Field(
        default=10,
        gt=0,
        le=50,
        description="Maximum number of function calling iterations in BookingAgent loop",
    )

    # ============================================================================
    # Prompt Size Constraints
    # ============================================================================
    BOOKING_MAX_PROMPT_SIZE_CHARS: int = Field(
        default=30000,
        gt=0,
        description="Maximum system prompt size in characters (warning threshold)",
    )

    BOOKING_MAX_CONTENT_SIZE_CHARS: int = Field(
        default=100000,
        gt=0,
        description="Maximum total content size in characters (warning threshold)",
    )

    # ============================================================================
    # Token Estimation
    # ============================================================================
    TOKEN_ESTIMATE_RATIO: float = Field(
        default=0.25,  # 1 token ≈ 4 chars
        gt=0.0,
        le=1.0,
        description="Ratio for estimating tokens from character count (chars_per_token inverse)",
    )

    # ============================================================================
    # Response Generation Configuration
    # ============================================================================
    BOOKING_RESPONSE_TIMEOUT_SECONDS: int = Field(
        default=30,
        gt=0,
        description="Timeout for Gemini API response in seconds",
    )

    BOOKING_MAX_OUTPUT_TOKENS: int = Field(
        default=2048,
        gt=0,
        le=4096,
        description="Maximum output tokens for Gemini API response",
    )

    BOOKING_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for response generation (0=deterministic, 2=creative)",
    )

    # ============================================================================
    # Error Handling
    # ============================================================================
    BOOKING_RETRY_MAX_ATTEMPTS: int = Field(
        default=3,
        gt=0,
        description="Maximum retry attempts for failed Gemini API calls",
    )

    BOOKING_RETRY_BACKOFF_SECONDS: float = Field(
        default=1.0,
        gt=0.0,
        description="Initial backoff time in seconds for retry logic (exponential)",
    )


# Global settings instance
booking_agent_settings = BookingAgentSettings()

__all__ = ["BookingAgentSettings", "booking_agent_settings"]
