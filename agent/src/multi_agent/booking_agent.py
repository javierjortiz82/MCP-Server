"""Booking Agent - Specialized Agent for Reservation Queries.

This module provides the BookingAgent class that handles all booking-related
queries including creating, canceling, rescheduling appointments, and checking
availability. Uses Gemini 2.5 Flash with booking MCP tools.

The agent specializes in:
- Creating new appointments/reservations
- Canceling existing bookings
- Rescheduling appointments
- Checking available time slots
- Listing customer bookings
- Providing booking confirmations

Architecture:
    BookingAgent inherits from BaseAgent, eliminating ~280 lines of duplicated code.
    Only agent-specific functionality is implemented here:
    - System prompt via PromptManager (with A/B testing support)
    - MCP tools configuration for function calling
    - Booking-specific business logic

References:
    - https://ai.google.dev/gemini-api/docs/function-calling
    - https://googleapis.github.io/python-genai/
    - https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 2.0.0 (Refactored to inherit from BaseAgent)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from gemini_agent.base_agent import BaseAgent
from gemini_agent.config.booking_agent_settings import booking_agent_settings
from gemini_agent.utils.language_detector import detect_user_language
from google.genai import types
from multi_agent.prompt_manager import PromptManager

# Gemini 2.5 Function Calling Optimization (Scope Limiting)
# Autodiscover booking tools from MCP server (single source of truth)
# This avoids hardcoding tool names and ensures automatic sync when tools change

# Setup MCP server path for imports
mcp_server_path = Path(__file__).parent.parent.parent.parent / "mcp_server"
if str(mcp_server_path) not in sys.path:
    sys.path.insert(0, str(mcp_server_path))

# Try to import autodiscovered booking tools
# Fallback to hardcoded list if MCP server not available
try:
    from mcp_handlers.booking_handlers import get_booking_tool_names

    BOOKING_TOOLS_ALLOWED = set(get_booking_tool_names())
    _logger = __import__("logging").getLogger("booking_agent_init")
    _logger.info(
        f"✅ Autodiscovered {len(BOOKING_TOOLS_ALLOWED)} booking tools from MCP server"
    )
except ImportError as e:
    _logger = __import__("logging").getLogger("booking_agent_init")
    _logger.warning(
        f"⚠️ Could not autodiscover booking tools from MCP server: {e}. "
        f"Using fallback hardcoded list."
    )
    # Fallback: Hardcoded list (8 booking tools)
    # This ensures the agent works even if MCP server is not available
    # But updates to tools must be made in BOTH places (not ideal - prefer autodiscover)
    BOOKING_TOOLS_ALLOWED = {
        "create_booking",
        "cancel_booking",
        "reschedule_booking",
        "get_available_slots",
        "get_booking_by_id",
        "list_customer_bookings",
        "get_services",
        "get_business_hours",
    }

# Import language context for MCP tool execution
try:
    from utils.language_context import set_current_language

    LANGUAGE_CONTEXT_AVAILABLE = True
except ImportError:
    LANGUAGE_CONTEXT_AVAILABLE = False
    set_current_language = None  # type: ignore[assignment]

# Import client_mcp utilities for function calling
client_mcp_path = Path(__file__).parent.parent.parent.parent / "client_mcp"
if str(client_mcp_path) not in sys.path:
    sys.path.insert(0, str(client_mcp_path))

try:
    from core.function_call_handler import FunctionCallHandler
    from core.mcp_connector import MCPConnector

    FUNCTION_CALLING_AVAILABLE = True
except ImportError:
    FUNCTION_CALLING_AVAILABLE = False
    FunctionCallHandler = None  # type: ignore[misc,assignment]
    MCPConnector = None  # type: ignore[misc,assignment]


# ═══════════════════════════════════════════════════════════════════════════════
# BOOKING RESPONSE SCHEMA (Gemini 2.5 Structured Output Feature)
# ═══════════════════════════════════════════════════════════════════════════════
# Defines JSON schema for structured responses (Google Gemini Best Practice 2025)
# Ensures: 100% valid JSON parsing, automatic intent detection, strict compliance
#
# Feature: responseSchema (introduced July 2025)
# Benefit: Eliminates parsing errors, enables reliable downstream processing
# ═══════════════════════════════════════════════════════════════════════════════

BOOKING_RESPONSE_SCHEMA = types.Schema(
    type="object",
    properties={
        "intent": types.Schema(
            type="string",
            enum=[
                "create_booking",
                "cancel_booking",
                "reschedule_booking",
                "list_bookings",
                "service_info",
                "business_hours",
                "availability_check",
                "disambiguation",
                "out_of_scope",
                "error",
            ],
            description="Automatically detected user intent",
        ),
        "confidence": types.Schema(
            type="number",
            description="Confidence score 0.0-1.0 for detected intent",
        ),
        "missing_data": types.Schema(
            type="array",
            items=types.Schema(type="string"),
            description="List of required data still needed from user",
        ),
        "suggested_actions": types.Schema(
            type="array",
            items=types.Schema(type="string"),
            description="List of next steps or options for user",
        ),
        "response_text": types.Schema(
            type="string",
            description="Main response text to user (conversational format)",
        ),
        "data_extracted": types.Schema(
            type="object",
            properties={
                "service_type": types.Schema(type="string"),
                "booking_date": types.Schema(type="string"),
                "booking_time": types.Schema(type="string"),
                "customer_email": types.Schema(type="string"),
                "customer_name": types.Schema(type="string"),
                "booking_id": types.Schema(type="string"),
            },
            description="Extracted booking-related data from conversation",
        ),
    },
    required=["intent", "confidence", "response_text"],
)


class BookingAgent(BaseAgent):
    """Specialized agent for handling booking/reservation queries.

    Inherits all common functionality from BaseAgent:
    - Gemini client initialization and lifecycle
    - Conversation history management
    - Base generation configuration
    - Response generation pipeline

    BookingAgent-specific additions:
    - Booking system prompt via PromptManager (with A/B testing)
    - MCP tools for booking operations
    - Function calling loop for tool execution
    - Booking-specific helper methods

    Example:
        >>> agent = BookingAgent(mcp_tools=booking_tools)
        >>> await agent.initialize()
        >>> response = await agent.generate_response(
        ...     "Quiero reservar una cita para mañana",
        ...     customer_email="maria@example.com"
        ... )
    """

    # PromptManager instance (shared across all BookingAgent instances)
    _prompt_manager: PromptManager | None = None

    # 🌍 ELEGANT MULTILINGUAL SUPPORT (Dynamic, No Hardcoding)
    # In-memory cache for generated fallback messages
    # Maps: language_code → {iteration → message}
    # Gemini 2.5 generates messages dynamically in ANY language
    _fallback_cache: dict[str, dict[int, str]] = {}

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        mcp_client: MCPConnector | None = None,
        **generation_params: Any,
    ) -> None:
        """Initialize BookingAgent with function calling support.

        Args:
            api_key: Google API key for Gemini.
            model_name: Model to use for generation.
            mcp_tools: List of MCP tools for booking operations.
            mcp_client: MCP connector for tool execution.
            **generation_params: Override generation parameters.
        """
        super().__init__(api_key, model_name, mcp_tools, **generation_params)

        # Function calling support (max iterations configurable via booking_agent_settings)
        self.mcp_client = mcp_client
        self.function_call_handler = (
            FunctionCallHandler(
                max_iterations=booking_agent_settings.BOOKING_MAX_FUNCTION_CALL_ITERATIONS
            )
            if FUNCTION_CALLING_AVAILABLE
            else None
        )

    @property
    def agent_name(self) -> str:
        """Return agent name for logging.

        Required by BaseAgent abstract property.
        """
        return "booking_agent"

    async def initialize(self) -> None:
        """Initialize BookingAgent and log available MCP tools.

        Extends BaseAgent.initialize() to log available tools for debugging.
        """
        # Initialize BaseAgent (Gemini client, config, etc.)
        await super().initialize()

        # Log MCP tools if available
        if self.mcp_tools:
            self._log_available_tools()

    def _log_available_tools(self) -> None:
        """Log available MCP tools (FunctionDeclaration format)."""
        if not self.mcp_tools:
            return

        self.logger.info("📋 Available MCP tools (FunctionDeclaration):")
        for i, func_decl in enumerate(self.mcp_tools, 1):
            tool_name = func_decl.name
            tool_description = func_decl.description or "No description"
            desc_first_line = tool_description.split("\n")[0]
            self.logger.info(f"   {i}. {tool_name}: {desc_first_line}")

    def get_system_prompt(
        self,
        customer_email: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Get system prompt for BookingAgent using PromptManager (Jinja2).

        Implements BaseAgent's abstract method.

        Configuration-driven thresholds:
        - TOKEN_ESTIMATE_RATIO: Ratio for estimating tokens from character count (default: 0.25)
        - BOOKING_MAX_PROMPT_SIZE_CHARS: Maximum prompt size in characters (warning threshold, default: 30000)

        Args:
            customer_email: Optional customer email for personalization.
            **kwargs: Additional parameters (user_id for A/B testing, etc.).

        Returns:
            System prompt text for BookingAgent.

        Example:
            >>> prompt = agent.get_system_prompt(customer_email="maria@example.com")
        """
        # Initialize PromptManager if not already done
        if self._prompt_manager is None:
            self.logger.debug("Initializing PromptManager for BookingAgent (Jinja2)")
            self._prompt_manager = PromptManager()

        # Get prompt from PromptManager (supports A/B testing and multilingual)
        user_lang = kwargs.get("user_lang", "es")
        self.logger.info(f"🌐 GET_SYSTEM_PROMPT: Requesting template for language: {user_lang}")
        prompt = self._prompt_manager.get_booking_prompt(
            customer_email=customer_email,
            user_id=kwargs.get("user_id"),
            user_lang=user_lang,  # Pass language context for template selection
        )
        prompt_size = len(prompt)
        estimated_tokens = int(prompt_size * booking_agent_settings.TOKEN_ESTIMATE_RATIO)
        self.logger.info(
            f"✅ Loaded booking prompt from Jinja2 (lang={user_lang}, "
            f"{prompt_size} chars, ~{estimated_tokens} tokens)"
        )
        # Log first 200 chars of prompt to verify template
        self.logger.debug(f"Prompt preview: {prompt[:200]}...")

        # Warn if prompt exceeds configured threshold
        if prompt_size > booking_agent_settings.BOOKING_MAX_PROMPT_SIZE_CHARS:
            self.logger.warning(
                f"⚠️ Prompt is very long: {prompt_size} chars (~{estimated_tokens} tokens)\n"
                f"   This may cause issues with Gemini API (recommended < {booking_agent_settings.BOOKING_MAX_PROMPT_SIZE_CHARS} chars)"
            )

        return prompt

    async def generate_response(
        self,
        query: str,
        *,
        include_history: bool = True,
        **kwargs: Any,
    ) -> str:
        """Generate response for user query with function calling support.

        Implements Gemini 2.5 Best Practices:
        - Scope limiting: Only booking tools are available
        - Strict system instructions: Prevents hallucinations and off-topic responses
        - Function calling with AUTO mode: Flexible, natural conversation flow
        - Runtime scope validation: Ensures no function calls outside allowed scope

        This method overrides BaseAgent.generate_response() to add function
        calling loop support. When Gemini wants to call a tool, this method:
        1. Detects the function call
        2. Validates it's in BOOKING_TOOLS_ALLOWED (scope check)
        3. Executes it via MCP
        4. Sends result back to Gemini
        5. Repeats until text response

        Args:
            query: User query/message to respond to.
            include_history: Whether to include conversation history.
            **kwargs: Agent-specific parameters (customer_email, user_id, etc.).

        Returns:
            Generated response text from agent.

        Raises:
            RuntimeError: If client not initialized or function calling not available.

        Example:
            >>> response = await booking_agent.generate_response(
            ...     "Quiero agendar para el 2025-10-27",
            ...     customer_email="customer@example.com"
            ... )

        Security Notes (Gemini 2.5):
        - All functions validated against BOOKING_TOOLS_ALLOWED before execution
        - System prompt includes explicit scope boundaries
        - Out-of-scope queries are redirected to appropriate teams
        """
        # Check if client is initialized
        if not self.client:
            self.logger.error(f"{self.agent_name} not initialized - call initialize() first")
            raise RuntimeError(f"{self.agent_name} not initialized")

        # Start timing for metrics
        import time

        start_time = time.time()
        self._metrics["total_requests"] += 1

        try:
            self.logger.info(f"Generating response for: '{query[:100]}...'")

            # Auto-detect or use provided language for consistent context
            if "language" in kwargs:
                # Priority 1: Explicit language parameter from caller
                new_language = kwargs["language"]
                if new_language != self.language:
                    self.logger.info(
                        f"🌐 Updating agent language (explicit): {self.language} → {new_language}"
                    )
                    self.language = new_language
            else:
                # Priority 2: Auto-detect language from user query
                detected_language = detect_user_language(query)
                if detected_language != self.language:
                    self.logger.info(
                        f"🌐 Auto-detected language: {self.language} → {detected_language}"
                    )
                    self.language = detected_language
                kwargs["language"] = detected_language

            # Build conversation contents (uses template method pattern)
            contents = self._build_contents(query, include_history, **kwargs)

            # DEBUG: Log contents size for diagnosis (using configurable token estimation ratio)
            total_chars = sum(len(str(content)) for content in contents)
            estimated_tokens = int(total_chars * booking_agent_settings.TOKEN_ESTIMATE_RATIO)
            self.logger.debug(
                f"Contents built: {len(contents)} messages, "
                f"{total_chars} chars, ~{estimated_tokens} tokens"
            )
            if total_chars > booking_agent_settings.BOOKING_MAX_CONTENT_SIZE_CHARS:
                self.logger.warning(
                    f"⚠️ Total contents size is very large: {total_chars} chars "
                    f"(~{estimated_tokens} tokens, threshold: {booking_agent_settings.BOOKING_MAX_CONTENT_SIZE_CHARS})"
                )

            # Build system prompt using language context (following Google Gemini best practices)
            kwargs["user_lang"] = self.language
            self.logger.info(
                f"🌐 GENERATE_RESPONSE: Agent language is '{self.language}', setting kwargs['user_lang']={self.language}"
            )
            system_prompt = self.get_system_prompt(**kwargs)
            self.logger.debug(
                f"Language: {self.language}, System prompt length: {len(system_prompt)}"
            )

            # Build generation config with system instruction
            config_dict = {
                "temperature": self.generation_config.temperature,
                "top_k": self.generation_config.top_k,
                "top_p": self.generation_config.top_p,
                "max_output_tokens": self.generation_config.max_output_tokens,
                "response_mime_type": self.generation_config.response_mime_type,
                "system_instruction": system_prompt,
            }

            # CRITICAL FIX: Only add response_schema if NO tools are available
            # When tools are present, response_schema conflicts with function_calling:
            # - response_schema forces Gemini to return structured JSON
            # - function_calling expects Gemini to return function_call parts
            # - These are mutually exclusive → response.parts becomes None
            # Solution: Use response_schema ONLY for text-only responses (no tools)
            if not self.mcp_tools:
                config_dict["response_schema"] = BOOKING_RESPONSE_SCHEMA
                self.logger.info(
                    "✅ Structured output enabled: BOOKING_RESPONSE_SCHEMA with intent detection"
                )
            else:
                self.logger.info(
                    "⏭️ Skipping response_schema (tools present): Let Gemini choose function calls naturally"
                )

            # Add tools and tool config if available
            # Implements Gemini 2.5 Function Calling Best Practices
            if self.mcp_tools:
                # Validate tools are in allowed booking tools (scope limiting)
                # BOOKING_TOOLS_ALLOWED is autodiscovered from get_booking_tool_names()
                # This prevents the agent from calling unintended functions
                # If autodiscover failed, falls back to hardcoded list
                tool_names = {func.name for func in self.mcp_tools}
                invalid_tools = tool_names - BOOKING_TOOLS_ALLOWED
                if invalid_tools:
                    self.logger.warning(
                        f"⚠️ Invalid tools passed to BookingAgent (not in BOOKING_TOOLS_ALLOWED): "
                        f"{invalid_tools}. These will be available but not recommended by system prompt."
                    )

                config_dict["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
                config_dict["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        # Mode selection rationale:
                        # - AUTO (default): Model decides when to call functions
                        #   ✅ Flexible (can choose text or function calls)
                        #   ✅ Good for booking (sometimes just answer questions)
                        #   ✅ Prevents forced function calling when not needed
                        # - ANY: Model MUST call a function (if specified allowed_function_names)
                        #   ❌ Not ideal for booking (some queries need text only)
                        # - NONE: No function calling (use only if debugging)
                        #   ❌ Defeats purpose of MCP integration
                        mode=types.FunctionCallingConfigMode.AUTO,
                    )
                )

                self.logger.info(
                    f"✅ Function calling configured: AUTO mode with {len(self.mcp_tools)} booking tools"
                )

            # CRITICAL FIX: Avoid conflict between response_schema and function_calling_loop
            # Google Gemini API returns 500 INTERNAL when response_schema is used in
            # subsequent calls within a function calling loop. Solution: create two configs:
            # 1. initial_config: WITH response_schema (for first call, intent detection)
            # 2. loop_config: WITHOUT response_schema (for function calling loop iterations)
            # Reference: https://github.com/google-gemini/generative-ai-python/issues/...

            initial_config = types.GenerateContentConfig(**config_dict)  # type: ignore[arg-type]

            # For function calling loop: remove response_schema to avoid API conflicts
            loop_config_dict = config_dict.copy()
            loop_config_dict.pop("response_schema", None)
            loop_config = types.GenerateContentConfig(**loop_config_dict)  # type: ignore[arg-type]

            self.logger.debug(
                "📋 Created two configs: initial_config (WITH schema), loop_config (WITHOUT schema)"
            )

            # Generate initial response with system_instruction in config
            # (uses response_schema for intent detection)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=initial_config,
            )

            # DEBUG: Log response details for diagnosis
            self.logger.debug(f"Response type: {type(response).__name__}")
            self.logger.debug(f"Has candidates: {hasattr(response, 'candidates')}")
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                self.logger.debug(f"Candidates count: {len(response.candidates)}")
                self.logger.debug(f"Candidate.content: {candidate.content}")
                self.logger.debug(
                    f"Candidate.finish_reason: {getattr(candidate, 'finish_reason', 'N/A')}"
                )
                self.logger.debug(
                    f"Candidate.safety_ratings: {getattr(candidate, 'safety_ratings', 'N/A')}"
                )

                # CRITICAL: Log if content is None
                if candidate.content is None:
                    self.logger.error(
                        f"🚨 Gemini returned content=None!\n"
                        f"  Query: '{query[:100]}...'\n"
                        f"  Finish reason: {getattr(candidate, 'finish_reason', 'UNKNOWN')}\n"
                        f"  Safety ratings: {getattr(candidate, 'safety_ratings', 'N/A')}"
                    )

            # Run function calling loop if tools are available
            # Use loop_config (WITHOUT response_schema) to avoid API conflicts
            if self.mcp_tools and self.function_call_handler:
                final_text = await self._run_function_calling_loop(
                    response, contents, loop_config
                )
            else:
                # No tools - extract text directly (fallback to BaseAgent behavior)
                final_text = await self._extract_text_from_response(response)

            # Update history if requested
            if include_history:
                self._update_history(
                    contents[-1],
                    types.Content(role="model", parts=[types.Part(text=final_text)]),
                )

            # Track success metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["successful_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms
            self._metrics["history_sizes"].append(len(self.conversation_history))

            self.logger.info(f"✅ Response generated ({len(final_text)} chars, {elapsed_ms:.0f}ms)")
            return final_text

        except Exception as e:
            # Track error metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["failed_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms

            # Track error type
            error_type = type(e).__name__
            self._metrics["errors"][error_type] = self._metrics["errors"].get(error_type, 0) + 1

            self.logger.exception(f"Error generating response: {e}")
            raise

    async def _run_function_calling_loop(
        self,
        response: Any,
        contents: list[types.Content],
        config: types.GenerateContentConfig,
    ) -> str:
        """Run function calling loop until text response or max iterations.

        Args:
            response: Initial Gemini API response.
            contents: Current conversation contents.
            config: Generation config with system instruction and language context.

        Returns:
            Final text response.
        """
        if not self.function_call_handler:
            raise RuntimeError("Function call handler not available")

        iteration = 0
        max_iterations = self.function_call_handler.max_iterations

        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Function calling iteration {iteration}/{max_iterations}")

            # Check if response has candidates
            if not self.function_call_handler.has_candidates(response):
                self.logger.warning("No candidates in response")
                return await self._create_fallback_response(iteration)

            # Get parts from response
            parts = self.function_call_handler.get_parts(response)

            # If parts is None, try to extract text directly from content as fallback
            if parts is None:
                self.logger.warning(
                    f"⚠️ Response parts is None (iteration {iteration}) - Gemini API issue detected"
                )
                # Log diagnostic information about response structure for debugging
                if response.candidates:
                    candidate = response.candidates[0]
                    self.logger.debug(
                        f"Response diagnostic - candidate.content: {candidate.content}, "
                        f"finish_reason: {candidate.finish_reason}"
                    )

                # GEMINI 2.5 FIX: Try to extract text and use as recovery
                try:
                    content = response.candidates[0].content if response.candidates else None
                    text = self.function_call_handler.extract_text_from_content(content)
                    if text and len(text.strip()) > 10:
                        # Got meaningful text, use it
                        self.logger.debug(f"✅ Extracted text from content: {text[:100]}...")
                        return text
                except (AttributeError, IndexError) as e:
                    self.logger.warning(f"Failed to extract text from content: {e}")

                # Use multilingual fallback response (respects self.language)
                self.logger.info(f"Using fallback response for iteration {iteration}")
                return await self._create_fallback_response(iteration)

            # Extract function calls
            function_calls = self.function_call_handler.extract_function_calls(parts)

            # If no function calls, extract and return text
            if not function_calls:
                text = self.function_call_handler.extract_text(parts)
                if text:
                    self.logger.debug(f"Extracted final text: {text[:100]}...")
                    return text
                else:
                    # Try fallback text extraction from content
                    try:
                        content = response.candidates[0].content if response.candidates else None
                        text = self.function_call_handler.extract_text_from_content(content)
                        if text:
                            self.logger.debug(f"Extracted text from content (fallback): {text[:100]}...")
                            return text
                    except (AttributeError, IndexError):
                        pass

                    self.logger.warning(f"No function calls and no text in iteration {iteration}")
                    return await self._create_fallback_response(iteration)

            # Execute function calls
            self.logger.debug(f"Found {len(function_calls)} function calls")
            function_response_parts = await self._execute_function_calls(function_calls)

            # Add function call parts to contents (model response)
            contents.append(types.Content(role="model", parts=parts))

            # Add function response parts (user role)
            contents.append(types.Content(role="user", parts=function_response_parts))

            # Generate next response with system_instruction in config
            # (maintain language context through function calling loop)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=contents,  # type: ignore[arg-type]
                config=config,
            )

        # Exhausted iterations
        self.logger.warning(f"Function calling loop exhausted after {iteration} iterations")
        return await self._create_fallback_response(iteration)

    async def _execute_function_calls(self, function_calls: list[Any]) -> list[types.Part]:
        """Execute function calls and return structured responses.

        Implements scope validation (Gemini 2.5 best practice) to ensure
        the agent only calls booking-related functions and never attempts
        to call functions outside the allowed scope.

        Args:
            function_calls: List of function call objects from response.

        Returns:
            List of FunctionResponse Parts with structured data.

        Raises:
            ValueError: If function call attempts to call non-booking function.
        """
        function_response_parts = []

        for fc in function_calls:
            function_name = fc.name
            function_args = dict(fc.args)

            # SCOPE VALIDATION: Gemini 2.5 Best Practice
            # Ensure agent only calls allowed booking tools
            if function_name not in BOOKING_TOOLS_ALLOWED:
                self.logger.error(
                    f"🚫 SCOPE VIOLATION: Attempted to call '{function_name}' "
                    f"which is NOT in BOOKING_TOOLS_ALLOWED. Returning error."
                )
                # Return error response instead of calling the invalid function
                response_data = {
                    "error": f"Function '{function_name}' is not available for this agent. "
                    f"Only booking-related functions are allowed.",
                    "function": function_name,
                    "allowed_functions": sorted(BOOKING_TOOLS_ALLOWED),
                }
                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )
                continue  # Skip to next function call

            self.logger.info(f"🔧 Executing: {function_name}({function_args})")

            try:
                # Execute tool
                result = await self._execute_tool(function_name, function_args)
                self.logger.debug(f"✅ Tool result: {type(result).__name__}")

                # Serialize result
                response_data = self._serialize_tool_result(result)

                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )

            except Exception as e:
                self.logger.exception(f"❌ Error executing {function_name}: {e}")
                # Structured error response
                response_data = {
                    "error": str(e),
                    "function": function_name,
                    "args": function_args,
                }

                function_response_parts.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=function_name, response=response_data
                        )
                    )
                )

        return function_response_parts

    async def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a single tool with proper error handling and language context.

        Propagates the agent's language context to MCP tools so responses
        are in the correct language (English or Spanish).

        Args:
            tool_name: Tool name to execute.
            args: Tool arguments.

        Returns:
            Tool result (preserving structure).

        Raises:
            RuntimeError: If no MCP client available.
        """
        if not self.mcp_client:
            raise RuntimeError("No MCP client available for tool execution")

        # Propagate language context to MCP tools (CRITICAL for multilingual support)
        if LANGUAGE_CONTEXT_AVAILABLE and set_current_language:
            set_current_language(self.language)
            self.logger.debug(f"Set MCP language context to: {self.language}")

        # Execute tool via MCP (MCP handlers will use the language context)
        result = await self.mcp_client.call_tool(tool_name, args)
        return result

    def _serialize_tool_result(self, result: Any) -> dict:
        """Serialize tool result to structured format.

        Args:
            result: Tool result to serialize.

        Returns:
            Serialized result as dictionary.
        """
        if isinstance(result, dict):
            return result
        elif isinstance(result, list):
            return {"items": result}
        elif isinstance(result, str):
            return {"result": result}
        else:
            return {"result": str(result)}

    async def _extract_text_from_response(self, response: Any) -> str:
        """Extract text from response (fallback when no tools).

        Args:
            response: Gemini API response.

        Returns:
            Extracted text.

        Raises:
            RuntimeError: If no text found.
        """
        if not response.candidates or not response.candidates[0].content:
            self.logger.error("Empty response from Gemini API")
            raise RuntimeError("No response from Gemini")

        content_parts = response.candidates[0].content.parts
        if not content_parts or len(content_parts) == 0:
            self.logger.error("Response has no content parts")
            raise RuntimeError("No content parts in response")

        response_text = content_parts[0].text
        if not response_text:
            self.logger.error("Response text is None or empty")
            raise RuntimeError("Empty response text")

        return response_text

    async def _create_fallback_response(self, iteration: int) -> str:
        """Create multilingual fallback response for ANY language.

        🌍 ELEGANT SOLUTION: Pure dynamic generation via Gemini 2.5

        No hardcoding. No translation dictionaries. Pure magic.

        Gemini 2.5 is natively multilingual - it automatically generates
        messages in ANY language the user speaks. We just cache results
        to avoid regenerating for the same user.

        Why this is elegant:
        - ✅ Zero hardcoding
        - ✅ Supports UNLIMITED languages (Arabic, Mandarin, Swahili, etc.)
        - ✅ Self-improving (Gemini gets better at languages over time)
        - ✅ Cache-aware for performance
        - ✅ Follows the project's dynamic generation pattern
        - ✅ No manual translation maintenance needed

        Args:
            iteration: Current iteration number.

        Returns:
            Language-appropriate fallback message generated by Gemini.
            Respects self.language attribute (any ISO 639-1 code).
        """
        return await self._generate_fallback_dynamic(iteration)

    async def _generate_fallback_dynamic(self, iteration: int) -> str:
        """Generate multilingual fallback message dynamically via Gemini 2.5.

        🌍 ELEGANT APPROACH: Pure dynamic generation without hardcoding

        Leverages Gemini 2.5's native multilingual capabilities to generate
        appropriate fallback messages in ANY language the user speaks.
        Results are cached in-memory to avoid regenerating for the same language.

        Why this is elegant:
        - Zero hardcoded translation dictionaries
        - Supports UNLIMITED languages automatically
        - Deterministic generation (temperature=0.3)
        - Cache-aware for performance
        - Self-improving (as Gemini models improve over time)

        Supports ANY ISO 639-1 language code:
        Arabic (ar), Chinese (zh), French (fr), German (de), Hindi (hi),
        Italian (it), Japanese (ja), Polish (pl), Portuguese (pt), Russian (ru),
        Spanish (es), Swahili (sw), Thai (th), Vietnamese (vi), etc.

        Args:
            iteration: Current iteration number (1, 2, etc.)

        Returns:
            Professional fallback message in user's language (from cache or newly generated).

        Raises:
            Exception: If Gemini API call fails after retries.
        """
        # Check cache first - avoid regenerating for same language + iteration combo
        if self.language in self._fallback_cache:
            cached_msg = self._fallback_cache[self.language].get(iteration)
            if cached_msg:
                self.logger.debug(
                    f"✅ Cached fallback (lang={self.language}, iteration={iteration})"
                )
                return cached_msg

        # Define context based on iteration number
        context_map = {
            1: (
                "first attempt at user request - we need more information from user "
                "to process their request"
            ),
            2: (
                "multiple failed attempts - a technical issue occurred during processing"
            ),
        }
        context = context_map.get(iteration, "error processing user request")

        # Construct elegant prompt that asks Gemini to generate in user's language
        fallback_prompt = f"""You are a professional customer service assistant.
