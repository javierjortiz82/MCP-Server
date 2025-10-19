"""Odiseo Bot - Intelligent Sales Agent with MCP Tools.

This module implements Odiseo Bot, an advanced conversational agent for
product search and sales using Google Gemini AI and MCP protocol.

This is the main orchestrator that coordinates between:
- GeminiClient: API interactions and schema conversion
- ConversationManager: History management
- ResponseValidator: Anti-hallucination validation
- DebugFormatter: Metrics formatting
- ToolExecutor: Tool execution with enhancements
"""

import asyncio
import uuid
from typing import Any

try:
    from google.genai import types
except ImportError:
    raise RuntimeError(
        "Instala la librería 'google-genai' con: pip install google-genai>=1.38.0"
    )

try:
    from gemini_agent import GeminiAgent
except ImportError:
    raise RuntimeError(
        "Instala la librería 'gemini-agent' con: pip install -e ../agent"
    )

try:
    from ..config.settings import settings
    from ..utils.logger import get_logger
    from .conversation_manager import ConversationManager
    from .debug_formatter import DebugFormatter
    from .function_call_handler import FunctionCallHandler
    from .mcp_connector import MCPConnector
    from .pagination_manager import PaginationManager
    from .prompt_builder import PromptBuilder
    from .response_processor import ResponseProcessor
    from .response_validator import ResponseValidator
    from .result_serializer import ResultSerializer
    from .thinking_manager import ThinkingManager
    from .tool_executor import ToolExecutor
except ImportError:
    # Fallback for test environment
    from config.settings import settings
    from core.conversation_manager import ConversationManager
    from core.debug_formatter import DebugFormatter
    from core.function_call_handler import FunctionCallHandler
    from core.mcp_connector import MCPConnector
    from core.pagination_manager import PaginationManager
    from core.prompt_builder import PromptBuilder
    from core.response_processor import ResponseProcessor
    from core.response_validator import ResponseValidator
    from core.result_serializer import ResultSerializer
    from core.thinking_manager import ThinkingManager
    from core.tool_executor import ToolExecutor
    from utils.logger import get_logger

# Import PromptManager for modular prompt management (Fase C integration)
try:
    import sys
    from pathlib import Path

    # Add agent src to path for PromptManager import
    agent_src = Path(__file__).parent.parent.parent / "agent" / "src"
    if str(agent_src) not in sys.path:
        sys.path.insert(0, str(agent_src))
    from multi_agent.prompt_manager import PromptManager

    PROMPT_MANAGER_AVAILABLE = True
except ImportError:
    PROMPT_MANAGER_AVAILABLE = False
    PromptManager = None  # type: ignore[assignment,misc]

# Conditional import for rate limiting
if settings.ENABLE_RATE_LIMITING:
    try:
        from .rate_limiter import RateLimiter, get_rate_limiter
    except ImportError:
        try:
            from core.rate_limiter import RateLimiter, get_rate_limiter
        except ImportError:
            # aiolimiter not installed - rate limiting will be disabled
            settings.ENABLE_RATE_LIMITING = False
            RateLimiter = None  # type: ignore[misc,assignment]
            get_rate_limiter = None  # type: ignore[assignment]


