"""Gemini AI Agent - Separated AI Service Provider.

This module provides the Google Gemini AI integration layer, extracted from
the main application for better separation of concerns.

Updated to use Pydantic v2 configuration and structured logging.
"""

import asyncio
from typing import Any

from google import genai
from google.genai import types

from gemini_agent.config import settings
from gemini_agent.utils.logger import setup_logging

# Setup logger for Gemini Agent
logger = setup_logging("gemini_agent")


class GeminiAgent:
    """Google Gemini AI Agent for natural language processing.

    This class encapsulates all Gemini-specific functionality:
    - Client initialization
    - Response generation
    - Conversation history management
    - Configuration management
    """

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        **generation_params: Any,
    ) -> None:
        """Initialize Gemini Agent.

        Args:
            api_key: Google API key for Gemini (uses settings if not provided)
            model_name: Model to use for generation (uses settings if not provided)
            **generation_params: Override generation parameters (temperature, top_k, etc.)
        """
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.MODEL
        self.client: genai.Client | None = None
        self.conversation_history: list[types.Content] = []
        self.generation_config: types.GenerateContentConfig | None = None
        self.cached_content: types.CachedContent | None = None
        self._generation_params = generation_params

        logger.info(
            "Initializing Gemini Agent - Model: %s, API Key: %s",
            self.model_name,
            "***REDACTED***" if self.api_key else "None",
        )

    async def initialize(self) -> None:
        """Initialize the Gemini client."""
        logger.debug("Initializing Gemini client...")
        self.client = genai.Client(api_key=self.api_key)
        self.generation_config = self._build_generation_config(
            **self._generation_params
        )
        logger.info("Gemini client initialized successfully")

    def _build_generation_config(
        self,
        temperature: float | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
    ) -> types.GenerateContentConfig:
        """Build generation configuration for Gemini.

        Args:
            temperature: Sampling temperature (uses settings if not provided)
            top_k: Top K sampling parameter (uses settings if not provided)
            top_p: Top P (nucleus) sampling parameter (uses settings if not provided)
            max_output_tokens: Maximum tokens to generate (uses settings if not provided)

        Returns:
            Generation configuration with specified parameters
        """
        # Use settings defaults if parameters not provided
        temp = temperature if temperature is not None else settings.TEMPERATURE
        k = top_k if top_k is not None else settings.TOP_K
        p = top_p if top_p is not None else settings.TOP_P
        tokens = (
            max_output_tokens
            if max_output_tokens is not None
            else settings.MAX_OUTPUT_TOKENS
        )

        logger.debug(
            "Generation config: temp=%s, top_k=%s, top_p=%s, max_tokens=%s",
            temp,
            k,
            p,
            tokens,
        )

        return types.GenerateContentConfig(
            temperature=temp,
            top_k=k,
            top_p=p,
            max_output_tokens=tokens,
            response_mime_type="text/plain",
            response_schema=None,
            presence_penalty=None,
            frequency_penalty=None,
            stop_sequences=None,
        )

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str = "",
        tools: list[types.FunctionDeclaration] | None = None,
        tool_config: types.ToolConfig | None = None,
        include_history: bool = True,
    ) -> types.GenerateContentResponse:
        """Generate a response using Gemini.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            tools: Available tools for function calling
            tool_config: Tool configuration
            include_history: Whether to include conversation history

        Returns:
            Generated response from Gemini
        """
        if not self.client:
            logger.error("Gemini client not initialized")
            raise RuntimeError("Gemini client not initialized")

        logger.debug("Generating response for prompt (length: %d)", len(prompt))

        # Build conversation context
        contents = []

        # Add system prompt if provided
        if system_prompt:
            contents.append(
                types.Content(role="user", parts=[types.Part(text=system_prompt)])
            )
            contents.append(
                types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            text="Entendido. Seguiré estas instrucciones como Odiseo Bot."
                        )
                    ],
                )
            )

        # Add conversation history if requested
        if include_history:
            contents.extend(self.conversation_history)

        # Add current prompt
        contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))

        # Generate response
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=self.generation_config,
                tools=tools,
                tool_config=tool_config,
            )

            logger.debug("Response generated successfully")

            # Update history
            if include_history:
                self.conversation_history.append(contents[-1])
                if response.candidates and response.candidates[0].content:
                    self.conversation_history.append(response.candidates[0].content)

                # Maintain reasonable history size
                if len(self.conversation_history) > 20:
                    logger.debug(
                        "Trimming conversation history (was %d items)",
                        len(self.conversation_history),
                    )
                    self.conversation_history = self.conversation_history[-20:]

            return response
        except Exception as e:
            logger.error("Error generating response: %s", e, exc_info=True)
            raise

    def add_to_history(
        self, user_content: types.Content, model_content: types.Content
    ) -> None:
        """Manually add content to conversation history.

        Args:
            user_content: User message content
            model_content: Model response content
        """
        self.conversation_history.append(user_content)
        self.conversation_history.append(model_content)

        # Maintain history size
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        logger.debug(
            "Clearing conversation history (had %d items)",
            len(self.conversation_history),
        )
        self.conversation_history = []

    def update_generation_config(self, **kwargs: Any) -> None:
        """Update generation configuration parameters.

        Args:
            **kwargs: Parameters to update (temperature, top_k, top_p, etc.)
        """
        config_dict = {
            "temperature": kwargs.get("temperature", settings.TEMPERATURE),
            "top_k": kwargs.get("top_k", settings.TOP_K),
            "top_p": kwargs.get("top_p", settings.TOP_P),
            "max_output_tokens": kwargs.get(
                "max_output_tokens", settings.MAX_OUTPUT_TOKENS
            ),
        }
        self.generation_config = self._build_generation_config(**config_dict)

    def convert_tools_to_genai(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[types.FunctionDeclaration]:
        """Convert MCP tools to Google GenAI FunctionDeclaration format.

        Args:
            mcp_tools: List of MCP tool definitions with name, description, inputSchema

        Returns:
            List of FunctionDeclaration for Google GenAI
        """
        function_declarations: list[types.FunctionDeclaration] = []

        for tool in mcp_tools:
            tool_name = tool["name"]
            tool_description = tool["description"]
            input_schema = tool["inputSchema"]

            # Convert JSON Schema to FunctionDeclaration.Schema
            parameters = self._convert_json_schema_to_gemini_schema(input_schema)

            # Create FunctionDeclaration
            function_decl = types.FunctionDeclaration(
                name=tool_name, description=tool_description, parameters=parameters
            )

            function_declarations.append(function_decl)
            logger.debug("Converted tool: %s -> FunctionDeclaration", tool_name)

        return function_declarations

    def _convert_json_schema_to_gemini_schema(
        self, json_schema: dict[str, Any]
    ) -> types.Schema:
        """Convert JSON Schema to Gemini Schema format.

        Args:
            json_schema: JSON Schema from MCP tool definition

        Returns:
            types.Schema for FunctionDeclaration
        """
        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        # Convert properties to Gemini format
        gemini_properties = {}
        for prop_name, prop_def in properties.items():
            gemini_properties[prop_name] = self._convert_property_to_schema(prop_def)

        return types.Schema(
            type=types.Type.OBJECT,
            properties=gemini_properties,
            required=required if required else None,
        )

    def _convert_property_to_schema(self, prop_def: dict[str, Any]) -> types.Schema:
        """Convert a single JSON Schema property to Gemini Schema.

        Args:
            prop_def: Property definition from JSON Schema

        Returns:
            types.Schema for the property
        """
        prop_type_str = prop_def.get("type", "string")
        prop_description = prop_def.get("description", "")
        prop_enum = prop_def.get("enum")

        # Handle array types
        if prop_type_str == "array":
            items_schema = prop_def.get("items", {})
            items_type = (
                self._convert_property_to_schema(items_schema)
                if items_schema
                else types.Schema(type=types.Type.STRING)
            )
            return types.Schema(
                type=types.Type.ARRAY, description=prop_description, items=items_type
            )

        # Handle object types
        elif prop_type_str == "object":
            nested_properties = prop_def.get("properties", {})
            nested_required = prop_def.get("required", [])

            gemini_nested_properties = {}
            for nested_prop_name, nested_prop_def in nested_properties.items():
                gemini_nested_properties[nested_prop_name] = (
                    self._convert_property_to_schema(nested_prop_def)
                )

            return types.Schema(
                type=types.Type.OBJECT,
                description=prop_description,
                properties=gemini_nested_properties,
                required=nested_required if nested_required else None,
            )

        # Handle primitive types
        else:
            return types.Schema(
                type=self._map_json_type_to_gemini(prop_type_str),
                description=prop_description,
                enum=prop_enum if prop_enum else None,
            )

    def _map_json_type_to_gemini(self, json_type: str) -> types.Type:
        """Map JSON Schema types to Gemini types.

        Args:
            json_type: JSON Schema type string

        Returns:
            types.Type enum value
        """
        type_mapping = {
            "string": types.Type.STRING,
            "integer": types.Type.INTEGER,
            "number": types.Type.NUMBER,
            "boolean": types.Type.BOOLEAN,
            "array": types.Type.ARRAY,
            "object": types.Type.OBJECT,
        }
        return type_mapping.get(json_type, types.Type.STRING)

    def build_generation_config(
        self,
        system_prompt: str,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        use_cache: bool = False,
    ) -> types.GenerateContentConfig:
        """Build generation config with tools support (public version).

        This method is compatible with client_mcp's usage pattern.

        Args:
            system_prompt: System instruction text (reserved for future use)
            mcp_tools: Optional list of function declarations (reserved for future use)
            use_cache: Whether to use caching (reserved for future use)

        Returns:
            GenerateContentConfig instance

        Note:
            Parameters system_prompt, mcp_tools, and use_cache are reserved for
            future implementation and currently not used.
        """
        # Suppress unused parameter warnings
        _ = system_prompt, mcp_tools, use_cache

        # Build base config using internal method
        config = self._build_generation_config(**self._generation_params)

        # Store for future use
        self.generation_config = config

        logger.debug("Generation config built")
        return config

    async def delete_cache(self) -> None:
        """Delete cached content if it exists."""
        if self.cached_content:
            try:
                await self.cached_content.delete()
                self.cached_content = None
                logger.info("🗑️ Context cache deleted")
            except Exception as e:
                logger.warning("Error deleting cache: %s", e)

    async def generate_with_retry(
        self, contents: list[types.Content], max_retries: int = 3
    ) -> types.GenerateContentResponse:
        """Generate content with retry logic for rate limits.

        Args:
            contents: Conversation history
            max_retries: Maximum retry attempts

        Returns:
            Response from Gemini API

        Raises:
            Exception: If generation fails after all retries
        """

        retry_delay = 1.0  # Start with 1 second

        for attempt in range(max_retries):
            try:
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=self.generation_config,
                )

            except Exception as e:
                error_str = str(e)

                # Check if cache expired/not found (403 error)
                if ("403" in error_str or "PERMISSION_DENIED" in error_str) and (
                    "CachedContent" in error_str
                ):
                    logger.warning(
                        "⚠️ Cache expired or not found. Fallback to standard mode..."
                    )
                    # Invalidate cache and rebuild config
                    self.cached_content = None
                    self.generation_config = self._build_generation_config(
                        **self._generation_params
                    )
                    logger.info("✅ Config rebuilt in standard mode (no cache)")
                    continue

                # Check if rate limit error (429)
                if (
                    "429" in error_str
                    or "quota" in error_str.lower()
                    or "rate limit" in error_str.lower()
                ):
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2**attempt)
                        logger.warning(
                            "⚠️ Rate limit hit (429). Retrying in %.1fs... (attempt %d/%d)",
                            wait_time,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    logger.error("❌ Rate limit exceeded after all retries")
                    raise

                # Other errors - re-raise immediately
                raise

        raise RuntimeError("Generate content failed after all retries")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("Cleaning up Gemini Agent resources")
        self.clear_history()
        self.client = None
        self.generation_config = None
        self.cached_content = None
        logger.debug("Cleanup completed")
