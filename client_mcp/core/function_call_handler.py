"""Function calling loop handler for Gemini API.

This module handles the iterative function calling loop required by Gemini API,
including function execution, response processing, and iteration management.
"""

from typing import Any

from google.genai import types

from client_mcp.config.settings import settings
from client_mcp.utils.logger import get_logger

logger = get_logger("FunctionCallHandler", settings.LOG_LEVEL)


class FunctionCallHandler:
    """Handler for Gemini function calling loop.

    Gemini doesn't auto-execute functions, so we need to manually:
    1. Extract function calls from response
    2. Execute functions
    3. Add results to conversation
    4. Generate next response
    5. Repeat until we get text response

    Attributes:
        max_iterations: Maximum iterations to prevent infinite loops
        logger: Logger instance for debugging
    """

    def __init__(self, max_iterations: int = 10):
        """Initialize function call handler.

        Args:
            max_iterations: Maximum function calling iterations
        """
        self.max_iterations = max_iterations

    def extract_function_calls(self, parts: list[types.Part] | None) -> list[Any]:
        """Extract function calls from response parts.

        Args:
            parts: Response parts from Gemini

        Returns:
            List of function_call objects
        """
        if parts is None:
            logger.warning("Response parts is None - cannot extract function calls")
            return []

        function_calls = [part.function_call for part in parts if hasattr(part, "function_call") and part.function_call]

        return function_calls

    def extract_text(self, parts: list[types.Part] | None) -> str | None:
        """Extract text content from response parts.

        Args:
            parts: Response parts from Gemini

        Returns:
            Combined text from all text parts, or None if no text
        """
        if parts is None:
            logger.warning("Response parts is None - cannot extract text")
            return None

        # Handle empty parts list - text may be directly in response
        if len(parts) == 0:
            return None

        text_parts = [part.text for part in parts if hasattr(part, "text") and part.text]

        if not text_parts:
            return None

        return " ".join(text_parts)

    def extract_text_from_content(self, content: Any) -> str | None:
        """Extract text directly from content object.

        This is a fallback when parts structure is not available.

        Args:
            content: Response content from Gemini

        Returns:
            Text from content, or None if not available
        """
        if content is None:
            return None

        # Try to get text directly from content
        if hasattr(content, "text") and content.text:
            return content.text

        return None

    def has_candidates(self, response: Any) -> bool:
        """Check if response has candidates.

        Args:
            response: Gemini API response

        Returns:
            True if response has candidates
        """
        return hasattr(response, "candidates") and response.candidates

    def get_parts(self, response: Any) -> list[types.Part] | None:
        """Get parts from response.

        Args:
            response: Gemini API response

        Returns:
            Parts list or None if not available
        """
        if not self.has_candidates(response):
            return None

        # Defensive check: content can be None
        content = response.candidates[0].content
        if content is None or not hasattr(content, "parts"):
            logger.warning("Response content is None or missing parts - cannot extract")
            return None

        parts = content.parts

        # Handle case where parts is empty or None
        if parts is None or len(parts) == 0:
            logger.debug("Response parts is empty, checking for text content directly")
            # Try to extract text content directly if parts are missing
            if hasattr(content, "text") and content.text:
                logger.debug("Found text content directly in response - creating part")
                # Return as empty parts, text will be extracted separately
                return []
            return None

        return parts
