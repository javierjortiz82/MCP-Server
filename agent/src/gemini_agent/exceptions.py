"""Domain-specific exceptions for the Gemini Agent system.

This module provides a hierarchy of custom exceptions for different error domains
in the agent system. These exceptions enable precise error handling and better
error reporting across the application.

Exception Hierarchy:
    AgentError (base)
        ├── ConfigurationError      - Configuration loading/validation failures
        ├── PromptError             - Prompt management and template errors
        ├── ConnectionError         - External API and network failures
        ├── InitializationError     - Agent initialization failures
        ├── GenerationError         - Response generation failures
        └── ValidationError         - Input/output validation failures

Usage Example:
    >>> from gemini_agent.exceptions import PromptError, ConfigurationError
    >>> try:
    ...     prompt = manager.get_booking_prompt()
    ... except PromptError as e:
    ...     logger.error(f"Failed to load prompt: {e}")
    ... except ConfigurationError as e:
    ...     logger.error(f"Configuration issue: {e}")

Author: Lab01-MCP Team
Created: 2025-11-03
Version: 1.0.0
"""

from typing import Any, Optional


class AgentError(Exception):
    """Base exception for all agent-related errors.

    This is the root exception class for the agent system. All domain-specific
    exceptions inherit from this class.

    Attributes:
        message: Error description
        error_code: Optional error code for categorization
        context: Optional context dictionary with additional information
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize AgentError.

        Args:
            message: Human-readable error message
            error_code: Optional error code (e.g., "CONFIG_001")
            context: Optional dictionary with additional context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN"
        self.context = context or {}

    def __str__(self) -> str:
        """String representation of the error."""
        base = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{base} (context: {context_str})"
        return base


class ConfigurationError(AgentError):
    """Configuration loading or validation has failed.

    This exception is raised when:
    - Environment variables are missing
    - Configuration files are invalid or missing
    - Pydantic validation fails
    - Settings have invalid values

    Example:
        >>> raise ConfigurationError(
        ...     message="GOOGLE_API_KEY not set",
        ...     error_code="CONFIG_001",
        ...     context={"required_var": "GOOGLE_API_KEY"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CONFIG_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ConfigurationError."""
        super().__init__(message, error_code, context)


class PromptError(AgentError):
    """Prompt management or template rendering has failed.

    This exception is raised when:
    - Template file is not found
    - Template rendering fails
    - Required context variables are missing
    - YAML configuration is invalid
    - Template syntax is invalid

    Example:
        >>> raise PromptError(
        ...     message="Template file not found: booking_agent.jinja2",
        ...     error_code="PROMPT_001",
        ...     context={"template": "booking_agent.jinja2", "path": "/path/to/templates"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "PROMPT_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize PromptError."""
        super().__init__(message, error_code, context)


class ConnectionError(AgentError):
    """External API or network connection has failed.

    This exception is raised when:
    - Gemini API is unreachable
    - API returns an error
    - Network timeout occurs
    - Authentication with external service fails
    - Rate limiting is triggered

    Example:
        >>> raise ConnectionError(
        ...     message="Failed to connect to Gemini API",
        ...     error_code="CONN_001",
        ...     context={"api": "Gemini", "status_code": 503, "retry_after": 30}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "CONN_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ConnectionError."""
        super().__init__(message, error_code, context)


class InitializationError(AgentError):
    """Agent initialization has failed.

    This exception is raised when:
    - Gemini client initialization fails
    - Required dependencies are missing
    - Agent subclass is missing required methods
    - Memory manager cannot be initialized
    - Session cannot be created

    Example:
        >>> raise InitializationError(
        ...     message="Failed to initialize Gemini client",
        ...     error_code="INIT_001",
        ...     context={"client_type": "genai.Client", "reason": "API key invalid"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INIT_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize InitializationError."""
        super().__init__(message, error_code, context)


class GenerationError(AgentError):
    """Response generation from Gemini has failed.

    This exception is raised when:
    - Content generation fails
    - Function calling fails
    - Response is invalid or empty
    - Generation timeout occurs
    - Model returns an error response

    Example:
        >>> raise GenerationError(
        ...     message="Failed to generate response from Gemini",
        ...     error_code="GEN_001",
        ...     context={"model": "gemini-2.5-flash", "reason": "Invalid content"}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "GEN_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize GenerationError."""
        super().__init__(message, error_code, context)


class ValidationError(AgentError):
    """Input or output validation has failed.

    This exception is raised when:
    - User input is invalid or malicious
    - Agent output doesn't match expected schema
    - Required fields are missing
    - Type validation fails

    Example:
        >>> raise ValidationError(
        ...     message="User input exceeds maximum length",
        ...     error_code="VAL_001",
        ...     context={"max_length": 2000, "actual_length": 2500}
        ... )
    """

    def __init__(
        self,
        message: str,
        error_code: str = "VAL_ERR",
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Initialize ValidationError."""
        super().__init__(message, error_code, context)
