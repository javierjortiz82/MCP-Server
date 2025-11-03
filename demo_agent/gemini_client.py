"""Gemini API wrapper for demo agent.

Handles all communication with Google Gemini API with token counting.

Author: Lab01-MCP Team
Created: 2025-10-31
Version: 1.0.0
"""


from google import genai
from google.genai import types

from demo_agent.config.settings import config
from demo_agent.logger import logger


class GeminiClient:
    """Wrapper for Google Gemini API.

    Handles API calls, token counting, and error handling.

    Attributes:
        client: Google Gemini client instance
        model_name: Model to use (e.g., gemini-2.5-flash)
    """

    def __init__(self):
        """Initialize Gemini client."""
        if not config.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required")

        self.client = genai.Client(api_key=config.GOOGLE_API_KEY)
        self.model_name = config.MODEL
        logger.info(f"✅ Gemini client initialized (model: {self.model_name})")

    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> tuple[str, int]:
        """Generate response using Gemini API with accurate token counting.

        Args:
            system_prompt: System instruction for the model
            user_message: User query/message
            temperature: Model temperature (optional, uses config default)
            max_output_tokens: Max tokens to generate (optional, uses config default)

        Returns:
            Tuple[str, int]: (response_text, tokens_used)

        Raises:
            ValueError: If API key is missing
            RuntimeError: If API call fails

        Token Counting:
            - Uses Gemini's official count_tokens API for input
            - Response tokens counted from actual generation
            - Ensures accurate quota deduction
        """
        try:
            temp = temperature or config.TEMPERATURE
            max_tokens = max_output_tokens or config.MAX_OUTPUT_TOKENS

            # FIX 2.1: Count input tokens using Gemini's official API
            # This ensures accurate token counting instead of word estimation
            logger.debug(f"Counting input tokens for {self.model_name}...")
            try:
                input_count_response = self.client.models.count_tokens(
                    model=self.model_name,
                    contents=user_message,
                )
                input_tokens = input_count_response.total_tokens
                logger.debug(f"Input tokens: {input_tokens}")
            except Exception as e:
                logger.warning(f"Failed to count input tokens: {e}. Using fallback.")
                # Fallback: simple word count (should rarely happen)
                input_tokens = len(user_message.split())

            # Build generation config
            config_dict = {
                "temperature": temp,
                "max_output_tokens": max_tokens,
                "system_instruction": system_prompt,
            }

            generation_config = types.GenerateContentConfig(**config_dict)

            # Call Gemini API
            logger.debug(f"Calling Gemini API ({self.model_name})...")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=user_message,
                config=generation_config,
            )

            # Extract response text
            response_text = ""
            if response.candidates and response.candidates[0].content:
                content_parts = response.candidates[0].content.parts
                if content_parts and len(content_parts) > 0:
                    response_text = content_parts[0].text or ""

            if not response_text:
                raise RuntimeError("Empty response from Gemini API")

            # FIX 2.1: Count output tokens using Gemini's official API
            logger.debug(f"Counting output tokens for {self.model_name}...")
            try:
                output_count_response = self.client.models.count_tokens(
                    model=self.model_name,
                    contents=response_text,
                )
                output_tokens = output_count_response.total_tokens
                logger.debug(f"Output tokens: {output_tokens}")
            except Exception as e:
                logger.warning(f"Failed to count output tokens: {e}. Using fallback.")
                # Fallback: simple word count (should rarely happen)
                output_tokens = len(response_text.split())

            total_tokens = input_tokens + output_tokens

            logger.info(
                f"✅ Gemini response generated (input={input_tokens}, "
                f"output={output_tokens}, total={total_tokens} tokens, "
                f"{len(response_text)} chars)"
            )

            return response_text, total_tokens

        except Exception as e:
            logger.exception(f"Error calling Gemini API: {e}")
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    async def count_tokens(
        self,
        system_prompt: str,
        user_message: str,
    ) -> int:
        """Count tokens for a request using Gemini's official API.

        Args:
            system_prompt: System instruction
            user_message: User query

        Returns:
            int: Accurate total token count

        Note:
            Uses Gemini's official count_tokens API for accurate counts.
            Includes both system prompt and user message tokens.

        FIX 2.1: Accurate Token Counting
            - Uses Gemini's official count_tokens API
            - Replaces word-count estimation
            - Provides pre-flight token check before API calls
        """
        try:
            logger.debug(f"Counting tokens for {self.model_name}...")

            # Count system prompt tokens
            try:
                prompt_count_response = self.client.models.count_tokens(
                    model=self.model_name,
                    contents=system_prompt,
                )
                prompt_tokens = prompt_count_response.total_tokens
            except Exception as e:
                logger.warning(f"Failed to count system prompt tokens: {e}")
                prompt_tokens = len(system_prompt.split())

            # Count user message tokens
            try:
                message_count_response = self.client.models.count_tokens(
                    model=self.model_name,
                    contents=user_message,
                )
                message_tokens = message_count_response.total_tokens
            except Exception as e:
                logger.warning(f"Failed to count user message tokens: {e}")
                message_tokens = len(user_message.split())

            total_tokens = prompt_tokens + message_tokens
            logger.debug(
                f"Token count: prompt={prompt_tokens}, message={message_tokens}, "
                f"total={total_tokens}"
            )

            return total_tokens

        except Exception as e:
            logger.exception(f"Error counting tokens: {e}")
            # Fallback: word count estimation (should rarely happen)
            fallback_count = len(system_prompt.split()) + len(user_message.split())
            logger.warning(f"Using fallback token count: {fallback_count}")
            return fallback_count

    def get_model_info(self) -> dict:
        """Get information about the current model.

        Returns:
            dict: Model information
        """
        return {
            "model_name": self.model_name,
            "temperature": config.TEMPERATURE,
            "max_output_tokens": config.MAX_OUTPUT_TOKENS,
        }
