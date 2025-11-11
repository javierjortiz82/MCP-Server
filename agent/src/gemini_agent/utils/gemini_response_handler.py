"""Gemini Response Handler - Best Practices for Error Handling.

This module implements Google's official best practices for handling Gemini API
responses, including retry logic with exponential backoff, response validation,
and graceful error handling.

Based on official documentation:
- https://ai.google.dev/gemini-api/docs/troubleshooting
- https://cloud.google.com/iam/docs/retry-strategy

Key Features:
- Exponential backoff with jitter for transient errors
- Response validation (finish_reason, safety_ratings, blocked content)
- Model fallback strategy (Pro -> Flash)
- Comprehensive logging for diagnostics
- Type-safe error handling

Author: Lab01-MCP Team
Created: 2025-11-04
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
import random
import time
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from logging import Logger

    from google.genai import types


class ResponseStatus(Enum):
    """Status of Gemini API response validation."""

    SUCCESS = "success"  # Valid response with content
    EMPTY_RESPONSE = "empty_response"  # response.text is None or empty
    SAFETY_BLOCKED = "safety_blocked"  # Blocked by safety filters
    RECITATION = "recitation"  # Content detected as copied text
    NO_CANDIDATES = "no_candidates"  # No candidates in response
    FINISH_REASON_OTHER = "finish_reason_other"  # Unknown finish reason
    MAX_TOKENS = "max_tokens"  # Hit token limit
    TRANSIENT_ERROR = "transient_error"  # 503, 504, network errors


class RetryConfig:
    """Configuration for retry logic with exponential backoff.

    Based on Google Cloud best practices:
    https://cloud.google.com/iam/docs/retry-strategy

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        multiplier: Exponential backoff multiplier (default: 2.0)
        jitter: Add random jitter to prevent thundering herd (default: True)
        retry_on_status: HTTP status codes to retry (default: 503, 504)
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        multiplier: float = 2.0,
        jitter: bool = True,
        retry_on_status: tuple[int, ...] = (503, 504),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.multiplier = multiplier
        self.jitter = jitter
        self.retry_on_status = retry_on_status

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        # Calculate exponential backoff: delay = base_delay * (multiplier ^ attempt)
        delay = min(self.base_delay * (self.multiplier**attempt), self.max_delay)

        # Add jitter: random value between 0 and 1 second
        if self.jitter:
            delay += random.uniform(0, 1)

        return delay