class OdiseoBot:
    """Odiseo Bot - Intelligent sales agent with emotional intelligence.

    This class implements an advanced conversational agent using:
    - Google Gemini AI for natural language understanding
    - Official MCP SDK for tool integration
    - Advanced prompt engineering (600+ lines)
    - Emotional intelligence and sentiment detection
    - Autodiscovery of MCP tools
    """

    def __init__(self, debug_mode: bool = False, user_id: str | None = None):
        """Initialize Odiseo Bot with MCP connector.

        Args:
            debug_mode: Enable debug mode for detailed logging
            user_id: Optional user ID for A/B testing (deterministic bucketing)
        """
        self.debug_mode = debug_mode
        # Use LOG_LEVEL from settings (.env) instead of debug_mode
        self.logger = get_logger("OdiseoBot", settings.LOG_LEVEL)

        # Session ID for persistence tracking
        self.session_id = uuid.uuid4()

        # User ID for A/B testing (optional)
        self.user_id = user_id or str(self.session_id)  # Fallback to session_id

        # Core components (orchestrator pattern)
        self.gemini_client: GeminiAgent | None = None
        self.conversation_manager = ConversationManager()
        self.response_validator: ResponseValidator | None = None
        self.debug_formatter = DebugFormatter()
        self.function_call_handler = FunctionCallHandler(max_iterations=10)
        self.response_processor: ResponseProcessor | None = None

        # MCP and tools
        self.system_prompt: str = ""
        self.mcp_client: MCPConnector | None = None
        self.mcp_tools: list[types.FunctionDeclaration] = []
        self.mcp_tools_raw: list[dict] = []  # Store original MCP tool definitions
        self.tool_executor: ToolExecutor | None = None

        # Prompt management (Fase C: modular prompts with A/B testing)
        self.prompt_manager: PromptManager | None = None
        self.use_modular_prompts = PROMPT_MANAGER_AVAILABLE  # Feature flag

        # Specialized managers
        self.pagination_manager = PaginationManager(session_id=self.session_id)
        self.thinking_manager = ThinkingManager(
            settings.ENABLE_THINKING,
            settings.THINKING_BUDGET,
            settings.INCLUDE_THOUGHTS,
        )

        # Generation config (singleton pattern - built once in initialize())
        self._generation_config: types.GenerateContentConfig | None = None
        self.cached_content: types.CachedContent | None = None

        # Initialize Rate Limiter (if enabled)
        if settings.ENABLE_RATE_LIMITING and get_rate_limiter is not None:
            self.rate_limiter: RateLimiter | None = get_rate_limiter()
        else:
            self.rate_limiter = None

    async def initialize(self) -> None:
        """Initialize the bot with API client and official MCP client."""
        self.logger.startup_banner("Odiseo Bot - Vendedor Inteligente")

        # Initialize Gemini Agent
        try:
            api_key = settings.get_api_key()
            self.gemini_client = GeminiAgent(api_key=api_key, model_name=settings.MODEL)
            await self.gemini_client.initialize()
            self.logger.success("Gemini Agent configurado")
        except Exception as e:
            self.logger.exception(f"Error configurando Gemini Agent: {e}")
            raise

        # Connect to MCP server using official SDK
        await self._connect_mcp_official()

        # Build system prompt with autodiscovered tools
        # Fase C: Use PromptManager (modular) with fallback to PromptBuilder (legacy)
        self.system_prompt = await self._build_system_prompt()

        # ✅ Create cached content for system instruction + tools (if enabled)
        if settings.ENABLE_CONTEXT_CACHING and self.gemini_client:
            try:
                self.logger.info(
                    "🔄 Creating context cache for system instruction + tools..."
                )
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
                self.cached_content = self.gemini_client.client.caches.create(
                    model=settings.MODEL,
                    config=types.CreateCachedContentConfig(
                        # Don't include contents parameter - system_instruction + tools is enough
                        system_instruction=self.system_prompt,
                        tools=tools_for_cache,
                        tool_config=tool_config_for_cache,
                        display_name="odiseo_system_prompt",
                        ttl=f"{ttl_seconds}s",
                    ),
                )
                token_count = (
                    self.cached_content.usage_metadata.total_token_count
                    if hasattr(self.cached_content, "usage_metadata")
                    else "unknown"
                )
                self.logger.success(
                    f"✅ System prompt + tools cached: {len(self.system_prompt)} chars, "
                    f"{len(self.mcp_tools)} tools, {token_count} tokens, TTL: {settings.CACHE_TTL_MINUTES}min"
                )
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Context caching failed: {e}. Using standard mode."
                )
                self.cached_content = None

        # ✅ Build generation config ONCE (singleton pattern) - REPLICATED FROM ORIGINAL
        self._generation_config = self._build_generation_config()

        # Initialize response validator
        if self.gemini_client:
            self.response_validator = ResponseValidator(
                conversation_history=self.conversation_manager.get_history(),
                gemini_client=self.gemini_client,
            )

            # Initialize response processor
            self.response_processor = ResponseProcessor(
                response_validator=self.response_validator,
                debug_formatter=self.debug_formatter,
                tool_executor=None,  # Will be set after tool executor initialization
            )

        cache_status = "with context cache" if self.cached_content else "standard mode"
        self.logger.success("Sistema inicializado con nuevo SDK")
        self.logger.info(
            f"📝 Sistema prompt: {len(self.system_prompt)} chars ({cache_status})"
        )
        self.logger.info(
            f"🎛️  Parámetros optimizados: temp={settings.TEMPERATURE}, top_k={settings.TOP_K}, top_p={settings.TOP_P}"
        )
        self.logger.info(
            "🔧 Tools format: FunctionDeclaration (google-genai 1.41.0 compliant)"
        )

        # Log pagination persistence status
        if self.pagination_manager._db and self.pagination_manager._db.is_enabled:
            self.logger.success("💾 Persistencia de paginación: ACTIVA")
            self.logger.info(
                f"   📊 Database: {settings.PAGINATION_DB_NAME} "
                f"(schema: test, port: {settings.PAGINATION_DB_PORT})"
            )
            self.logger.info(
                f"   ⏱️  TTL: {settings.PAGINATION_TTL_HOURS}h | "
                f"Page size: {settings.PAGINATION_PAGE_SIZE} | "
                f"Session: {str(self.session_id)[:8]}..."
            )
        else:
            self.logger.info("💾 Persistencia de paginación: Solo memoria (disabled)")

    async def _connect_mcp_official(self) -> None:
        """Connect to MCP server using official SDK."""
        try:
            self.logger.info("🔍 Conectando al servidor MCP (Official SDK)...")

            # Create official MCP client
            mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"

            # Check server health first
            self.logger.info("🏥 Verificando salud del servidor MCP...")
            health = await MCPConnector.check_server_health(mcp_url)

            if health["status"] == "unreachable":
                self.logger.error(
                    f"❌ Servidor MCP no accesible: {health.get('error')}"
                )
                self.logger.error(f"   URL: {health.get('url')}")
                raise RuntimeError(f"MCP server unreachable at {mcp_url}")

            elif health["status"] == "unhealthy":
                self.logger.error("❌ Servidor MCP en estado UNHEALTHY")
                if "checks" in health and "database" in health["checks"]:
                    db_check = health["checks"]["database"]
                    self.logger.error(f"   Database status: {db_check.get('status')}")
                    if "error" in db_check:
                        self.logger.error(f"   Error: {db_check['error']}")
                    if "warning" in db_check:
                        self.logger.error(f"   Warning: {db_check['warning']}")
                raise RuntimeError(f"MCP server unhealthy: {health}")

            elif health["status"] == "degraded":
                self.logger.warning("⚠️  Servidor MCP en estado DEGRADED")
                if "checks" in health and "database" in health["checks"]:
                    db_check = health["checks"]["database"]
                    self.logger.warning(f"   Database status: {db_check.get('status')}")
                    if "warning" in db_check:
                        self.logger.warning(f"   Warning: {db_check['warning']}")
                    if "extensions" in db_check:
                        self.logger.warning(f"   Extensions: {db_check['extensions']}")
                self.logger.warning(
                    "   Continuando conexión con capacidades limitadas..."
                )

            else:
                # Healthy status
                self.logger.success("✅ Servidor MCP saludable")
                if "checks" in health and "database" in health["checks"]:
                    db_check = health["checks"]["database"]
                    product_count = db_check.get("product_count", 0)
                    extensions = db_check.get("extensions", [])
                    self.logger.info(f"   📦 Productos: {product_count}")
                    self.logger.info(f"   🔧 Extensiones: {', '.join(extensions)}")

            # Initialize connection
            self.mcp_client = MCPConnector(mcp_url)
            await self.mcp_client.__aenter__()

            # List available tools
            tools = await self.mcp_client.list_tools()

            self.logger.mcp_connect("MCP Server (Official)", len(tools))

            # Store raw MCP tools for later use with GeminiClient
            self.mcp_tools_raw = tools

            # Convert tools to GenAI format using GeminiClient
            self.mcp_tools = self.gemini_client.convert_tools_to_genai(tools)

            if self.mcp_tools:
                self.logger.success(f"Cargadas {len(self.mcp_tools)} herramientas MCP")
                self._log_available_tools()

                # Initialize ToolExecutor with all improvements
                if (
                    settings.ENABLE_VALIDATION
                    or settings.ENABLE_CACHE
                    or settings.ENABLE_METRICS
                ):
                    self.tool_executor = ToolExecutor(self.mcp_client)
                    # Register tool schemas for validation
                    await self.tool_executor.register_tool_schemas(tools)
                    self.logger.success("Tool Executor inicializado con mejoras")

                    # Update response processor with tool executor
                    if self.response_processor:
                        self.response_processor.tool_executor = self.tool_executor

                    # Configure default fallback rules if enabled
                    if settings.ENABLE_FALLBACK and self.tool_executor:
                        self._configure_fallback_rules()
                        self.logger.success("Reglas de fallback configuradas")
            else:
                self.logger.warning("No se encontraron herramientas MCP")

        except Exception as e:
            self.logger.exception(f"Error conectando a MCP: {e}")
            self.logger.warning("Continuando sin herramientas MCP...")

    async def _build_system_prompt(self) -> str:
        """Build system prompt using PromptManager (modular) with fallback to PromptBuilder (legacy).

        This method implements the Fase C integration, using the new modular prompt
        system with A/B testing support when available, and gracefully falling back
        to the legacy PromptBuilder if PromptManager is unavailable or fails.

        Returns:
            System prompt text with MCP tools context
        """
        # Try PromptManager first (modular prompts with A/B testing)
        if self.use_modular_prompts and PROMPT_MANAGER_AVAILABLE:
            try:
                if self.prompt_manager is None:
                    self.logger.info("🎨 Initializing PromptManager (modular prompts)")
                    self.prompt_manager = PromptManager()

                # Get prompt with A/B testing support
                prompt = self.prompt_manager.get_sales_prompt(
                    mcp_tools=self.mcp_tools, user_id=self.user_id
                )

                self.logger.success(
                    f"✅ Using modular prompt system ({len(prompt)} chars, user_id={self.user_id[:8]}...)"
                )
                return prompt

            except Exception as e:
                self.logger.warning(
                    f"⚠️ PromptManager failed: {e}. Falling back to PromptBuilder."
                )

        # Fallback to legacy PromptBuilder
        self.logger.info("📝 Using legacy PromptBuilder (monolithic prompt)")
        return PromptBuilder.build_dynamic_system_prompt(self.mcp_tools)

    def _log_available_tools(self) -> None:
        """Log available MCP tools (FunctionDeclaration format)."""
        if not self.mcp_tools:
            return

        self.logger.info("📋 Herramientas MCP disponibles (FunctionDeclaration):")
        for i, func_decl in enumerate(self.mcp_tools, 1):
            tool_name = func_decl.name
            tool_description = func_decl.description or "Sin descripción"
            # Get first line of description
            desc_first_line = (
                tool_description.split("\n")[0]
                if tool_description
                else "Sin descripción"
            )
            self.logger.info(f"   {i}. {tool_name}: {desc_first_line}")

    def _configure_fallback_rules(self) -> None:
        """Configure default fallback rules for common MCP tools."""
        if not self.tool_executor:
            return

        # Get available tool names from FunctionDeclaration
        available_tools = {func_decl.name for func_decl in self.mcp_tools or []}

        # Rule 1: search_products → fuzzy_search_smart
        if (
            "search_products" in available_tools
            and "fuzzy_search_smart" in available_tools
        ):
            self.tool_executor.add_fallback_rule(
                primary_tool="search_products",
                fallback_tool="fuzzy_search_smart",
                param_mapping={"query": "search_term", "k": "limit"},
            )
            self.logger.debug("Fallback: search_products → fuzzy_search_smart")

        # Rule 2: fetch_by_sku → fetch_by_id (if both exist)
        if "fetch_by_sku" in available_tools and "fetch_by_id" in available_tools:
            self.tool_executor.add_fallback_rule(
                primary_tool="fetch_by_sku",
                fallback_tool="fetch_by_id",
                param_mapping={"sku": "product_id"},
            )
            self.logger.debug("Fallback: fetch_by_sku → fetch_by_id")

        # Rule 3: fuzzy_search_smart → search_products (reverse fallback)
        if (
            "fuzzy_search_smart" in available_tools
            and "search_products" in available_tools
        ):
            self.tool_executor.add_fallback_rule(
                primary_tool="fuzzy_search_smart",
                fallback_tool="search_products",
                param_mapping={"search_term": "query", "limit": "k"},
            )
            self.logger.debug("Fallback: fuzzy_search_smart → search_products")

    def _build_generation_config(self) -> types.GenerateContentConfig:
        """Build generation config ONCE during initialization.

        Uses cached content if available, otherwise falls back to system_instruction.

        IMPORTANT: When using cached_content, you CANNOT include system_instruction,
        tools, or tool_config in GenerateContentConfig (they must be in the cache).

        Returns:
            types.GenerateContentConfig: Singleton configuration
        """
        # Base config params (always included)
        config_params = {
            "temperature": settings.TEMPERATURE,
            "top_k": settings.TOP_K,
            "top_p": settings.TOP_P,
            "max_output_tokens": settings.MAX_OUTPUT_TOKENS,
            "thinking_config": self.thinking_manager.get_thinking_config(),
        }

        if self.cached_content:
            # ✅ Use cached content (includes system_instruction, tools, and tool_config)
            # IMPORTANT: Do NOT add tools, tool_config, or system_instruction here
            config_params["cached_content"] = self.cached_content.name
            self.logger.debug(f"✅ Using cached content: {self.cached_content.name}")
        else:
            # ✅ Fallback to standard mode (no cache)
            # Configure tool calling mode
            tool_config = None
            tools = None

            if self.mcp_tools:
                # Create Tool wrapper with function declarations
                tools = [types.Tool(function_declarations=self.mcp_tools)]
                tool_config = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO,
                        allowed_function_names=None,
                    )
                )
                self.logger.debug("✅ Tool config: AUTO mode (model decides)")

            # Add system_instruction, tools, and tool_config when NOT using cache
            config_params["system_instruction"] = self.system_prompt
            config_params["tools"] = tools
            config_params["tool_config"] = tool_config
            self.logger.debug("✅ Using standard system instruction + tools")

        return types.GenerateContentConfig(**config_params)

    async def _generate_with_rate_limit(self, contents: list[types.Content]) -> Any:
        """Generate content with rate limiting and retry logic.

        Args:
            contents: Conversation history

        Returns:
            Response from Gemini API

        Raises:
            RuntimeError: If client is not initialized
            Exception: If generation fails after retries
        """
        if self.gemini_client is None or self.gemini_client.client is None:
            raise RuntimeError("Client not initialized. Call initialize() first.")

        max_retries = 3
        retry_delay = 1.0  # Start with 1 second

        for attempt in range(max_retries):
            try:
                if self.rate_limiter:
                    # Use rate limiter
                    async with self.rate_limiter.acquire():
                        return self.gemini_client.client.models.generate_content(
                            model=settings.MODEL,
                            contents=contents,
                            config=self._generation_config,  # ✅ Use local config with tools
                        )
                else:
                    # No rate limiting
                    return self.gemini_client.client.models.generate_content(
                        model=settings.MODEL,
                        contents=contents,
                        config=self._generation_config,  # ✅ Use local config with tools
                    )

            except Exception as e:
                error_str = str(e)

                # ✅ Check if it's a cache-related 403 error (cache expired/not found)
                if (
                    "403" in error_str or "PERMISSION_DENIED" in error_str
                ) and "CachedContent" in error_str:
                    self.logger.warning(
                        "⚠️ Cache expired or not found. Fallback to standard mode..."
                    )

                    # Invalidate cache and rebuild config without cache
                    self.cached_content = None
                    self._generation_config = self._build_generation_config()
                    self.logger.info("✅ Config rebuilt in standard mode (no cache)")

                    # Retry immediately with new config (don't count as a retry)
                    continue

                # Check if it's a rate limit error (429)
                if (
                    "429" in error_str
                    or "quota" in error_str.lower()
                    or "rate limit" in error_str.lower()
                ):
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (2**attempt)  # Exponential backoff
                        self.logger.warning(
                            f"⚠️  Rate limit hit (429). Retrying in {wait_time:.1f}s... "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        self.logger.error("❌ Rate limit exceeded after all retries")
                        raise

                # Other errors - re-raise immediately
                raise

        # Should never reach here
        raise RuntimeError("Generate content failed after all retries")

    async def send_message(self, user_message: str) -> str:
        """Send a message and get response using google-genai 1.41.0 SDK.

        Professional implementation following official guidelines.

        Args:
            user_message: User's message

        Returns:
            Assistant's response
        """
        if not self.gemini_client or not self._generation_config:
            raise RuntimeError("Client no inicializado. Llama a initialize() primero.")

        try:
            # ✅ PAGINATION: Check for "show more" requests first (no AI needed)
            pagination_response = await self._handle_pagination_request(user_message)
            if pagination_response:
                self.logger.info("📄 Handled pagination request (client-side)")
                # Add to conversation history for context
                self.conversation_manager.add_user_message(user_message)
                self.conversation_manager.add_model_message(pagination_response)
                return pagination_response

            # Set user query context for tracking
            if self.tool_executor:
                self.tool_executor.set_user_query(user_message)

            # Add user message to history
            self.conversation_manager.add_user_message(user_message)

            # ✅ Generate response with rate limiting
            response = await self._generate_with_rate_limit(
                self.conversation_manager.get_history()
            )

            # Extract and log thoughts if enabled
            if self.thinking_manager.is_thinking_enabled():
                thoughts = self.thinking_manager.extract_thoughts(response)
                if thoughts and (self.debug_mode or settings.INCLUDE_THOUGHTS):
                    self.thinking_manager.log_thoughts(thoughts)

            # Manual function calling loop (Gemini doesn't auto-execute functions)
            iteration = 0

            while iteration < self.function_call_handler.max_iterations:
                iteration += 1
                self.logger.debug(
                    f"Function calling iteration {iteration}/{self.function_call_handler.max_iterations}"
                )

                # Check if response has candidates
                if not self.function_call_handler.has_candidates(response):
                    self.logger.warning("No candidates in response")
                    break

                # Get parts from response
                parts = self.function_call_handler.get_parts(response)
                if parts is None:
                    self.logger.warning(
                        "Response parts is None - cannot extract function calls or text"
                    )
                    break

                # Extract function calls
                function_calls = self.function_call_handler.extract_function_calls(
                    parts
                )

                # If no function calls, extract and process text
                if not function_calls:
                    # Extract text using handler
                    final_text = self.function_call_handler.extract_text(parts)

                    if final_text:
                        # Process response with validation and debug info
                        # (ResponseProcessor handles anti-hallucination validation internally)
                        processed_text = (
                            await self.response_processor.process_text_response(
                                final_text, user_message
                            )
                        )

                        # Add to history
                        self.conversation_manager.add_model_message(processed_text)
                        self.logger.debug(
                            f"Extracted text from parts: {processed_text[:100]}..."
                        )
                        return processed_text

                    self.logger.warning(
                        f"No function calls and no text in iteration {iteration}"
                    )
                    break

                self.logger.debug(
                    f"Found {len(function_calls)} function calls in iteration {iteration}"
                )

                # ✅ Execute function calls with structured JSON responses
                function_response_parts = await self._execute_function_calls(
                    function_calls
                )

                # Add function call parts to history as model response
                self.conversation_manager.add_function_call(parts)

                # Add function response parts - Gemini expects these as "user" role
                # This is the official pattern for function responses
                self.conversation_manager.add_function_response(function_response_parts)

                # Generate next response with rate limiting
                response = await self._generate_with_rate_limit(
                    self.conversation_manager.get_history()
                )

                # Extract and log thoughts from function calling iteration
                if self.thinking_manager.is_thinking_enabled():
                    thoughts = self.thinking_manager.extract_thoughts(response)
                    if thoughts and (self.debug_mode or settings.INCLUDE_THOUGHTS):
                        self.thinking_manager.log_thoughts(thoughts)

            # If we exhausted iterations without getting text
            self.logger.warning(
                f"Function calling loop exhausted after {iteration} iterations"
            )
            return (
                "No pude generar una respuesta final. Las herramientas se ejecutaron "
                "pero no pude procesar el resultado."
            )

        except Exception as e:
            self.logger.exception(f"Error enviando mensaje: {e}")
            raise

    async def _execute_function_calls(
        self, function_calls: list[Any]
    ) -> list[types.Part]:
        """Execute function calls and return STRUCTURED responses.

        Args:
            function_calls: List of function call objects from response

        Returns:
            List of FunctionResponse Parts with structured data
        """
        function_response_parts = []

        for fc in function_calls:
            function_name = fc.name
            function_args = dict(fc.args)

            self.logger.info(f"🔧 Executing: {function_name}")
            if self.debug_mode:
                print(f"[Function Call] {function_name}({function_args})")

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
                # ✅ Structured error response
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
            tool_name: Tool name to execute
            args: Tool arguments

        Returns:
            Tool result (preserving structure)

        Raises:
            RuntimeError: If no executor available
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
        if tool_name in ["search_products", "fuzzy_search_smart"]:
            self._track_search_results(tool_name, args, result)

        return result

    def _track_search_results(self, tool_name: str, args: dict, result: Any) -> None:
        """Track search results in pagination manager for client-side pagination.

        Args:
            tool_name: Name of search tool executed
            args: Tool arguments (contains query)
            result: Tool result (contains products)
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

            # ✅ Defensive check: ensure products is a list (not None)
            if products is None:
                self.logger.warning(
                    f"⚠️  Tool {tool_name} returned None for products - skipping pagination tracking"
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
            # Don't fail the tool execution if tracking fails
            self.logger.warning(f"⚠️ Failed to track search results: {e}")

    async def _handle_pagination_request(self, user_message: str) -> str | None:
        """Handle pagination requests ("muéstrame más", "next", etc.).

        This method provides client-side pagination for search results.
        Since the MCP server doesn't support offset/page parameters, we fetch
        more results upfront and show them in chunks when requested.

        Args:
            user_message: User's message

        Returns:
            Formatted response with next page, or None if not a pagination request
        """
        # Check if this is a "show more" request
        if not self.pagination_manager.is_show_more_request(user_message):
            return None

        # Detect which category user wants more of
        category = self.pagination_manager.detect_category(user_message)

        if not category:
            # User said "más" but we don't have context
            return None

        # Check if we have more results to show
        if not self.pagination_manager.has_more_results(category):
            # Determine response language based on user message
            if any(
                word in user_message.lower()
                for word in ["más", "siguiente", "muéstrame"]
            ):
                return f"Ya te mostré todos los resultados disponibles para {category}. ¿Te gustaría buscar algo diferente?"
            else:
                return f"I've already shown you all available results for {category}. Would you like to search for something different?"

        # Get next page of results
        next_products = self.pagination_manager.get_next_page(category)

        if not next_products:
            return None

        # Determine language for response
        spanish_mode = any(
            word in user_message.lower()
            for word in ["más", "siguiente", "muéstrame", "opciones"]
        )

        # Get remaining count and format response
        remaining = self.pagination_manager.get_remaining_count(category)

        return PaginationManager.format_pagination_response(
            category=category,
            products=next_products,
            remaining=remaining,
            spanish_mode=spanish_mode,
        )

    def _clean_json_artifacts(self, text: str) -> str:
        """Clean JSON escape artifacts from LLM responses.

        Removes escaped characters that sometimes appear when LLM processes
        JSON data (e.g., \" becomes ", \\ becomes \\).

        Args:
            text: Raw text response from LLM

        Returns:
            Cleaned text with unescaped characters
        """
        if not text:
            return text

        # Common JSON escapes to clean
        replacements = {
            '\\"': '"',  # Escaped quotes
            "\\\\": "\\",  # Escaped backslashes
            "\\n": "\n",  # Keep newlines as actual newlines
            "\\t": "\t",  # Keep tabs as actual tabs
        }

        cleaned = text
        for escaped, unescaped in replacements.items():
            cleaned = cleaned.replace(escaped, unescaped)

        return cleaned

    async def run_interactive(self) -> None:
        """Run interactive chat loop."""
        self.logger.info("\n" + "═" * 60)
        self.logger.info("🌟 ODISEO BOT - Tu Vendedor Inteligente")
        self.logger.info("═" * 60)
        self.logger.info(
            "💡 Soy Odiseo, experto en ayudarte a encontrar productos perfectos"
        )
        self.logger.info("🔧 Comandos: /exit, /debug, /help, /metrics")
        self.logger.info("─" * 60)
        self.logger.info("👋 ¡Hola! ¿Qué producto buscas hoy?\n")

        while True:
            try:
                # Get user input
                user_input = input("\n👤 Tú: ").strip()

                if not user_input:
                    continue

                # Reset shown debug hashes for new query
                self.debug_formatter.reset()

                # Handle commands
                if user_input.lower() == "/exit":
                    self.logger.info("👋 ¡Hasta luego!")
                    break
                elif user_input.lower() == "/debug":
                    self.debug_mode = not self.debug_mode
                    status = "activado" if self.debug_mode else "desactivado"
                    self.logger.info(f"🐛 Modo debug {status}")
                    continue
                elif user_input.lower() == "/help":
                    self._show_help()
                    continue
                elif user_input.lower() == "/metrics":
                    self.show_metrics()
                    continue

                # Send message and get response
                response = await self.send_message(user_input)
                print(f"\n🤖 Bot: {response}")

            except KeyboardInterrupt:
                self.logger.info("\n👋 ¡Hasta luego!")
                break
            except Exception as e:
                self.logger.exception(f"Error: {e}")

    def _show_help(self) -> None:
        """Show help information."""
        print("\n" + "═" * 60)
        print("📚 AYUDA - ODISEO BOT")
        print("═" * 60)
        print("\n🎯 ¿Qué puedo hacer por ti?")
        print("  • Buscar productos por nombre, marca o categoría")
        print("  • Encontrar productos específicos por código SKU")
        print("  • Recomendar productos según tus necesidades")
        print("  • Búsqueda inteligente con tolerancia a errores tipográficos")
        print("\n💬 Comandos especiales:")
        print("  /exit    - Salir del chat")
        print("  /debug   - Alternar modo debug (ver detalles técnicos)")
        print("  /help    - Mostrar esta ayuda")
        print("  /metrics - Ver métricas de ejecución")
        print(f"\n🔧 Herramientas MCP activas: {len(self.mcp_tools)}")
        print("\n💡 Ejemplos de consultas:")
        print('  • "Busco una laptop gaming"')
        print('  • "Quiero el producto LAPTOP-001"')
        print('  • "Necesito algo para diseño gráfico profesional"')
        print('  • "Tienes laptops ultraligeras?" (tolera errores)')
        print("─" * 60 + "\n")

    def show_metrics(self) -> None:
        """Show execution metrics if tool executor is enabled."""
        if not self.tool_executor:
            print("\n📊 Métricas no disponibles (Tool Executor no inicializado)")
            return

        print("\n" + "═" * 60)
        print("📊 MÉTRICAS DE EJECUCIÓN - ODISEO BOT")
        print("═" * 60)

        stats = self.tool_executor.get_stats()

        if "summary" in stats:
            summary = stats["summary"]
            print("\n🎯 Resumen General:")
            print(f"  Total de llamadas: {summary.get('total_tool_calls', 0)}")
            print(f"  Exitosas: {summary.get('successful_calls', 0)}")
            print(f"  Fallidas: {summary.get('failed_calls', 0)}")
            print(f"  Tasa de éxito: {summary.get('success_rate_percent', 0):.2f}%")
            print(f"  Herramientas únicas: {summary.get('unique_tools_used', 0)}")

        # Most used tools
        most_used = self.tool_executor.get_most_used_tools(5)
        if most_used:
            print("\n🔝 Herramientas Más Usadas:")
            for i, (tool_name, count) in enumerate(most_used, 1):
                print(f"  {i}. {tool_name}: {count} llamadas")

        # Slowest tools
        slowest = self.tool_executor.get_slowest_tools(5)
        if slowest:
            print("\n⏱️  Herramientas Más Lentas:")
            for i, (tool_name, avg_time) in enumerate(slowest, 1):
                print(f"  {i}. {tool_name}: {avg_time:.2f}ms promedio")

        # Error rates
        error_rates = self.tool_executor.get_error_rate_by_tool()
        if error_rates:
            print("\n❌ Tasas de Error:")
            for tool_name, rate in error_rates.items():
                if rate > 0:
                    print(f"  {tool_name}: {rate:.2f}%")

        # Cache stats
        cache_stats = self.tool_executor.get_cache_stats()
        if cache_stats:
            print("\n💾 Estado del Cache:")
            print(
                f"  Herramientas en cache: {cache_stats.get('total_tools_cached', 0)}"
            )
            print(
                f"  Cache válido: {'Sí' if cache_stats.get('has_valid_snapshot') else 'No'}"
            )

        print("─" * 60 + "\n")

    async def cleanup(self) -> None:
        """Cleanup resources and export metrics."""
        # Export metrics if enabled
        if self.tool_executor and settings.ENABLE_METRICS:
            try:
                self.tool_executor.export_metrics(settings.METRICS_EXPORT_PATH)
                self.logger.info(
                    f"📊 Métricas exportadas a: {settings.METRICS_EXPORT_PATH}"
                )
            except Exception as e:
                self.logger.warning(f"Error exportando métricas: {e}")

        # Delete context cache if exists
        if self.cached_content and self.gemini_client:
            try:
                self.gemini_client.client.caches.delete(name=self.cached_content.name)
                self.logger.info("🗑️ Context cache deleted")
            except Exception as e:
                self.logger.warning(f"Error deleting cache: {e}")

        # Disconnect MCP
        if self.mcp_client:
            try:
                await self.mcp_client.__aexit__(None, None, None)
                self.logger.info("🔌 Desconectado de servidor MCP")
            except asyncio.CancelledError:
                # CancelledError is expected during shutdown, just log and suppress
                self.logger.debug(
                    "🔌 Conexión MCP cancelada (esperado durante shutdown)"
                )
            except Exception as e:
                self.logger.exception(f"Error cerrando conexión MCP: {e}")

        # Cleanup pagination manager (close database connections)
        try:
            self.pagination_manager.cleanup()
            self.logger.debug("🔌 Pagination manager cleanup complete")
        except Exception as e:
            self.logger.warning(f"Error during pagination cleanup: {e}")
