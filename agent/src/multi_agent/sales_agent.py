"""SalesAgent - Multi-Agent Sales Specialist for Product Recommendations.

This agent handles all product sales queries including search, recommendations,
pricing, and purchase guidance. It inherits from BaseAgent for core functionality
while adding sales-specific features.

Architecture:
- Inherits from BaseAgent (Gemini client, history, metrics, config)
- Advanced features: pagination, thinking mode, context caching
- MCP integration for product catalog access
- Consistent with BookingAgent and GeneralAgent design

Author: Lab01-MCP Team
Created: 2025-10-11 (as OdiseoBotV2)
Renamed: 2025-10-12 (to SalesAgent for consistency)
Version: 3.0.0 (Breaking change - renamed from OdiseoBotV2)
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Import BaseAgent
from gemini_agent.base_agent import BaseAgent
from google.genai import types

if TYPE_CHECKING:
    from core.mcp_connector import MCPConnector

# Import client_mcp utilities (will be migrated to extensions/ in Phase 3)
# Add client_mcp to path
client_mcp_path = Path(__file__).parent.parent.parent.parent / "client_mcp"
if str(client_mcp_path) not in sys.path:
    sys.path.insert(0, str(client_mcp_path))

try:
    # Import settings from client_mcp explicitly to avoid sys.path conflicts
    # (multi_agent/__init__.py manipulates sys.path, potentially loading mcp_server.config instead)
    from importlib.util import spec_from_file_location, module_from_spec

    client_settings_path = client_mcp_path / "config" / "settings.py"
    spec = spec_from_file_location("client_mcp_settings", client_settings_path)
    if spec and spec.loader:
        client_settings_module = module_from_spec(spec)
        spec.loader.exec_module(client_settings_module)
        settings = client_settings_module.settings
    else:
        raise ImportError("Could not load client_mcp settings")

    from core.conversation_manager import ConversationManager
    from core.debug_formatter import DebugFormatter
    from core.function_call_handler import FunctionCallHandler
    from core.pagination_manager import PaginationManager
    from core.response_processor import ResponseProcessor
    from core.response_validator import ResponseValidator
    from core.result_serializer import ResultSerializer
    from core.thinking_manager import ThinkingManager
    from core.tool_executor import ToolExecutor
except ImportError as e:
    raise RuntimeError(
        f"Failed to import client_mcp utilities: {e}. Make sure client_mcp/ is accessible."
    )

# Import PromptManager for modular prompts
try:
    from multi_agent.prompt_manager import PromptManager

    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False
    PromptManager = None  # type: ignore[misc,assignment]

# Conditional import for rate limiting
if settings.ENABLE_RATE_LIMITING:
    try:
        from core.rate_limiter import RateLimiter, get_rate_limiter
    except ImportError:
        settings.ENABLE_RATE_LIMITING = False
        RateLimiter = None  # type: ignore[misc,assignment]
        get_rate_limiter = None  # type: ignore[assignment]


class SalesAgent(BaseAgent):
    """Sales agent with advanced features (pagination, thinking, caching).

    Inherits from BaseAgent:
    - Gemini client initialization ✅
    - Conversation history management ✅
    - MCP tools configuration ✅
    - Generation config ✅
    - Metrics tracking ✅

    SalesAgent-specific additions:
    - Client-side pagination (search results)
    - Gemini 2.5 thinking mode
    - Context caching (performance)
    - Advanced response validation
    - Tool execution with fallback rules
    - MCP health checks

    Example:
        >>> bot = SalesAgent(user_id="customer_123")
        >>> await bot.initialize()
        >>> response = await bot.send_message("Busco una laptop gaming")
        >>> await bot.cleanup()
    """

    def __init__(
        self,
        *,
        user_id: str | None = None,
        debug_mode: bool = False,
        mcp_client: MCPConnector | None = None,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        mcp_tools_raw: list[dict] | None = None,
        **kwargs: Any,
    ):
        """Initialize SalesAgent with dependency injection.

        This constructor follows the Dependency Injection pattern, allowing
        the AgentOrchestrator to provide pre-configured MCP client and tools.
        This eliminates code duplication and enables centralized MCP management.

        Args:
            user_id: Optional user ID for A/B testing and session tracking.
            debug_mode: Enable debug logging.
            mcp_client: Optional pre-configured MCP client (injected by orchestrator).
                If None, agent will run without MCP tools (graceful degradation).
            mcp_tools: Optional pre-converted MCP tools (FunctionDeclaration format).
                If None, agent will run without tools.
            mcp_tools_raw: Optional raw MCP tool definitions (for ToolExecutor).
            **kwargs: Additional parameters passed to BaseAgent (api_key, model_name, etc.).

        Example:
            >>> # Standalone mode (no tools)
            >>> bot = SalesAgent(user_id="user_123")
            >>> await bot.initialize()

            >>> # Orchestrated mode (with injected MCP)
            >>> bot = SalesAgent(
            ...     user_id="user_123",
            ...     mcp_client=mcp_client,
            ...     mcp_tools=tools
            ... )
            >>> await bot.initialize()
        """
        # Generate session ID for pagination persistence
        self.session_id = uuid.uuid4()
        self.user_id = user_id or str(self.session_id)
        self.debug_mode = debug_mode

        # Initialize BaseAgent (handles Gemini client, history, metrics)
        # Pass mcp_tools to BaseAgent for tool configuration
        super().__init__(mcp_tools=mcp_tools, **kwargs)

        # SalesAgent-specific managers (client-side features)
        self.pagination_manager = PaginationManager(session_id=self.session_id)
        self.thinking_manager = ThinkingManager(
            settings.ENABLE_THINKING,
            settings.THINKING_BUDGET,
            settings.INCLUDE_THOUGHTS,
        )

        # Advanced features (orchestration)
        self.conversation_manager = ConversationManager()  # For compatibility
        self.debug_formatter = DebugFormatter()
        self.function_call_handler = FunctionCallHandler(
            max_iterations=settings.FUNCTION_CALL_MAX_ITERATIONS
        )
        self.response_validator: ResponseValidator | None = None
        self.response_processor: ResponseProcessor | None = None
        self.tool_executor: ToolExecutor | None = None

        # MCP connection (injected by orchestrator or None for standalone)
        self.mcp_client = mcp_client
        self.mcp_tools_raw = mcp_tools_raw or []  # Original MCP tool definitions

        # Track ownership: only close MCP if we created it
        # If mcp_client was injected, orchestrator is responsible for closing it
        self._owns_mcp_client = False  # Will be True only if created internally

        # Pagination: autodiscovered tools that support client-side pagination
        # Fetched from tool-categories://pageable-tools resource (dynamic discovery)
        self._pageable_tools: set[str] | None = None

        # Context caching (performance optimization)
        self.cached_content: types.CachedContent | None = None

        # Rate limiting
        if settings.ENABLE_RATE_LIMITING and get_rate_limiter is not None:
            self.rate_limiter: RateLimiter | None = get_rate_limiter()
        else:
            self.rate_limiter = None

        # Prompt management (Jinja2 + PromptManager is mandatory)
        self.prompt_manager_instance: PromptManager | None = None

    @property
    def agent_name(self) -> str:
        """Return agent name for logging.

        Required by BaseAgent abstract property.
        CRITICAL: Must return "sales" (without "_agent" suffix) to match memory scope
        used in save_memory_block() and database constraints.
        """
        return "sales"

    def get_system_prompt(self, **kwargs: Any) -> str:
        """Get system prompt for SalesAgent using PromptManager (Jinja2).

        Implements BaseAgent's abstract method.

        Uses PromptManager with Jinja2 templates and A/B testing support.

        CRITICAL FIX: Includes memory blocks and conversation context in system prompt
        to help agent understand user preferences and previous conversation state.

        Args:
            **kwargs: Additional parameters (user_id, mcp_tools, etc.).

        Returns:
            System prompt text for SalesAgent.

        Example:
            >>> prompt = bot.get_system_prompt(user_id="user_123")
        """
        # Initialize PromptManager if not already done
        if self.prompt_manager_instance is None:
            self.logger.debug("🎨 Initializing PromptManager (Jinja2 templates)")
            self.prompt_manager_instance = PromptManager()

        # Get prompt with A/B testing support and multilingual
        user_lang = kwargs.get("user_lang", "es")
        prompt = self.prompt_manager_instance.get_sales_prompt(
            mcp_tools=kwargs.get("mcp_tools", self.mcp_tools),
            user_id=kwargs.get("user_id", self.user_id),
            user_lang=user_lang,  # Pass language context for template selection
        )

        # CRITICAL FIX: Append memory blocks context to system prompt
        # This helps the agent understand user preferences and conversation history
        customer_email = kwargs.get("customer_email")
        if self._memory_enabled:
            try:
                # Get session-level memory blocks (this conversation)
                session_blocks = self.get_memory_blocks(agent_scope="sales")
                if session_blocks:
                    self.logger.debug(f"Including {len(session_blocks)} session memory blocks in prompt")
                    blocks_text = "\n".join([
                        f"  - {block['block_label']}: {block['block_value']}"
                        for block in session_blocks
                    ])
                    prompt += f"\n\n## CONTEXTO DE CONVERSACIÓN (Session Memory):\n{blocks_text}"

                # Get user-level memory blocks (cross-session) for personalization
                if customer_email:
                    try:
                        user_blocks = self.memory_manager.get_user_memory_blocks(
                            customer_email=customer_email,
                            agent_scope="shared"
                        )
                        if user_blocks:
                            self.logger.debug(f"Including {len(user_blocks)} user memory blocks in prompt")
                            user_blocks_text = "\n".join([
                                f"  - {block['block_label']}: {block['block_value']}"
                                for block in user_blocks
                            ])
                            prompt += f"\n\n## PREFERENCIAS DE USUARIO (User Profile):\n{user_blocks_text}"
                    except Exception as e:
                        self.logger.debug(f"Could not load user memory blocks: {e}")
            except Exception as e:
                self.logger.debug(f"Could not include memory blocks in prompt: {e}")
                # Continue gracefully - agent can still function without memory blocks

        self.logger.debug(
            f"✅ Sales prompt loaded from Jinja2 ({len(prompt)} chars, "
            f"user_id={self.user_id[:8]}...)"
        )
        return prompt

    async def _fetch_pageable_tools(self) -> set[str]:
        """Fetch pageable tools from MCP resource (autodiscovery).

        Queries the MCP server's tool-categories://pageable-tools resource to
        dynamically discover which tools return pageable result lists. This
        eliminates the need for hardcoding tool lists (like SEARCH_TOOL_NAMES).

        Returns:
            Set of tool names that support client-side pagination.
            Falls back to default set if MCP unavailable or fetch fails.

        Example:
            >>> tools = await agent._fetch_pageable_tools()
            >>> # tools = {"fuzzy_search_smart", "search_products"}
        """
        try:
            if not self.mcp_client:
                self.logger.debug("ℹ️  No MCP client available, using default pageable tools")
                return {"fuzzy_search_smart", "search_products"}

            self.logger.debug("📥 Fetching pageable tools from MCP resource...")
            resource_uri = "tool-categories://pageable-tools"
            resource_content = await self.mcp_client.read_resource(resource_uri)

            # Extract text from TextResourceContents object
            import json

            content_text = (
                resource_content.text
                if hasattr(resource_content, "text")
                else str(resource_content)
            )
            data = json.loads(content_text)
            tool_names = set(data.get("tools", []))

            if tool_names:
                self.logger.info(
                    f"✅ Autodiscovered {len(tool_names)} pageable tools: {sorted(tool_names)}"
                )
                return tool_names
            else:
                self.logger.warning("⚠️  Pageable tools list is empty, using defaults")
                return {"fuzzy_search_smart", "search_products"}

        except Exception as e:
            self.logger.warning(f"⚠️  Failed to fetch pageable tools from MCP ({e}), using defaults")
            # Fallback to reasonable defaults
            return {"fuzzy_search_smart", "search_products"}

    async def initialize(self) -> None:
        """Initialize SalesAgent with injected MCP dependencies.

        Extends BaseAgent.initialize() with SalesAgent-specific setup:
        - Context caching (if enabled)
        - Response validation setup
        - ToolExecutor initialization (if MCP available)

        Note: MCP connection and tool autodiscovery are now handled by
        AgentOrchestrator via dependency injection (eliminates code duplication).
        """
        # Log startup banner
        self.logger.info("=" * 80)
        self.logger.info("  🌟 SALES AGENT - Product Sales & Recommendations")
        self.logger.info("=" * 80)

        # Initialize BaseAgent (Gemini client, config, etc.)
        await super().initialize()
        self.logger.info("✅ BaseAgent initialized (client, history, metrics)")

        # Log MCP status (injected or standalone)
        if self.mcp_client and self.mcp_tools:
            self.logger.info(f"✅ MCP client injected with {len(self.mcp_tools)} tools")
            self._log_available_tools()

            # Initialize ToolExecutor with injected MCP client and tools
            if settings.ENABLE_VALIDATION or settings.ENABLE_CACHE or settings.ENABLE_METRICS:
                self.tool_executor = ToolExecutor(self.mcp_client)
                if self.mcp_tools_raw:
                    await self.tool_executor.register_tool_schemas(self.mcp_tools_raw)
                    self.logger.info("✅ Tool Executor initialized with injected tools")

                    # Configure fallback rules
                    if settings.ENABLE_FALLBACK and self.tool_executor:
                        self._configure_fallback_rules()
                        self.logger.info("✅ Fallback rules configured")
        else:
            self.logger.info("⚠️ No MCP client injected - running in standalone mode (no tools)")

        # Rebuild system prompt (with injected tools or standalone)
        system_prompt = self.get_system_prompt(mcp_tools=self.mcp_tools, user_id=self.user_id)

        # Create context cache if enabled (performance optimization)
        if settings.ENABLE_CONTEXT_CACHING and self.client:
            await self._create_context_cache(system_prompt)

        # Rebuild generation config with cache or standard mode
        self.generation_config = self._build_generation_config_with_cache()

        # Initialize response validator and processor
        if self.client:
            self.response_validator = ResponseValidator(
                conversation_history=self.conversation_manager.get_history(),
                gemini_client=self,  # Pass self as it has compatible interface
            )

            self.response_processor = ResponseProcessor(
                response_validator=self.response_validator,
                debug_formatter=self.debug_formatter,
                tool_executor=self.tool_executor,
            )

        # Log pagination status
        if self.pagination_manager._db and self.pagination_manager._db.is_enabled:
            self.logger.info("💾 Persistencia de paginación: ACTIVA")
            self.logger.info(
                f"   📊 Contexto TTL: {settings.PAGINATION_TTL_HOURS}h, "
                f"Tamaño página: {settings.PAGINATION_PAGE_SIZE}"
            )
        else:
            self.logger.info("💾 Persistencia de paginación: Solo memoria")

        # Fetch pageable tools (autodiscovery from MCP resource)
        self._pageable_tools = await self._fetch_pageable_tools()

        self.logger.info("✅ SalesAgent initialized successfully")

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

    def _configure_fallback_rules(self) -> None:
        """Configure default fallback rules for common MCP tools."""
        if not self.tool_executor:
            return

        # Get available tool names
        available_tools = {func_decl.name for func_decl in self.mcp_tools or []}

        # Rule 1: search_products → fuzzy_search_smart
        if "search_products" in available_tools and "fuzzy_search_smart" in available_tools:
            self.tool_executor.add_fallback_rule(
                primary_tool="search_products",
                fallback_tool="fuzzy_search_smart",
                param_mapping={"query": "search_term", "k": "limit"},
            )
            self.logger.debug("Fallback: search_products → fuzzy_search_smart")

        # Rule 2: fuzzy_search_smart → search_products (reverse)
        if "fuzzy_search_smart" in available_tools and "search_products" in available_tools:
            self.tool_executor.add_fallback_rule(
                primary_tool="fuzzy_search_smart",
                fallback_tool="search_products",
                param_mapping={"search_term": "query", "limit": "k"},
            )
            self.logger.debug("Fallback: fuzzy_search_smart → search_products")

    async def _create_context_cache(self, system_prompt: str) -> None:
        """Create context cache for system instruction + tools (performance).

        Args:
            system_prompt: System prompt text to cache.
        """
        try:
            self.logger.info("🔄 Creating context cache for system + tools...")
            ttl_seconds = settings.CACHE_TTL_MINUTES * 60

            # Prepare tools for cache
            tools_for_cache = None
            tool_config_for_cache = None

            if self.mcp_tools:
                tools_for_cache = [types.Tool(function_declarations=self.mcp_tools)]
                tool_config_for_cache = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO,
                    )
                )

            # Note: Gemini 2.5 Flash requires minimum 1024 tokens for caching
            # system_prompt alone is usually sufficient (>1700 tokens with tools)
            self.cached_content = self.client.caches.create(
                model=self.model_name,
                config=types.CreateCachedContentConfig(
                    # Don't include contents parameter - system_instruction + tools is enough
                    system_instruction=system_prompt,
                    tools=tools_for_cache,
                    tool_config=tool_config_for_cache,
                    display_name="sales_agent_system_prompt",
                    ttl=f"{ttl_seconds}s",
                ),
            )

            token_count = (
                self.cached_content.usage_metadata.total_token_count
                if hasattr(self.cached_content, "usage_metadata")
                else "unknown"
            )

            self.logger.info(
                f"✅ Context cached: {len(system_prompt)} chars, "
                f"{len(self.mcp_tools)} tools, {token_count} tokens, "
                f"TTL: {settings.CACHE_TTL_MINUTES}min"
            )

        except Exception as e:
            self.logger.warning(f"⚠️ Context caching failed: {e}. Using standard mode.")
            self.cached_content = None

    def _build_generation_config_with_cache(self) -> types.GenerateContentConfig:
        """Build generation config with context cache or standard mode.

        Returns:
            GenerateContentConfig with cache or standard configuration.
        """
        # Base config params
        config_params = {
            "temperature": self._generation_params.get("temperature", settings.TEMPERATURE),
            "top_k": self._generation_params.get("top_k", settings.TOP_K),
            "top_p": self._generation_params.get("top_p", settings.TOP_P),
            "max_output_tokens": self._generation_params.get(
                "max_output_tokens", settings.MAX_OUTPUT_TOKENS
            ),
            "thinking_config": self.thinking_manager.get_thinking_config(),
        }

        if self.cached_content:
            # Use cached content (includes system_instruction, tools, tool_config)
            config_params["cached_content"] = self.cached_content.name
            self.logger.debug(f"✅ Using cached content: {self.cached_content.name}")
        else:
            # Standard mode - add system_instruction, tools, tool_config
            system_prompt = self.get_system_prompt(mcp_tools=self.mcp_tools, user_id=self.user_id)

            tools = None
            tool_config = None

            if self.mcp_tools:
                tools = [types.Tool(function_declarations=self.mcp_tools)]
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO,
                    )
                )
                self.logger.debug("✅ Tool config: AUTO mode")

            config_params["system_instruction"] = system_prompt
            config_params["tools"] = tools
            config_params["tool_config"] = tool_config
            self.logger.debug("✅ Using standard system instruction + tools")

        return types.GenerateContentConfig(**config_params)

    async def send_message(self, user_message: str, **kwargs) -> str:
        """Send message and get response (SalesAgent's main method).

        Refactored for better maintainability (was 123 lines → ~35 lines).
        Uses extracted methods for cleaner code and easier testing.

        This is the main entry point for user queries. It:
        1. Validates client initialization
        2. Checks for pagination requests ("muéstrame más")
        3. Generates response using BaseAgent
        4. Executes function calls in a loop
        5. Returns final response

        Args:
            user_message: User's message/query.
            **kwargs: Additional parameters including language and intent.

        Returns:
            Bot's response text.

        Example:
            >>> response = await bot.send_message("Busco una laptop gaming")
            >>> response = await bot.send_message("I want a gaming laptop", language="en")

        Raises:
            RuntimeError: If bot not initialized.
        """
        try:
            # Update agent language if provided in kwargs (allows orchestrator to change language per-query)
            if "language" in kwargs:
                new_language = kwargs["language"]
                if new_language != self.language:
                    self.logger.info(
                        f"🌐 Updating agent language: {self.language} → {new_language}"
                    )
                    self.language = new_language

            # Store intent for DB persistence (passed from AgentOrchestrator)
            self.current_intent = kwargs.get("intent", None)

            # 1. Validate client is ready
            self._validate_client_initialized()

            # 2. Try pagination shortcut (no AI needed)
            pagination_response = await self._try_pagination_shortcut(user_message)
            if pagination_response:
                return pagination_response

            # 3. Prepare context and generate initial response
            response = await self._prepare_message_context(user_message)

            # 4. Run function calling loop and get tool_calls and token_count
            final_response, tool_calls, token_count = await self._run_function_calling_loop(response, user_message)

            # 5. Persist to database if memory is enabled
            if self._memory_enabled and self.memory_manager and self.session_id:
                self.logger.info(
                    f"📝 Persisting to DB (session={self.session_id[:8]}, "
                    f"intent={self.current_intent}, tokens={token_count}, tools={len(tool_calls) if tool_calls else 0})"
                )
                self._update_history(
                    types.Content(role="user", parts=[types.Part(text=user_message)]),
                    types.Content(role="model", parts=[types.Part(text=final_response)]),
                    response_time_ms=None,  # SalesAgent doesn't track response time yet
                    tool_calls=tool_calls,
                    token_count=token_count
                )

            return final_response

        except Exception as e:
            self.logger.exception(f"Error sending message: {e}")
            raise

    def _validate_client_initialized(self) -> None:
        """Validate that client and config are initialized.

        Raises:
            RuntimeError: If client not initialized.
        """
        if not self.client or not self.generation_config:
            raise RuntimeError("Bot not initialized. Call initialize() first.")

    async def _try_pagination_shortcut(self, user_message: str) -> str | None:
        """Try to handle pagination request without AI (fast path).

        Args:
            user_message: User's message

        Returns:
            Pagination response if applicable, None otherwise
        """
        pagination_response = await self._handle_pagination_request(user_message)
        if pagination_response:
            self.logger.info("📄 Handled pagination request (client-side)")
            # Add to conversation history for context
            self.conversation_manager.add_user_message(user_message)
            self.conversation_manager.add_model_message(pagination_response)
        return pagination_response

    async def _prepare_message_context(self, user_message: str) -> Any:
        """Prepare message context and generate initial response.

        Args:
            user_message: User's message

        Returns:
            Initial Gemini API response
        """
        # Set user query context for tracking
        if self.tool_executor:
            self.tool_executor.set_user_query(user_message)

        # Add user message to history
        self.conversation_manager.add_user_message(user_message)

        # Generate response (with retry, cache handling, and rate limiting)
        response = await self._generate_content(self.conversation_manager.get_history())

        # Extract and log thoughts if enabled
        self._extract_and_log_thoughts(response)

        return response

    def _extract_and_log_thoughts(self, response: Any) -> None:
        """Extract and log thinking process if enabled.

        Args:
            response: Gemini API response
        """
        if self.thinking_manager.is_thinking_enabled():
            thoughts = self.thinking_manager.extract_thoughts(response)
            if thoughts and (self.debug_mode or settings.INCLUDE_THOUGHTS):
                self.thinking_manager.log_thoughts(thoughts)

    async def _run_function_calling_loop(self, response: Any, user_message: str) -> tuple[str, list[dict[str, Any]] | None, int | None]:
        """Run function calling loop until text response or max iterations.

        Args:
            response: Initial Gemini API response
            user_message: Original user message for validation

        Returns:
            Tuple of (final_text, tool_calls, token_count) where:
            - final_text: The final response text
            - tool_calls: List of tool calls executed during the loop
            - token_count: Total token count from final Gemini response
        """
        iteration = 0
        max_iterations = self.function_call_handler.max_iterations

        # Track all tool calls for analytics/debugging
        tool_calls_log: list[dict[str, Any]] = []
        self._current_tool_calls = tool_calls_log  # Store for _execute_function_calls access

        # Helper function to extract token count from response
        def extract_token_count(resp: Any) -> int | None:
            try:
                if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
                    return resp.usage_metadata.total_token_count
            except (AttributeError, TypeError):
                pass
            return None

        while iteration < max_iterations:
            iteration += 1
            self.logger.debug(f"Function calling iteration {iteration}/{max_iterations}")

            # Process one iteration
            result = await self._process_single_iteration(response, user_message, iteration)

            # Check if we got a final response
            if isinstance(result, str):
                return (result, tool_calls_log if tool_calls_log else None, extract_token_count(response))

            # Otherwise, result is the next response to process
            response = result

        # Exhausted iterations
        self.logger.warning(f"Function calling loop exhausted after {iteration} iterations")
        return (settings.FALLBACK_ERROR_MESSAGE_ES, tool_calls_log if tool_calls_log else None, extract_token_count(response))

    async def _process_single_iteration(
        self, response: Any, user_message: str, iteration: int
    ) -> str | Any:
        """Process a single function calling iteration.

        Args:
            response: Current Gemini API response
            user_message: Original user message
            iteration: Current iteration number

        Returns:
            Either final text response (str) or next response to process (Any)
        """
        # Check if response has candidates
        if not self.function_call_handler.has_candidates(response):
            self.logger.warning("No candidates in response")
            return await self._create_fallback_response(iteration)

        # Get parts from response
        parts = self.function_call_handler.get_parts(response)
        if parts is None:
            self.logger.warning("Response parts is None - cannot extract function calls or text")
            return await self._create_fallback_response(iteration)

        # Extract function calls
        function_calls = self.function_call_handler.extract_function_calls(parts)

        # If no function calls, process text response
        if not function_calls:
            return await self._handle_text_response(parts, user_message, iteration)

        # Execute functions and continue loop
        return await self._handle_function_execution(function_calls, parts)

    async def _handle_text_response(self, parts: list, user_message: str, iteration: int) -> str:
        """Handle final text response (no function calls).

        Args:
            parts: Response parts from Gemini
            user_message: Original user message for validation
            iteration: Current iteration number

        Returns:
            Processed text response
        """
        # Extract text using handler
        final_text = self.function_call_handler.extract_text(parts)

        if final_text:
            # Process response with validation and debug info
            processed_text = await self.response_processor.process_text_response(
                final_text, user_message
            )

            # Add to conversation manager history (in-memory, for Gemini context)
            self.conversation_manager.add_model_message(processed_text)
            self.logger.debug(f"Extracted text: {processed_text[:100]}...")
            return processed_text

        # No text found
        self.logger.warning(f"No function calls and no text in iteration {iteration}")
        return await self._create_fallback_response(iteration)

    async def _handle_function_execution(self, function_calls: list, parts: list) -> Any:
        """Execute function calls and generate next response.

        Args:
            function_calls: List of function calls to execute
            parts: Response parts containing function calls

        Returns:
            Next Gemini API response
        """
        self.logger.debug(f"Found {len(function_calls)} function calls")

        # Execute function calls with structured JSON responses
        function_response_parts = await self._execute_function_calls(function_calls)

        # Add function call parts to history as model response
        self.conversation_manager.add_function_call(parts)

        # Add function response parts - Gemini expects these as "user" role
        self.conversation_manager.add_function_response(function_response_parts)

        # Generate next response (with retry, cache handling, and rate limiting)
        response = await self._generate_content(self.conversation_manager.get_history())

        # Extract and log thoughts from function calling iteration
        self._extract_and_log_thoughts(response)

        return response

    # NOTE: _create_fallback_response and _generate_fallback_dynamic removed
    # These methods are now inherited from BaseAgent (DRY principle)
    # BaseAgent provides shared multilingual fallback generation for all agents

    async def _generate_content(self, contents: list[types.Content]) -> Any:
        """Generate content with SalesAgent-specific logic (cache + rate limiter).

        This method wraps the Gemini API call with:
        - Cache error handling (CachedContent expiration)
        - Rate limiter integration (if available)
        - Retry logic via BaseAgent.response_handler (Google best practices)

        Args:
            contents: Conversation history

        Returns:
            Gemini API response

        Raises:
            RuntimeError: If client not initialized
            Exception: If generation fails after retries
        """
        if self.client is None:
            raise RuntimeError("Client not initialized")

        # Define the actual generation function
        async def _do_generate() -> Any:
            if self.rate_limiter:
                # Use rate limiter
                async with self.rate_limiter.acquire():
                    return self.client.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=self.generation_config,
                    )
            else:
                # No rate limiting
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=self.generation_config,
                )

        # Try with cache, fallback to standard mode if cache expired
        try:
            if self.response_handler:
                # Use retry logic from BaseAgent
                return await self.response_handler.retry_with_backoff(_do_generate)
            else:
                # Direct call (legacy mode)
                return await _do_generate()

        except Exception as e:
            error_str = str(e)

            # Check if cache-related error (specific to SalesAgent)
            if "CachedContent" in error_str and "not found" in error_str:
                self.logger.warning("⚠️ Cache expired. Rebuilding config in standard mode...")

                # Invalidate cache and rebuild config
                self.cached_content = None
                self.generation_config = self._build_generation_config_with_cache()
                self.logger.info("✅ Config rebuilt without cache")

                # Retry once with new config
                if self.response_handler:
                    return await self.response_handler.retry_with_backoff(_do_generate)
                else:
                    return await _do_generate()

            # Other errors - re-raise
            raise

    async def _execute_function_calls(self, function_calls: list[Any]) -> list[types.Part]:
        """Execute function calls and return structured responses.

        Args:
            function_calls: List of function call objects from response.

        Returns:
            List of FunctionResponse Parts with structured data.
        """
        function_response_parts = []

        for fc in function_calls:
            function_name = fc.name
            function_args = dict(fc.args)

            # Track tool call for analytics/debugging (if tracking is enabled)
            if hasattr(self, '_current_tool_calls'):
                self._current_tool_calls.append({
                    "tool_name": function_name,
                    "args": function_args,
                })

            self.logger.info(f"🔧 Executing: {function_name}")
            if self.debug_mode:
                self.logger.debug(f"[Function Call] {function_name}({function_args})")

            try:
                # Execute tool and serialize result
                result = await self._execute_tool(function_name, function_args)
                response_data = ResultSerializer.serialize_tool_result(result)
                self.logger.debug(f"✅ Result type: {type(response_data).__name__}")

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
        """Execute a single tool with proper error handling.

        Args:
            tool_name: Tool name to execute.
            args: Tool arguments.

        Returns:
            Tool result (preserving structure).

        Raises:
            RuntimeError: If no executor available.
        """
        # Execute tool
        if self.tool_executor:
            result = await self.tool_executor.execute_tool(
                tool_name, args, validate=settings.ENABLE_VALIDATION
            )
        elif self.mcp_client:
            result = await self.mcp_client.call_tool(tool_name, args)
        else:
            raise RuntimeError("No tool executor or MCP client available")

        # ✅ PAGINATION: Track search results for client-side pagination
        # Use autodiscovered pageable tools instead of hardcoded SEARCH_TOOL_NAMES
        if self._pageable_tools and tool_name in self._pageable_tools:
            self._track_search_results(tool_name, args, result)

        return result

    def _track_search_results(self, tool_name: str, args: dict, result: Any) -> None:
        """Track search results in pagination manager for client-side pagination.

        Args:
            tool_name: Name of search tool executed.
            args: Tool arguments (contains query).
            result: Tool result (contains products).
        """
        try:
            # Extract query and products from result
            query = args.get("query", args.get("search_term", "general"))

            # Handle different result formats
            products = []
            if isinstance(result, dict):
                if "items" in result:
                    products = result["items"]
                elif "products" in result:
                    products = result["products"]
            elif isinstance(result, list):
                products = result

            # Defensive check: ensure products is a list (not None)
            if products is None:
                self.logger.warning(
                    f"⚠️ Tool {tool_name} returned None for products - skipping pagination tracking"
                )
                return

            # Only save if we have products
            if products and isinstance(products, list):
                category = self.pagination_manager.extract_category_from_query(query)

                self.pagination_manager.save_search(
                    category=category,
                    tool=tool_name,
                    query=query,
                    results=products,
                    page_size=settings.PAGINATION_PAGE_SIZE,
                )

                self.logger.debug(
                    f"📋 Saved {len(products)} products for pagination (category: {category})"
                )

        except Exception as e:
            # Don't fail tool execution if tracking fails
            self.logger.warning(f"⚠️ Failed to track search results: {e}")

    async def _handle_pagination_request(self, user_message: str) -> str | None:
        """Handle pagination requests ("muéstrame más", "next", etc.).

        This method provides client-side pagination for search results.
        Since the MCP server doesn't support offset/page parameters, we fetch
        more results upfront and show them in chunks when requested.

        Args:
            user_message: User's message.

        Returns:
            Formatted response with next page, or None if not a pagination request.
        """
        # Check if this is a "show more" request
        if not self.pagination_manager.is_show_more_request(user_message):
            return None

        # Detect which category user wants more of
        category = self.pagination_manager.detect_category(user_message)

        if not category:
            # User said "más" but we don't have context
            return None

        # Parse language-specific keywords from configuration
        spanish_keywords = settings.PAGINATION_KEYWORDS_ES.split(",")
        settings.PAGINATION_KEYWORDS_EN.split(",")

        # Check if we have more results to show
        if not self.pagination_manager.has_more_results(category):
            # Determine response language
            is_spanish = any(word.strip() in user_message.lower() for word in spanish_keywords)
            if is_spanish:
                return (
                    f"Ya te mostré todos los resultados disponibles para {category}. "
                    "¿Te gustaría buscar algo diferente?"
                )
            else:
                return (
                    f"I've already shown you all available results for {category}. "
                    "Would you like to search for something different?"
                )

        # Get next page of results
        next_products = self.pagination_manager.get_next_page(category)

        if not next_products:
            return None

        # Determine language for response (configurable keywords)
        spanish_mode = any(word.strip() in user_message.lower() for word in spanish_keywords)

        # Get remaining count and format response
        remaining = self.pagination_manager.get_remaining_count(category)

        return PaginationManager.format_pagination_response(
            category=category,
            products=next_products,
            remaining=remaining,
            spanish_mode=spanish_mode,
        )

    async def cleanup(self) -> None:
        """Cleanup resources (extends BaseAgent.cleanup()).

        Cleans up:
        - Tool executor metrics export
        - Context cache deletion
        - MCP connection
        - Pagination database
        - BaseAgent resources
        """
        # Export metrics if enabled
        if self.tool_executor and settings.ENABLE_METRICS:
            try:
                self.tool_executor.export_metrics(settings.METRICS_EXPORT_PATH)
                self.logger.info(f"📊 Metrics exported to: {settings.METRICS_EXPORT_PATH}")
            except Exception as e:
                self.logger.warning(f"Error exporting metrics: {e}")

        # Delete context cache if exists
        if self.cached_content and self.client:
            try:
                self.client.caches.delete(name=self.cached_content.name)
                self.logger.info("🗑️ Context cache deleted")
            except Exception as e:
                self.logger.warning(f"Error deleting cache: {e}")

        # Disconnect MCP (only if we own it)
        # If MCP client was injected by orchestrator, it's responsible for closing it
        if self.mcp_client and self._owns_mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
                self.logger.info("🔌 Disconnected from MCP server")
            except asyncio.CancelledError:
                self.logger.debug("🔌 MCP connection cancelled (expected during shutdown)")
            except Exception as e:
                self.logger.exception(f"Error closing MCP connection: {e}")
        elif self.mcp_client and not self._owns_mcp_client:
            self.logger.debug("🔌 MCP client not closed (managed by orchestrator)")

        # Cleanup pagination manager (close database connections)
        try:
            self.pagination_manager.cleanup()
            self.logger.debug("🔌 Pagination manager cleanup complete")
        except Exception as e:
            self.logger.warning(f"Error during pagination cleanup: {e}")

        # Call BaseAgent cleanup (history, metrics, etc.)
        await super().cleanup()

    def __repr__(self) -> str:
        """String representation of SalesAgent."""
        return (
            f"SalesAgent(model={self.model_name}, "
            f"tools={len(self.mcp_tools)}, "
            f"session={str(self.session_id)[:8]}..., "
            f"history={len(self.conversation_history)})"
        )