class GeminiResponseHandler:
    """Handler for Gemini API responses with validation and retry logic.

    Implements Google's best practices for:
    1. Response validation (finish_reason, safety_ratings)
    2. Exponential backoff retry for transient errors
    3. Comprehensive logging for diagnostics
    4. Graceful error handling

    Example:
        >>> handler = GeminiResponseHandler(logger, retry_config)
        >>> status, response = await handler.validate_response(response)
        >>> if status != ResponseStatus.SUCCESS:
        ...     # Handle error based on status
        ...     logger.warning(f"Response failed validation: {status}")
    """

    def __init__(
        self,
        logger: Logger,
        retry_config: Optional[RetryConfig] = None,
    ):
        """Initialize response handler.

        Args:
            logger: Logger instance for diagnostics
            retry_config: Configuration for retry logic (default: RetryConfig())
        """
        self.logger = logger
        self.retry_config = retry_config or RetryConfig()

    def validate_response(self, response: Any) -> tuple[ResponseStatus, Optional[str]]:
        """Validate Gemini API response and extract status.

        Checks for:
        - No candidates (API error)
        - Empty content.parts (None response)
        - finish_reason (STOP=ok, SAFETY/RECITATION/OTHER=error)
        - safety_ratings (if blocked)

        Args:
            response: Gemini API response object

        Returns:
            Tuple of (ResponseStatus, diagnostic_message)
            - ResponseStatus: Status enum indicating validation result
            - diagnostic_message: Detailed message for logging (or None if success)

        Example:
            >>> status, message = handler.validate_response(response)
            >>> if status == ResponseStatus.SAFETY_BLOCKED:
            ...     logger.warning(f"Safety filter triggered: {message}")
        """
        # Check if response has candidates
        if not response.candidates or len(response.candidates) == 0:
            return (
                ResponseStatus.NO_CANDIDATES,
                "Response has no candidates - possible API error or rate limit",
            )

        candidate = response.candidates[0]

        # Check if candidate has content
        if candidate.content is None:
            safety_info = self._format_safety_ratings(candidate)
            finish_reason = getattr(candidate, "finish_reason", "UNKNOWN")
            return (
                ResponseStatus.EMPTY_RESPONSE,
                f"Candidate.content is None | finish_reason: {finish_reason} | {safety_info}",
            )

        # Check if content has parts
        if not candidate.content.parts or len(candidate.content.parts) == 0:
            safety_info = self._format_safety_ratings(candidate)
            finish_reason = getattr(candidate, "finish_reason", "UNKNOWN")
            return (
                ResponseStatus.EMPTY_RESPONSE,
                f"Content.parts is empty | finish_reason: {finish_reason} | {safety_info}",
            )

        # Validate finish_reason
        finish_reason = getattr(candidate, "finish_reason", None)
        if finish_reason:
            # Convert to string for comparison (handle enum or int values)
            finish_reason_str = str(finish_reason)

            # SAFETY: Response blocked by safety filters
            if "SAFETY" in finish_reason_str:
                safety_info = self._format_safety_ratings(candidate)
                return (
                    ResponseStatus.SAFETY_BLOCKED,
                    f"Content blocked by safety filters | {safety_info}",
                )

            # RECITATION: Content detected as copied/plagiarized text
            if "RECITATION" in finish_reason_str:
                return (
                    ResponseStatus.RECITATION,
                    "Content detected as recitation (copied text) - increase temperature or modify prompt",
                )

            # MAX_TOKENS: Hit output token limit
            if "MAX_TOKENS" in finish_reason_str or "LENGTH" in finish_reason_str:
                return (
                    ResponseStatus.MAX_TOKENS,
                    "Response truncated due to max_tokens limit - increase max_output_tokens",
                )

            # OTHER: Unknown finish reason (investigate)
            if "OTHER" in finish_reason_str and "STOP" not in finish_reason_str:
                safety_info = self._format_safety_ratings(candidate)
                return (
                    ResponseStatus.FINISH_REASON_OTHER,
                    f"Unknown finish_reason: {finish_reason_str} | {safety_info}",
                )

        # All validations passed
        return ResponseStatus.SUCCESS, None

    def _format_safety_ratings(self, candidate: Any) -> str:
        """Format safety ratings for logging.

        Args:
            candidate: Response candidate with safety_ratings

        Returns:
            Formatted string with safety ratings information
        """
        if not hasattr(candidate, "safety_ratings") or not candidate.safety_ratings:
            return "safety_ratings: N/A"

        ratings = []
        for rating in candidate.safety_ratings:
            category = getattr(rating, "category", "UNKNOWN")
            probability = getattr(rating, "probability", "UNKNOWN")
            blocked = getattr(rating, "blocked", False)

            # Format: HARM_CATEGORY_HARASSMENT: MEDIUM (blocked=False)
            status = "BLOCKED" if blocked else "ok"
            ratings.append(f"{category}={probability}({status})")

        return f"safety_ratings: [{', '.join(ratings)}]"

    async def retry_with_backoff(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute function with exponential backoff retry for transient errors.

        Retries on:
        - Network errors (ConnectionError, TimeoutError, asyncio.TimeoutError)
        - 503 Service Unavailable
        - 504 Gateway Timeout

        Does NOT retry on:
        - 4xx errors (except 429 rate limit - but should be handled separately)
        - Response validation failures (safety blocks, empty responses, etc.)

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of successful function execution

        Raises:
            Exception: If all retries exhausted or non-retryable error occurred

        Example:
            >>> response = await handler.retry_with_backoff(
            ...     client.aio.models.generate_content,
            ...     model="gemini-2.0-flash-exp",
            ...     contents=contents,
            ...     config=config
            ... )
        """
        last_exception = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                # Execute function
                result = await func(*args, **kwargs)
                return result

            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                last_exception = e
                self.logger.warning(
                    f"⚠️ Transient error (attempt {attempt + 1}/{self.retry_config.max_retries + 1}): {type(e).__name__} - {e}"
                )

            except Exception as e:
                # Check if it's a retryable HTTP error (503, 504)
                error_str = str(e)
                if any(f"{code}" in error_str for code in self.retry_config.retry_on_status):
                    last_exception = e
                    self.logger.warning(
                        f"⚠️ HTTP error {error_str} (attempt {attempt + 1}/{self.retry_config.max_retries + 1})"
                    )
                else:
                    # Non-retryable error - raise immediately
                    self.logger.error(f"❌ Non-retryable error: {type(e).__name__} - {e}")
                    raise

            # If we got here, we need to retry
            if attempt < self.retry_config.max_retries:
                delay = self.retry_config.calculate_delay(attempt)
                self.logger.info(f"⏳ Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)

        # All retries exhausted
        self.logger.error(
            f"❌ All {self.retry_config.max_retries} retry attempts exhausted"
        )
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry attempts exhausted with no exception captured")

    def log_response_diagnostics(
        self,
        response: Any,
        query: str,
        status: ResponseStatus,
    ) -> None:
        """Log comprehensive diagnostics for response validation failure.

        Args:
            response: Gemini API response
            query: Original user query
            status: Validation status from validate_response()
        """
        if not response.candidates:
            self.logger.error(
                f"🚨 NO CANDIDATES in response\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Response: {response}"
            )
            return

        candidate = response.candidates[0]
        finish_reason = getattr(candidate, "finish_reason", "UNKNOWN")
        safety_info = self._format_safety_ratings(candidate)

        # Log based on status
        if status == ResponseStatus.SAFETY_BLOCKED:
            self.logger.error(
                f"🚨 SAFETY FILTER BLOCKED response\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  {safety_info}\n"
                f"  Recommendation: Modify prompt to avoid triggering safety filters"
            )

        elif status == ResponseStatus.RECITATION:
            self.logger.warning(
                f"⚠️ RECITATION detected (copied content)\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  Recommendation: Increase temperature or make prompt more unique"
            )

        elif status == ResponseStatus.EMPTY_RESPONSE:
            self.logger.error(
                f"🚨 EMPTY RESPONSE (content=None or parts=[])\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  {safety_info}\n"
                f"  Content: {candidate.content}\n"
                f"  Recommendation: Check prompt, try fallback model, or increase timeout"
            )

        elif status == ResponseStatus.MAX_TOKENS:
            self.logger.warning(
                f"⚠️ MAX TOKENS reached\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  Recommendation: Increase max_output_tokens in config"
            )

        elif status == ResponseStatus.FINISH_REASON_OTHER:
            self.logger.error(
                f"🚨 UNKNOWN FINISH REASON\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  {safety_info}\n"
                f"  Content: {candidate.content}\n"
                f"  Recommendation: Check Gemini API status or report issue"
            )

        else:
            self.logger.error(
                f"🚨 VALIDATION FAILED with status: {status}\n"
                f"  Query: '{query[:100]}...'\n"
                f"  Finish reason: {finish_reason}\n"
                f"  {safety_info}"
            )