Generate a brief, helpful fallback message in {self.language}.

Context: {context}

Requirements:
- Respond ONLY in {self.language} (no English, no mixed languages)
- Acknowledge the issue briefly and professionally
- Ask user to provide more details or rephrase their question
- Maximum 2 sentences
- Friendly and helpful tone
- No emojis, no special formatting

Return ONLY the message itself - nothing else."""

        try:
            # Generate response in user's language via Gemini 2.5
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=fallback_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,  # Deterministic for consistency
                    max_output_tokens=150,
                    system_instruction=(
                        "You are a multilingual assistant. "
                        "Generate responses exclusively in the specified language. "
                        "Do not include explanations or meta-information."
                    ),
                ),
            )

            # Extract message and ensure it's clean
            message = response.text.strip()

            # Validate we got content
            if not message:
                raise ValueError(f"Gemini returned empty response for language {self.language}")

            # Cache for future requests in same language
            if self.language not in self._fallback_cache:
                self._fallback_cache[self.language] = {}
            self._fallback_cache[self.language][iteration] = message

            self.logger.debug(
                f"✅ Generated fallback (lang={self.language}, iteration={iteration}, "
                f"cached for future reuse)"
            )

            return message

        except Exception as e:
            # Log the error and re-raise for upstream handling
            self.logger.error(
                f"Failed to generate fallback for language '{self.language}': {e}"
            )
            raise

    def __repr__(self) -> str:
        """String representation of BookingAgent."""
        return (
            f"BookingAgent(model={self.model_name}, "
            f"tools={len(self.mcp_tools)}, "
            f"history_len={len(self.conversation_history)}, "
            f"mcp_connected={self.mcp_client is not None})"
        )
