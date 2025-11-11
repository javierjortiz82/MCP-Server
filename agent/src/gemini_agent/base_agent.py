"""Base Agent - Abstract Base Class for All Specialized Agents.

This module provides the BaseAgent abstract class that encapsulates common
functionality shared across all specialized agents (Booking, General, Sales, etc.).

By centralizing common code in BaseAgent, we:
- Eliminate ~280 lines of duplicated code across agents
- Follow DRY (Don't Repeat Yourself) principle
- Make it trivial to create new agents (only 2 methods to implement)
- Ensure consistency across all agents
- Simplify maintenance and testing

Architecture:
    BaseAgent (abstract)
      ├── BookingAgent (reservations with MCP tools)
      ├── GeneralAgent (general info without tools)
      └── SalesAgent (sales with MCP tools + pagination)

Usage Example:
    >>> class MyAgent(BaseAgent):
    ...     @property
    ...     def agent_name(self) -> str:
    ...         return "my_agent"
    ...
    ...     def get_system_prompt(self, **kwargs) -> str:
    ...         return "You are MyAgent..."
    ...
    >>> agent = MyAgent()
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Hello!")

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.0.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC
from typing import Any, TypedDict

from gemini_agent.config import settings
from gemini_agent.utils.gemini_response_handler import (
    GeminiResponseHandler,
    ResponseStatus,
    RetryConfig,
)
from gemini_agent.utils.language_detector import detect_user_language
from gemini_agent.utils.logger import setup_logging
from google import genai
from google.genai import types

# Observability imports (OPCIÓN 7)
try:
    from email_service.observability.metrics import get_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    from email_service.observability.context import (
        create_request_context,
        clear_request_context,
    )
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False


class MetricsDict(TypedDict):
    """Type definition for agent metrics dictionary."""

    total_requests: int
    successful_requests: int
    failed_requests: int
    total_response_time_ms: float
    errors: dict[str, int]
    history_sizes: list[int]


class BaseAgent(ABC):
    """Abstract base class for all specialized agents.

    This class provides common functionality for agent initialization, conversation
    management, and response generation. All specialized agents (Booking, General,
    Sales, etc.) inherit from this base class.

    **Common Functionality** (inherited by all agents):
    - Gemini client initialization and management
    - Conversation history tracking with automatic trimming
    - Generation configuration with customizable parameters
    - Common lifecycle methods (initialize, cleanup)
    - MCP tools integration support
    - Logging infrastructure
    - Response validation and retry logic (Google Best Practices)
    - Multilingual fallback message generation

    **Required Implementations** (must be provided by subclasses):
    - `agent_name` property: Unique identifier for logging
    - `get_system_prompt()` method: Agent-specific system instructions

    **Optional Overrides** (can be customized by subclasses):
    - `_build_generation_config()`: Customize generation parameters
    - `_build_contents()`: Customize conversation structure
    - `generate_response()`: Add specialized logic (e.g., function calling)
    - `_create_response_handler()`: Customize retry config
    - `_handle_validation_failure()`: Customize error handling

    Attributes:
        api_key: Google API key for Gemini (from settings if not provided)
        model_name: Model to use (e.g., 'gemini-2.5-flash-thinking-exp-1206')
        mcp_tools: List of MCP tool declarations for function calling
        client: Gemini client instance (initialized in initialize())
        generation_config: Configuration for response generation
        conversation_history: List of conversation turns (auto-trimmed to 20 items)
        logger: Logger instance with agent-specific name
        response_handler: Response validator and retry handler (optional)

    Example:
        >>> class CustomAgent(BaseAgent):
        ...     @property
        ...     def agent_name(self) -> str:
        ...         return "custom_agent"
        ...
        ...     def get_system_prompt(self, **kwargs) -> str:
        ...         return "You are a custom agent specialized in..."
        ...
        >>> agent = CustomAgent(api_key="YOUR_API_KEY")
        >>> await agent.initialize()
        >>> response = await agent.generate_response("What can you do?")
        >>> print(response)
    """

    # 🌍 ELEGANT MULTILINGUAL SUPPORT (shared by all agents)
    # In-memory cache for generated fallback messages
    # Maps: language_code → {iteration → message}
    # Gemini 2.5 generates messages dynamically in ANY language
    _fallback_cache: dict[str, dict[int, str]] = {}

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        session_id: str | None = None,
        memory_manager: Any | None = None,
        language: str = "es",
        enable_response_handler: bool = True,
        **generation_params: Any,
    ) -> None:
        """Initialize base agent with common parameters.

        Args:
            api_key: Google API key for Gemini (uses settings.GOOGLE_API_KEY if not provided).
            model_name: Model to use for generation (uses settings.MODEL if not provided).
            mcp_tools: List of MCP tools (FunctionDeclaration format) for function calling.
                Default is empty list (no tools).
            session_id: Optional session ID for persistent memory (UUID).
                If provided with memory_manager, enables conversation persistence.
            memory_manager: Optional MemoryManager instance for persistent context.
                If None, agent operates in stateless mode (RAM-only history).
            language: Language code for prompts ("es" or "en", default: "es").
            enable_response_handler: Enable response validation and retry logic (default: True).
                If False, agent operates without retry/validation (legacy mode).
                GeneralAgent disables this to reduce overhead.
            **generation_params: Override generation parameters:
                - temperature: Sampling temperature (0.0-1.0)
                - top_k: Top K sampling parameter
                - top_p: Top P (nucleus) sampling parameter
                - max_output_tokens: Maximum tokens to generate

        Note:
            The agent is not fully initialized until `initialize()` is called.
            This separation allows for flexible configuration before Gemini
            client initialization.
        """
        # Core configuration
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name or settings.MODEL
        self.mcp_tools = mcp_tools or []
        self.language = language  # Language for prompts (es or en)

        # Gemini client components (initialized in initialize())
        self.client: genai.Client | None = None
        self.generation_config: types.GenerateContentConfig | None = None

        # Conversation state
        self.conversation_history: list[types.Content] = []

        # Persistent memory (optional)
        self.session_id = session_id
        self.memory_manager = memory_manager
        self._memory_enabled = memory_manager is not None and session_id is not None

        # Store generation params for config building
        self._generation_params = generation_params

        # Metrics tracking (typed for MyPy)
        self._metrics: MetricsDict = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time_ms": 0.0,
            "errors": {},  # {error_type: count}
            "history_sizes": [],  # Track history size over time
        }

        # Setup logging with agent-specific name
        self.logger = setup_logging(self.agent_name)

        # Initialize observability (OPCIÓN 7)
        if OBSERVABILITY_AVAILABLE:
            self.structured_logger = get_structured_logger(f"agent.{self.agent_name}")
            self.metrics = get_metrics_collector()
        else:
            self.structured_logger = None
            self.metrics = None

        # Initialize response handler for retry + validation (Google Best Practices)
        # Subclasses can override _create_response_handler() for custom config
        if enable_response_handler:
            self.response_handler: GeminiResponseHandler | None = self._create_response_handler()
        else:
            self.response_handler = None

        self.logger.info(
            f"Initializing {self.agent_name} - "
            f"Model: {self.model_name}, "
            f"Tools: {len(self.mcp_tools)}, "
            f"Memory: {'✅ Enabled' if self._memory_enabled else '❌ Disabled'}, "
            f"Response Handler: {'✅ Enabled' if self.response_handler else '❌ Disabled'}, "
            f"API Key: {'***REDACTED***' if self.api_key else 'None'}, "
            f"Observability: {'✅ Enabled' if OBSERVABILITY_AVAILABLE else '❌ Disabled'}"
        )

        if self.structured_logger:
            self.structured_logger.info(
                "Agent initialization started",
                agent_type=self.agent_name,
                model=self.model_name,
                tools_count=len(self.mcp_tools),
                memory_enabled=self._memory_enabled
            )

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Get agent name for logging and identification.

        This property must be implemented by all subclasses to provide
        a unique identifier for the agent (e.g., 'booking_agent', 'sales_agent').

        The name is used for:
        - Logger instance naming
        - Debugging and metrics tracking
        - Agent identification in multi-agent systems

        Returns:
            Agent name string (e.g., 'booking_agent', 'general_agent')

        Example:
            >>> class MyAgent(BaseAgent):
            ...     @property
            ...     def agent_name(self) -> str:
            ...         return "my_agent"
        """
        pass

    @abstractmethod
    def get_system_prompt(self, **kwargs: Any) -> str:
        """Get agent-specific system prompt.

        This method must be implemented by all subclasses to provide the
        system instructions that define the agent's behavior, knowledge,
        and capabilities.

        Subclasses should:
        - Use PromptManager to load modular prompts
        - Support A/B testing with user_id parameter
        - Include agent-specific knowledge and rules
        - Define interaction patterns and tone

        Args:
            **kwargs: Agent-specific parameters:
                - user_id: For A/B testing (deterministic bucketing)
                - customer_email: For personalization
                - Other agent-specific context

        Returns:
            System prompt text that defines agent behavior

        Example:
            >>> class BookingAgent(BaseAgent):
            ...     def get_system_prompt(self, customer_email=None, **kwargs):
            ...         manager = PromptManager()
            ...         return manager.get_booking_prompt(
            ...             customer_email=customer_email,
            ...             user_id=kwargs.get('user_id')
            ...         )
        """
        pass

    def _create_response_handler(self) -> GeminiResponseHandler:
        """Create response handler with default retry configuration.

        This method creates a GeminiResponseHandler with Google's recommended
        retry settings (exponential backoff with jitter). Subclasses can override
        this method to customize retry behavior.

        Default configuration:
        - max_retries: 3 attempts
        - base_delay: 1.0 seconds
        - max_delay: 60.0 seconds
        - multiplier: 2.0 (exponential backoff: 1s, 2s, 4s, ...)
        - jitter: True (random variation to prevent thundering herd)

        Returns:
            GeminiResponseHandler instance configured for this agent

        Example (custom config in subclass):
            >>> class SalesAgent(BaseAgent):
            ...     def _create_response_handler(self) -> GeminiResponseHandler:
            ...         retry_config = RetryConfig(
            ...             max_retries=5,  # More retries for sales
            ...             base_delay=0.5,  # Faster retry
            ...         )
            ...         return GeminiResponseHandler(
            ...             logger=self.logger,
            ...             retry_config=retry_config,
            ...         )
        """
        retry_config = RetryConfig(
            max_retries=3,  # 3 retry attempts for transient errors
            base_delay=1.0,  # Start with 1 second delay
            max_delay=60.0,  # Cap at 60 seconds
            multiplier=2.0,  # Exponential backoff (1s, 2s, 4s, ...)
            jitter=True,  # Add random jitter to prevent thundering herd
        )
        return GeminiResponseHandler(
            logger=self.logger,
            retry_config=retry_config,
        )

    async def _handle_validation_failure(
        self,
        status: ResponseStatus,
        diagnostic: str,
        query: str,
    ) -> str:
        """Handle response validation failure (template method - overridable by subclasses).

        This method is called when response validation fails (e.g., safety block,
        empty response, etc.). Default behavior is to raise an exception, but
        subclasses can override to provide custom fallback responses.

        Args:
            status: Response validation status (SAFETY_BLOCKED, EMPTY_RESPONSE, etc.)
            diagnostic: Diagnostic message explaining the failure
            query: Original user query (for context in error messages)

        Returns:
            Fallback response text (if subclass overrides with custom logic)

        Raises:
            RuntimeError: Default behavior - raises exception with diagnostic info

        Example (custom handling in subclass):
            >>> class BookingAgent(BaseAgent):
            ...     async def _handle_validation_failure(self, status, diagnostic, query):
            ...         if status == ResponseStatus.SAFETY_BLOCKED:
            ...             return await self._create_fallback_response(iteration=1)
            ...         return await super()._handle_validation_failure(status, diagnostic, query)
        """
        self.logger.error(
            f"Response validation failed: {status} - {diagnostic}\n"
            f"Query: '{query[:100]}...'"
        )
        raise RuntimeError(f"Gemini API validation failed: {status}")

    async def _create_fallback_response(self, iteration: int) -> str:
        """Create multilingual fallback response for ANY language (shared by all agents).

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
            iteration: Current iteration number (1, 2, etc.)

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
            # Validate client is initialized
            if self.client is None:
                raise RuntimeError(
                    "Gemini client not initialized. Call initialize() first."
                )

            # Generate response in user's language via Gemini 2.5
            # Use response_handler if available, otherwise direct call
            if self.response_handler:
                response = await self.response_handler.retry_with_backoff(
                    self.client.aio.models.generate_content,
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

                # Validate response before extracting text
                status, diagnostic_msg = self.response_handler.validate_response(response)
                if status != ResponseStatus.SUCCESS:
                    self.logger.error(
                        f"❌ Fallback generation failed validation: {status} - {diagnostic_msg}"
                    )
                    raise ValueError(
                        f"Gemini returned invalid response for language {self.language}: {status}"
                    )
            else:
                # Direct call without retry/validation
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=fallback_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=150,
                        system_instruction=(
                            "You are a multilingual assistant. "
                            "Generate responses exclusively in the specified language. "
                            "Do not include explanations or meta-information."
                        ),
                    ),
                )

            # Extract message and ensure it's clean
            if response.text is None:
                raise ValueError(f"Gemini returned None response for language {self.language}")

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

    async def initialize(self) -> None:
        """Initialize the Gemini client and generation configuration.

        This method must be called before using the agent to generate responses.
        It performs the following initialization steps:
        1. Creates Gemini client with provided API key
        2. Builds generation configuration with tools (if provided)
        3. Auto-loads conversation history from database (if memory enabled)
        4. Logs successful initialization

        Raises:
            RuntimeError: If client initialization fails (e.g., invalid API key)

        Example:
            >>> agent = BookingAgent()
            >>> await agent.initialize()  # Must call before generate_response()
            >>> response = await agent.generate_response("Hello")
        """
        try:
            self.logger.debug(f"Initializing Gemini client for {self.agent_name}...")

            if self.structured_logger:
                self.structured_logger.debug("Initializing Gemini client", agent=self.agent_name)

            # Initialize Gemini client
            self.client = genai.Client(api_key=self.api_key)

            # Build generation configuration
            self.generation_config = self._build_generation_config(**self._generation_params)

            # CRITICAL FIX: Auto-load conversation history from database (context preservation)
            # This ensures agents maintain conversation context across requests
            if self._memory_enabled:
                try:
                    messages_loaded = self.load_history_from_db(limit=10)
                    self.logger.info(
                        f"✅ Auto-loaded {messages_loaded} messages from DB "
                        f"(session={self.session_id[:8]}..., memory enabled)"
                    )
                except Exception as history_error:
                    self.logger.warning(
                        f"⚠️ Failed to auto-load conversation history: {history_error}. "
                        f"Agent will start with empty context."
                    )
                    # Continue gracefully - agent can still function without history
            else:
                self.logger.debug(
                    "Memory not enabled - conversation history will remain empty "
                    "(stateless mode)"
                )

            self.logger.info(
                f"✅ {self.agent_name} initialized successfully "
                f"({len(self.mcp_tools)} tools available, "
                f"{len(self.conversation_history)} messages in context)"
            )

            if self.structured_logger:
                self.structured_logger.info(
                    "Agent initialized successfully",
                    agent=self.agent_name,
                    tools_available=len(self.mcp_tools),
                    context_messages=len(self.conversation_history)
                )

        except Exception as e:
            self.logger.exception(f"Failed to initialize {self.agent_name}: {e}")
            if self.structured_logger:
                self.structured_logger.exception(f"Agent initialization failed", agent=self.agent_name)
            raise RuntimeError(f"{self.agent_name} initialization failed: {e}") from e

    @classmethod
    async def resume_session(
        cls,
        session_id: str,
        memory_manager: Any,
        load_history: bool = True,
        load_user_memory: bool = True,
        show_summary: bool = True,
        **agent_params: Any,
    ) -> BaseAgent:
        """Resume a conversation session with automatic context loading.

        This is a convenience method that creates an agent with memory enabled,
        initializes it, and optionally loads conversation history from database.
        Provides a one-liner to resume previous conversations.

        Args:
            session_id: Session UUID to resume
            memory_manager: MemoryManager instance
            load_history: Automatically load history from DB (default: True)
            load_user_memory: Automatically load user-level memory blocks (default: True)
            show_summary: Print session summary (default: True)
            **agent_params: Additional parameters passed to agent __init__:
                - api_key: Google API key
                - model_name: Gemini model
                - mcp_tools: MCP tools list
                - temperature, top_k, etc.

        Returns:
            Initialized agent with loaded context (session-level + user-level)

        Raises:
            RuntimeError: If session doesn't exist or initialization fails

        Example:
            >>> from multi_agent import MemoryManager, GeneralAgent
            >>> memory = MemoryManager()
            >>> agent = await GeneralAgent.resume_session(
            ...     session_id="a8a32296-...",
            ...     memory_manager=memory
            ... )
            # Output:
            # "Resuming session a8a32296..."
            # "Last activity: 2 hours ago"
            # "Loaded 10 messages, 4 session memory blocks, 7 user memory blocks"
            >>> response = await agent.generate_response("Continue conversation")
        """
        import logging
        from datetime import datetime

        logger = logging.getLogger("base_agent.resume_session")

        try:
            # Verify session exists
            stats = memory_manager.get_session_statistics(session_id)
            if not stats:
                raise RuntimeError(f"Session {session_id} not found in database")

            if show_summary:
                logger.info(f"🔄 Resuming session {session_id[:8]}...")

            # Create agent with memory enabled
            agent = cls(session_id=session_id, memory_manager=memory_manager, **agent_params)

            # Initialize Gemini client
            await agent.initialize()

            # Load history if requested
            messages_loaded = 0
            if load_history:
                try:
                    messages_loaded = agent.load_history_from_db(limit=10)
                except Exception as e:
                    logger.warning(f"Failed to load history: {e}")

            # Get session-level memory blocks count
            session_blocks_count = 0
            try:
                blocks = agent.get_memory_blocks()
                session_blocks_count = len(blocks)
            except Exception:
                pass

            # Load user-level memory blocks if available
            user_blocks_count = 0
            customer_email = None
            if load_user_memory:
                try:
                    # Get session info to retrieve customer_email
                    session_info = memory_manager.get_session_info(session_id)
                    if session_info and session_info.get("customer_email"):
                        customer_email = session_info["customer_email"]
                        # Get user memory blocks
                        user_blocks = memory_manager.get_user_memory_blocks(
                            customer_email=customer_email,
                            agent_scope="shared",  # Load shared cross-session blocks
                        )
                        user_blocks_count = len(user_blocks)
                        logger.debug(
                            f"Loaded {user_blocks_count} user memory blocks for {customer_email}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to load user memory blocks: {e}")

            # Show summary
            if show_summary:
                # Calculate time since last activity (if available)
                last_activity = "unknown"
                try:
                    # Get session info from DB
                    from psycopg2 import sql
                    from utils.db import fetchone

                    schema = memory_manager.schema
                    # Use SQL identifier to prevent SQL injection
                    query = sql.SQL(
                        "SELECT last_activity_at FROM {}.conversation_sessions WHERE id = %s"
                    ).format(sql.Identifier(schema))
                    result = fetchone(query.as_string(), (session_id,))
                    if result and result.get("last_activity_at"):
                        last_activity_dt = result["last_activity_at"]
                        now = datetime.now(UTC)
                        delta = now - last_activity_dt
                        if delta.total_seconds() < 60:
                            last_activity = "just now"
                        elif delta.total_seconds() < 3600:
                            last_activity = f"{int(delta.total_seconds() / 60)} minutes ago"
                        elif delta.total_seconds() < 86400:
                            last_activity = f"{int(delta.total_seconds() / 3600)} hours ago"
                        else:
                            last_activity = f"{int(delta.total_seconds() / 86400)} days ago"
                except Exception:
                    pass

                logger.info("📊 Session info:")
                logger.info(f"   - Last activity: {last_activity}")
                logger.info(f"   - Total messages: {stats.get('total_messages', 0)}")
                logger.info(f"   - Loaded to RAM: {messages_loaded} messages")
                logger.info(f"   - Session memory blocks: {session_blocks_count}")
                if load_user_memory and customer_email:
                    logger.info(f"   - User memory blocks: {user_blocks_count} (cross-session)")
                    logger.info(f"   - Customer: {customer_email}")
                logger.info("✅ Session resumed successfully")

            return agent

        except Exception as e:
            logger.exception(f"Failed to resume session: {e}")
            raise RuntimeError(f"Session resumption failed: {e}") from e

    def _build_generation_config(
        self,
        temperature: float | None = None,
        top_k: int | None = None,
        top_p: float | None = None,
        max_output_tokens: int | None = None,
    ) -> types.GenerateContentConfig:
        """Build generation configuration for Gemini.

        This method creates a GenerateContentConfig with specified parameters,
        using settings defaults for any parameters not provided. Automatically
        includes MCP tools configuration if tools are available.

        Args:
            temperature: Sampling temperature (0.0-1.0). Higher values make output
                more random. Uses settings.TEMPERATURE if not provided.
            top_k: Top K sampling parameter (1-40). Limits vocabulary to K most
                likely tokens. Uses settings.TOP_K if not provided.
            top_p: Top P (nucleus) sampling parameter (0.0-1.0). Limits vocabulary
                to tokens with cumulative probability <= P. Uses settings.TOP_P if not provided.
            max_output_tokens: Maximum tokens to generate. Uses settings.MAX_OUTPUT_TOKENS
                if not provided.

        Returns:
            Generation configuration with specified parameters and tools (if available).

        Note:
            MCP tools are automatically included if self.mcp_tools is not empty.
            Subclasses no longer need to override this method just to add tools.
        """
        # Use settings defaults if parameters not provided
        temp = temperature if temperature is not None else settings.TEMPERATURE
        k = top_k if top_k is not None else settings.TOP_K
        p = top_p if top_p is not None else settings.TOP_P
        tokens = max_output_tokens if max_output_tokens is not None else settings.MAX_OUTPUT_TOKENS

        self.logger.debug(
            f"Generation config: temp={temp}, top_k={k}, top_p={p}, max_tokens={tokens}"
        )

        # Base configuration parameters
        config_params = {
            "temperature": temp,
            "top_k": k,
            "top_p": p,
            "max_output_tokens": tokens,
            "response_mime_type": "text/plain",
        }

        # ✅ Automatically add MCP tools if available
        if self.mcp_tools:
            config_params["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
            config_params["tool_config"] = types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.AUTO,
                )
            )
            self.logger.debug(f"Added {len(self.mcp_tools)} MCP tools to generation config")

        # Type ignore: MyPy can't infer kwargs unpacking for GenerateContentConfig
        return types.GenerateContentConfig(**config_params)  # type: ignore[arg-type]

    # =========================================================================
    # MCP Tool Conversion Methods (Common to All Agents)
    # =========================================================================

    def convert_tools_to_genai(
        self, mcp_tools: list[dict[str, Any]]
    ) -> list[types.FunctionDeclaration]:
        """Convert MCP tools to Google GenAI FunctionDeclaration format.

        This method converts MCP tool definitions (from MCP server) to the
        FunctionDeclaration format expected by Google Gemini's function calling API.

        Args:
            mcp_tools: List of MCP tool definitions with format:
                {
                    "name": str,
                    "description": str,
                    "inputSchema": dict  # JSON Schema
                }

        Returns:
            List of FunctionDeclaration for Google GenAI.

        Example:
            >>> mcp_tools = await mcp_client.list_tools()
            >>> agent.mcp_tools = agent.convert_tools_to_genai(mcp_tools)
            >>> # Now agent can use tools in function calling

        Note:
            This method is stateless and can be called multiple times.
            Common use case: Converting MCP tools during initialization.
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
            self.logger.debug(f"Converted tool: {tool_name} -> FunctionDeclaration")

        return function_declarations

    def _convert_json_schema_to_gemini_schema(self, json_schema: dict[str, Any]) -> types.Schema:
        """Convert JSON Schema to Gemini Schema format.

        Args:
            json_schema: JSON Schema from MCP tool definition (inputSchema field).

        Returns:
            types.Schema for FunctionDeclaration parameters.

        Note:
            This is a helper method for convert_tools_to_genai().
            Handles recursive conversion of nested schemas.

            IMPORTANT: Filters out 'ctx' parameter which is MCP Context (auto-injected
            by MCP framework, not passed by callers).
        """
        properties = json_schema.get("properties", {})
        required = json_schema.get("required", [])

        # Convert properties to Gemini format, EXCLUDING 'ctx' (MCP Context parameter)
        gemini_properties = {}
        for prop_name, prop_def in properties.items():
            # Skip 'ctx' parameter - it's auto-injected by MCP framework
            if prop_name == "ctx":
                self.logger.debug("Skipping 'ctx' parameter (MCP Context, auto-injected)")
                continue
            gemini_properties[prop_name] = self._convert_property_to_schema(prop_def)

        # Also filter 'ctx' from required list
        filtered_required = [r for r in required if r != "ctx"] if required else []

        return types.Schema(
            type=types.Type.OBJECT,
            properties=gemini_properties,
            required=filtered_required if filtered_required else None,
        )

    def _convert_property_to_schema(self, prop_def: dict[str, Any]) -> types.Schema:
        """Convert a single JSON Schema property to Gemini Schema.

        Handles complex property types including arrays, objects, and primitives.
        Recursively processes nested schemas.

        Args:
            prop_def: Property definition from JSON Schema.

        Returns:
            types.Schema for the property.

        Note:
            This is a helper method for _convert_json_schema_to_gemini_schema().
            Supports: string, integer, number, boolean, array, object types.
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
                gemini_nested_properties[nested_prop_name] = self._convert_property_to_schema(
                    nested_prop_def
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
            json_type: JSON Schema type string (e.g., 'string', 'integer', 'array').

        Returns:
            types.Type enum value for Gemini.

        Note:
            This is a helper method for _convert_property_to_schema().
            Defaults to STRING for unknown types.
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

    async def generate_response(
        self,
        query: str,
        *,
        include_history: bool = True,
        intent: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate response for user query.

        This is the main method for generating agent responses. It follows
        the template method pattern, allowing subclasses to customize specific
        steps while maintaining consistent overall structure.

        Workflow:
        1. Validate client is initialized
        2. Build conversation contents (system prompt + history + query)
        3. Call Gemini API to generate response
        4. Extract response text
        5. Update conversation history (if include_history=True)
        6. Track metrics (requests, latency, errors)

        Args:
            query: User query/message to respond to.
            include_history: Whether to include conversation history in context.
                Set to False for stateless interactions.
            **kwargs: Agent-specific parameters passed to get_system_prompt():
                - user_id: For A/B testing
                - customer_email: For personalization
                - Other agent-specific context

        Returns:
            Generated response text from agent.

        Raises:
            RuntimeError: If client not initialized (call initialize() first).
            Exception: If response generation fails.

        Example:
            >>> agent = BookingAgent()
            >>> await agent.initialize()
            >>> response = await agent.generate_response(
            ...     "I want to book an appointment",
            ...     customer_email="maria@example.com"
            ... )
            >>> print(response)

        Note:
            Subclasses can override this method to add specialized logic
            (e.g., function calling loop, pagination handling). See OdiseoBot
            for an example of complex override.
        """
        # Start timing for metrics
        import time

        start_time = time.time()

        # Create request context for this query (OPCIÓN 7)
        if self.structured_logger:
            request_ctx = create_request_context(
                email_id=None,  # Not applicable for agents
                recipient=None,
                operation=f"agent_generate_response.{self.agent_name}",
                custom_fields={"query_preview": query[:50], "include_history": include_history}
            )

        # Track request
        self._metrics["total_requests"] += 1
        if self.metrics:
            self.metrics.increment_counter(f"{self.agent_name}_queries", 1)

        # Check if initialized
        if not self.client:
            self._metrics["failed_requests"] += 1
            error_type = "RuntimeError"
            self._metrics["errors"][error_type] = self._metrics["errors"].get(error_type, 0) + 1
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["total_response_time_ms"] += elapsed_ms

            if self.metrics:
                self.metrics.increment_counter(f"{self.agent_name}_not_initialized", 1)
            if self.structured_logger:
                self.structured_logger.error("Agent not initialized", agent=self.agent_name)
                clear_request_context()

            self.logger.error(f"{self.agent_name} not initialized - call initialize() first")
            raise RuntimeError(f"{self.agent_name} not initialized")

        try:
            # Store intent for use in _update_history()
            self.current_intent = intent

            self.logger.info(f"Generating response for: '{query[:100]}...'")

            # Auto-detect or use provided language for consistent context (prevents language switching)
            if "language" in kwargs:
                # Priority 1: Explicit language parameter from caller
                new_language = kwargs["language"]
                if new_language != self.language:
                    self.logger.info(
                        f"🌐 Updating agent language (explicit): {self.language} → {new_language}"
                    )
                    self.language = new_language
            else:
                # Priority 2: Auto-detect language from user query (prevents English input → Spanish output)
                detected_language = detect_user_language(query)
                if detected_language != self.language:
                    self.logger.info(
                        f"🌐 Auto-detected language: {self.language} → {detected_language}"
                    )
                    self.language = detected_language
                kwargs["language"] = detected_language

            # Build conversation contents (uses template method pattern)
            contents = self._build_contents(query, include_history, **kwargs)

            # Build system prompt using language context
            kwargs["user_lang"] = self.language
            system_prompt = self.get_system_prompt(**kwargs)

            self.logger.debug(f"Generating with {len(self.mcp_tools)} tools available")
            self.logger.debug(
                f"Language: {self.language}, System prompt length: {len(system_prompt)}"
            )

            # Build generation config with system instruction (following Google Gemini best practices)
            # Create a config copy with the language-specific system instruction
            config_dict = {
                "temperature": self.generation_config.temperature,
                "top_k": self.generation_config.top_k,
                "top_p": self.generation_config.top_p,
                "max_output_tokens": self.generation_config.max_output_tokens,
                "response_mime_type": self.generation_config.response_mime_type,
                "system_instruction": system_prompt,
            }

            # Add tools and tool config if available
            if self.mcp_tools:
                config_dict["tools"] = [types.Tool(function_declarations=self.mcp_tools)]
                config_dict["tool_config"] = types.ToolConfig(
                    function_calling_config=types.FunctionCallingConfig(
                        mode=types.FunctionCallingConfigMode.AUTO,
                    )
                )

            dynamic_config = types.GenerateContentConfig(**config_dict)  # type: ignore[arg-type]

            # Generate response with system_instruction in config
            # Use response_handler for retry + validation if available (Google Best Practices)
            if self.response_handler:
                # With retry logic and exponential backoff
                if self.metrics:
                    async with self.metrics.record_latency_async(
                        f"{self.agent_name}_generate_latency",
                        tags={"model": self.model_name, "has_tools": len(self.mcp_tools) > 0}
                    ):
                        response = await self.response_handler.retry_with_backoff(
                            self.client.aio.models.generate_content,
                            model=self.model_name,
                            contents=contents,  # type: ignore[arg-type]
                            config=dynamic_config,
                        )
                else:
                    response = await self.response_handler.retry_with_backoff(
                        self.client.aio.models.generate_content,
                        model=self.model_name,
                        contents=contents,  # type: ignore[arg-type]
                        config=dynamic_config,
                    )

                # Validate response before processing
                status, diagnostic = self.response_handler.validate_response(response)
                if status != ResponseStatus.SUCCESS:
                    self.logger.warning(
                        f"⚠️ Response validation failed: {status} - {diagnostic}"
                    )
                    # Call template method for custom error handling (overridable by subclasses)
                    return await self._handle_validation_failure(status, diagnostic, query)

            else:
                # Legacy mode: No retry, no validation
                if self.metrics:
                    async with self.metrics.record_latency_async(
                        f"{self.agent_name}_generate_latency",
                        tags={"model": self.model_name, "has_tools": len(self.mcp_tools) > 0}
                    ):
                        response = await self.client.aio.models.generate_content(
                            model=self.model_name,
                            contents=contents,  # type: ignore[arg-type]
                            config=dynamic_config,
                        )
                else:
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,  # type: ignore[arg-type]
                        config=dynamic_config,
                    )

            self.logger.debug("Response generated successfully")
            if self.structured_logger:
                self.structured_logger.debug("Response generated", agent=self.agent_name)

            # Extract response text with safe indexing
            if not response.candidates or not response.candidates[0].content:
                # Log detailed error information for debugging
                self.logger.error("Empty response from Gemini API - DIAGNOSTIC INFO:")
                self.logger.error(f"  - Response object: {response}")
                self.logger.error(f"  - Has candidates: {bool(response.candidates)}")
                if hasattr(response, "prompt_feedback"):
                    self.logger.error(f"  - Prompt feedback: {response.prompt_feedback}")
                if response.candidates:
                    for idx, candidate in enumerate(response.candidates):
                        self.logger.error(f"  - Candidate {idx}:")
                        if hasattr(candidate, "finish_reason"):
                            self.logger.error(f"    - Finish reason: {candidate.finish_reason}")
                        if hasattr(candidate, "safety_ratings"):
                            self.logger.error(f"    - Safety ratings: {candidate.safety_ratings}")
                        if hasattr(candidate, "content"):
                            self.logger.error(f"    - Has content: {bool(candidate.content)}")
                raise RuntimeError("No response from Gemini")

            # Safe indexing: check if parts exists and has at least one element
            content_parts = response.candidates[0].content.parts
            if not content_parts or len(content_parts) == 0:
                self.logger.error("Response has no content parts")
                raise RuntimeError("No content parts in response")

            response_text = content_parts[0].text
            if not response_text:
                self.logger.error("Response text is None or empty")
                raise RuntimeError("Empty response text")

            # Calculate elapsed time BEFORE updating history (for accurate DB storage)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # Extract tool calls from response (for analytics)
            tool_calls = self._extract_tool_calls(response.candidates[0].content)

            # Update history (uses template method pattern)
            if include_history:
                self._update_history(
                    contents[-1],
                    response.candidates[0].content,
                    response_time_ms=elapsed_ms,
                    tool_calls=tool_calls
                )

            # Track success metrics
            self._metrics["successful_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms
            self._metrics["history_sizes"].append(len(self.conversation_history))

            if self.metrics:
                self.metrics.increment_counter(f"{self.agent_name}_successful_responses", 1)
                self.metrics.increment_counter(f"{self.agent_name}_response_tokens", len(response_text))
                self.metrics.set_gauge(f"{self.agent_name}_history_size", len(self.conversation_history))

            self.logger.info(
                f"✅ Response generated ({len(response_text)} chars, {elapsed_ms:.0f}ms)"
            )

            if self.structured_logger:
                self.structured_logger.info(
                    "Response generated successfully",
                    agent=self.agent_name,
                    response_length=len(response_text),
                    elapsed_ms=elapsed_ms
                )
                clear_request_context()

            return response_text

        except Exception as e:
            # Track error metrics
            elapsed_ms = (time.time() - start_time) * 1000
            self._metrics["failed_requests"] += 1
            self._metrics["total_response_time_ms"] += elapsed_ms

            # Track error type
            error_type = type(e).__name__
            self._metrics["errors"][error_type] = self._metrics["errors"].get(error_type, 0) + 1

            if self.metrics:
                self.metrics.increment_counter(f"{self.agent_name}_failed_responses", 1)
                self.metrics.increment_counter(f"{self.agent_name}_error_{error_type}", 1)

            self.logger.exception(f"Error generating response: {e}")

            if self.structured_logger:
                self.structured_logger.exception(
                    "Response generation failed",
                    agent=self.agent_name,
                    error_type=error_type,
                    elapsed_ms=elapsed_ms
                )
                clear_request_context()

            raise

    def _build_contents(
        self,
        query: str,
        include_history: bool,
        **kwargs: Any,
    ) -> list[types.Content]:
        """Build conversation contents for Gemini API.

        This method constructs the conversation context that will be sent to
        Gemini. IMPORTANT: System prompt is NO LONGER included here. It's passed
        via system_instruction parameter in generate_content() to follow Google
        Gemini API best practices for multilingual support.

        This method builds:
        1. Model acknowledgment (establishes agent role)
        2. Conversation history (previous turns, if include_history=True)
        3. Current user query

        Subclasses can override this method to customize the conversation
        structure (e.g., different acknowledgment message, additional context).

        Args:
            query: Current user query.
            include_history: Whether to include conversation history.
            **kwargs: Parameters passed through to get_system_prompt().

        Returns:
            List of Content objects representing the conversation.

        Note:
            - System prompt now goes ONLY in system_instruction parameter
            - This is a template method that can be overridden by subclasses
            - Supports multilingual responses via system_instruction
        """
        contents = []

        # Add model acknowledgment (establishes agent role) - language-aware
        if self.language == "en":
            ack_message = f"Understood. I'm {self.agent_name}. How can I help you?"
        else:
            ack_message = f"Entendido. Soy {self.agent_name}. ¿En qué puedo ayudarte?"

        contents.append(
            types.Content(
                role="model",
                parts=[types.Part(text=ack_message)],
            )
        )

        # Add conversation history if requested
        if include_history:
            contents.extend(self.conversation_history)

        # Add current query
        contents.append(types.Content(role="user", parts=[types.Part(text=query)]))

        return contents

    def _extract_tool_calls(self, model_content: types.Content) -> list[dict[str, Any]] | None:
        """Extract tool/function calls from Gemini response for database storage.

        Processes the model response to identify and extract function calls
        that were made during generation. Returns structured metadata for
        analytics and debugging.

        Args:
            model_content: Gemini model response content that may contain function calls.

        Returns:
            List of tool call dictionaries with structure:
            [
                {
                    "tool_name": str,           # Name of the function called
                    "args": dict,                # Arguments passed to function
                    "execution_time_ms": int,    # Execution time (if available)
                }
            ]
            Returns None if no function calls were made.

        Example:
            >>> response = await client.generate_content(...)
            >>> tool_calls = self._extract_tool_calls(response.candidates[0].content)
            >>> print(tool_calls)
            [{"tool_name": "get_products", "args": {"category": "laptops"}, "execution_time_ms": 45}]

        Note:
            This method only extracts metadata about tool calls. The actual
            function execution is handled by Gemini's function calling system.
        """
        if not model_content or not model_content.parts:
            return None

        tool_calls = []
        for part in model_content.parts:
            # Check if this part is a function call
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                tool_call_info = {
                    "tool_name": func_call.name,
                    "args": dict(func_call.args) if func_call.args else {},
                }
                tool_calls.append(tool_call_info)

        return tool_calls if tool_calls else None

    def _update_history(
        self,
        user_content: types.Content,
        model_content: types.Content,
        response_time_ms: int | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        token_count: int | None = None,
    ) -> None:
        """Update conversation history with automatic size management.

        Adds user and model messages to conversation history and automatically
        trims history to prevent context window overflow. Maintains the most
        recent 20 conversation turns (10 user + 10 model).

        If memory_manager is enabled, also persists messages to database for
        long-term storage and analytics.

        Args:
            user_content: User message to add to history.
            model_content: Model response to add to history.
            response_time_ms: Response generation time in milliseconds (for analytics).
            tool_calls: List of function calls made during response generation.
            token_count: Total token count from Gemini response (for cost tracking).

        Note:
            History trimming is automatic and transparent to the caller.
            The 20-turn limit balances context preservation with API limits.
            Database persistence happens asynchronously if enabled.
        """
        # Add to in-memory history (RAM - short-term)
        self.conversation_history.append(user_content)
        self.conversation_history.append(model_content)

        # Persist to database (PostgreSQL - long-term) if enabled
        self.logger.info(
            f"🔍 DEBUG _update_history: _memory_enabled={self._memory_enabled}, "
            f"memory_manager={self.memory_manager is not None}, "
            f"session_id={self.session_id is not None}"
        )
        if self._memory_enabled and self.memory_manager and self.session_id:
            self.logger.info("✅ Entering DB persistence block...")
            try:
                # Extract text from Content objects (ensure non-None strings for Pydantic)
                user_text = (user_content.parts[0].text if user_content.parts else "") or ""
                model_text = (model_content.parts[0].text if model_content.parts else "") or ""

                self.logger.info(
                    f"🔍 Extracted texts - user: '{user_text[:50]}...' ({len(user_text)} chars), "
                    f"model: '{model_text[:50]}...' ({len(model_text)} chars)"
                )

                # Save user message (no agent_name, response_time, or tool_calls for user)
                self.memory_manager.save_message(
                    session_id=self.session_id,
                    role="user",
                    message_text=user_text,
                    intent=self.current_intent,  # Use intent passed from AgentRouter
                )

                # Save model message with performance metrics and tool calls
                self.memory_manager.save_message(
                    session_id=self.session_id,
                    role="model",
                    agent_name=self.agent_name,
                    message_text=model_text,
                    intent=self.current_intent,  # Use intent passed from AgentRouter
                    tool_calls=tool_calls,
                    response_time_ms=response_time_ms,
                    token_count=token_count,
                )

                self.logger.info(
                    f"✅ Messages persisted to DB (session={self.session_id[:8]}, "
                    f"response_time={response_time_ms}ms, tokens={token_count}, tools={len(tool_calls) if tool_calls else 0})"
                )
            except Exception as e:
                # Non-critical: Log but don't fail if persistence fails
                self.logger.error(f"❌ Failed to persist messages to DB: {e}", exc_info=True)

        # Maintain reasonable history size (20 items = 10 conversation turns)
        if len(self.conversation_history) > 20:
            self.logger.debug(
                f"Trimming conversation history (was {len(self.conversation_history)} items)"
            )
            self.conversation_history = self.conversation_history[-20:]

    # =========================================================================
    # Utility Methods (Common to All Agents)
    # =========================================================================

    def clear_history(self) -> None:
        """Clear conversation history.

        Useful for:
        - Starting fresh conversation
        - Switching between different users/contexts
        - Resetting agent state after errors

        Note:
            This only clears RAM history. Database history (if enabled)
            is preserved for analytics and can be reloaded with load_history_from_db().

        Example:
            >>> agent.clear_history()
            >>> # Agent now has no memory of previous conversations
        """
        self.logger.debug(
            f"Clearing conversation history (had {len(self.conversation_history)} items)"
        )
        self.conversation_history = []

    def load_history_from_db(self, limit: int = 10) -> int:
        """Load conversation history from database.

        Loads recent messages from PostgreSQL and converts them to
        types.Content format for conversation_history.

        Args:
            limit: Maximum number of message pairs to load (default: 10 turns = 20 messages)

        Returns:
            Number of messages loaded

        Raises:
            RuntimeError: If memory_manager not enabled

        Example:
            >>> agent.load_history_from_db(limit=5)
            >>> # Loaded last 5 conversation turns from DB
        """
        if not self._memory_enabled or not self.memory_manager or not self.session_id:
            raise RuntimeError(
                "Memory manager not enabled - provide session_id and memory_manager to __init__()"
            )

        try:
            # Get recent messages from DB
            messages = self.memory_manager.get_recent_messages(
                self.session_id,
                limit=limit * 2,  # Each turn has user + model
            )

            # Convert to types.Content and reverse (DB returns DESC order)
            self.conversation_history = []
            for msg in reversed(messages):
                role = msg["role"]
                text = msg["message_text"]
                content = types.Content(role=role, parts=[types.Part(text=text)])
                self.conversation_history.append(content)

            self.logger.info(
                f"Loaded {len(messages)} messages from DB (session={self.session_id[:8]})"
            )
            return len(messages)

        except Exception as e:
            self.logger.exception(f"Failed to load history from DB: {e}")
            raise

    def save_memory_block(
        self,
        block_label: str,
        block_value: str,
        priority: int = 5,
        agent_scope: str = "shared",
    ) -> int:
        """Save semantic memory block (LLM-extracted fact).

        Memory blocks follow the Letta Memory Blocks pattern for structured
        context management. Use this to store important user preferences,
        product interests, or conversation context.

        Args:
            block_label: Memory category (e.g., 'user_preferences', 'product_interest')
            block_value: Memory content (e.g., "Usuario interesado en laptops gaming")
            priority: Priority score 0-10 (default: 5, threshold: 5)
            agent_scope: 'shared', 'sales', 'booking', or 'general' (default: 'shared')

        Returns:
            Memory block ID from database (-1 if skipped due to low priority)

        Raises:
            RuntimeError: If memory_manager not enabled

        Example:
            >>> agent.save_memory_block(
            ...     block_label="product_interest",
            ...     block_value="Usuario busca laptop gaming con RTX 4060",
            ...     priority=8,
            ...     agent_scope="sales"
            ... )
        """
        if not self._memory_enabled or not self.memory_manager or not self.session_id:
            raise RuntimeError(
                "Memory manager not enabled - provide session_id and memory_manager to __init__()"
            )

        try:
            block_id = self.memory_manager.save_memory_block(
                session_id=self.session_id,
                block_label=block_label,
                block_value=block_value,
                priority=priority,
                agent_scope=agent_scope,
            )

            if block_id > 0:
                self.logger.debug(
                    f"Memory block saved (id={block_id}, label={block_label}, priority={priority})"
                )
            else:
                self.logger.debug(f"Memory block skipped (priority {priority} < threshold)")

            return block_id

        except Exception as e:
            self.logger.exception(f"Failed to save memory block: {e}")
            raise

    def get_memory_blocks(self, agent_scope: str | None = None) -> list[dict[str, Any]]:
        """Get active memory blocks for current session.

        Retrieves non-expired memory blocks with priority >= threshold.

        Args:
            agent_scope: Filter by scope ('shared', 'sales', 'booking', 'general').
                If None, uses current agent's scope.

        Returns:
            List of memory block dictionaries

        Raises:
            RuntimeError: If memory_manager not enabled

        Example:
            >>> blocks = agent.get_memory_blocks()
            >>> for block in blocks:
            ...     print(f"{block['block_label']}: {block['block_value']}")
        """
        if not self._memory_enabled or not self.memory_manager or not self.session_id:
            raise RuntimeError(
                "Memory manager not enabled - provide session_id and memory_manager to __init__()"
            )

        scope = agent_scope or self.agent_name
        try:
            blocks = self.memory_manager.get_active_memory_blocks(
                self.session_id, agent_scope=scope
            )
            self.logger.debug(f"Retrieved {len(blocks)} memory blocks (scope={scope})")
            return blocks

        except Exception as e:
            self.logger.exception(f"Failed to get memory blocks: {e}")
            raise

    def get_user_context(self, customer_email: str | None = None) -> str:
        """Get formatted user memory context for prompt enrichment.

        Retrieves user-level memory blocks (cross-session) and formats them
        as structured text suitable for inclusion in system prompts. This enables
        agents to personalize responses based on user history across multiple sessions.

        Args:
            customer_email: User email to retrieve memory for.
                If None, attempts to get from current session.

        Returns:
            Formatted string with user memory context, or empty string if unavailable.

        Example:
            >>> context = agent.get_user_context("maria@example.com")
            >>> print(context)
            # Output:
            # "CROSS-SESSION USER MEMORY (maria@example.com):
            #  - product_interest: Usuario busca laptops gaming RTX 4060 (p=9)
            #  - user_preferences: Prefiere productos de alta gama (p=8)"
        """
        if not self._memory_enabled or not self.memory_manager:
            return ""

        try:
            # Get customer_email
            email = customer_email
            if not email and self.session_id:
                session_info = self.memory_manager.get_session_info(self.session_id)
                if session_info:
                    email = session_info.get("customer_email")

            if not email:
                self.logger.debug("No customer_email available for user context")
                return ""

            # Get user memory blocks
            user_blocks = self.memory_manager.get_user_memory_blocks(
                customer_email=email,
                agent_scope="shared",  # Load shared cross-session blocks
            )

            if not user_blocks:
                return ""

            # Format as structured text
            lines = [f"CROSS-SESSION USER MEMORY ({email}):"]
            for block in user_blocks[:10]:  # Limit to top 10 blocks
                label = block.get("block_label", "unknown")
                value = block.get("block_value", "")
                priority = block.get("priority", 0)
                lines.append(f" - {label}: {value} (p={priority})")

            formatted = "\n".join(lines)
            self.logger.debug(
                f"User context prepared: {len(user_blocks)} blocks, {len(formatted)} chars"
            )
            return formatted

        except Exception as e:
            self.logger.warning(f"Failed to get user context: {e}")
            return ""

    async def extract_semantic_memory(
        self,
        context: str | None = None,
        auto_save: bool = True,
    ) -> list[dict[str, Any]]:
        """Extract semantic memory blocks from conversation using LLM.

        Analyzes conversation history and automatically identifies important
        facts, preferences, and context using Gemini AI. Follows Memory Blocks
        pattern (Letta) for structured semantic memory.

        Args:
            context: Optional additional context for extraction
            auto_save: Automatically save extracted blocks to database (default: True)

        Returns:
            List of extracted memory block dictionaries

        Raises:
            RuntimeError: If memory_manager not enabled
            ImportError: If SemanticExtractor not available

        Example:
            >>> # After some conversation turns
            >>> memories = await agent.extract_semantic_memory()
            >>> print(f"Extracted {len(memories)} important facts")

        Note:
            This uses Gemini AI to analyze conversation and extract structured
            memory blocks. Only high-priority information (priority >= 5) is
            extracted and saved.
        """
        if not self._memory_enabled or not self.memory_manager or not self.session_id:
            raise RuntimeError(
                "Memory manager not enabled - provide session_id and memory_manager to __init__()"
            )

        try:
            # Import SemanticExtractor (lazy import to avoid circular dependency)
            import sys
            from pathlib import Path

            # Add mcp_server to path if not present
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            mcp_server_path = project_root / "mcp_server"
            if str(mcp_server_path) not in sys.path:
                sys.path.insert(0, str(mcp_server_path))

            from utils.semantic_extractor import SemanticExtractor

            # Initialize extractor
            extractor = SemanticExtractor(api_key=self.api_key)
            await extractor.initialize()

            # Get recent messages from DB
            messages = self.memory_manager.get_recent_messages(
                self.session_id,
                limit=10,  # Last 5 turns
            )

            if not messages:
                self.logger.debug("No messages to extract from")
                return []

            # Convert to format expected by extractor
            formatted_messages = [
                {"role": msg["role"], "text": msg["message_text"]} for msg in reversed(messages)
            ]

            # Extract semantic memory
            self.logger.info("Extracting semantic memory from conversation...")
            result = await extractor.extract_from_conversation(
                messages=formatted_messages, agent_name=self.agent_name, context=context
            )

            # Save to database if auto_save enabled
            extracted_blocks = []
            if auto_save and result.memories:
                for memory in result.memories:
                    try:
                        block_id = self.memory_manager.save_memory_block(
                            session_id=self.session_id,
                            block_label=memory.block_label,
                            block_value=memory.block_value,
                            priority=memory.priority,
                            agent_scope=memory.agent_scope,
                        )

                        if block_id > 0:
                            extracted_blocks.append(
                                {
                                    "id": block_id,
                                    "block_label": memory.block_label,
                                    "block_value": memory.block_value,
                                    "priority": memory.priority,
                                    "agent_scope": memory.agent_scope,
                                    "reasoning": memory.reasoning,
                                }
                            )
                            self.logger.debug(
                                f"Saved memory block: {memory.block_label} "
                                f"(id={block_id}, p={memory.priority})"
                            )
                    except Exception as e:
                        self.logger.warning(f"Failed to save memory block: {e}")

                self.logger.info(
                    f"✅ Extracted and saved {len(extracted_blocks)} semantic memory blocks "
                    f"({result.high_priority_count} high-priority)"
                )
            else:
                # Return without saving
                extracted_blocks = [
                    {
                        "block_label": m.block_label,
                        "block_value": m.block_value,
                        "priority": m.priority,
                        "agent_scope": m.agent_scope,
                        "reasoning": m.reasoning,
                    }
                    for m in result.memories
                ]
                self.logger.info(f"Extracted {len(extracted_blocks)} memory blocks (not saved)")

            return extracted_blocks

        except ImportError as e:
            self.logger.error(f"SemanticExtractor not available: {e}")
            raise ImportError("SemanticExtractor requires mcp_server in path") from e
        except Exception as e:
            self.logger.exception(f"Failed to extract semantic memory: {e}")
            raise

    def get_history_length(self) -> int:
        """Get current conversation history length.

        Returns:
            Number of items in conversation history (user + model messages).
            Each conversation turn contributes 2 items (1 user + 1 model).

        Example:
            >>> agent.get_history_length()
            10  # Represents 5 conversation turns
        """
        return len(self.conversation_history)

    def set_tools(self, mcp_tools: list[types.FunctionDeclaration]) -> None:
        """Set or update MCP tools for the agent.

        Updates the agent's available tools and rebuilds the generation
        configuration to include the new tools.

        Args:
            mcp_tools: List of MCP tools (FunctionDeclaration format).

        Example:
            >>> new_tools = [FunctionDeclaration(...)]
            >>> agent.set_tools(new_tools)
            >>> # Agent can now use new tools in responses
        """
        self.mcp_tools = mcp_tools
        self.logger.info(f"{self.agent_name} tools updated: {len(mcp_tools)} tools available")

        # Rebuild generation config to include new tools
        if self.client:
            self.generation_config = self._build_generation_config(**self._generation_params)
            self.logger.debug("Generation config rebuilt with updated tools")

    def get_metrics(self) -> dict[str, Any]:
        """Get agent performance metrics.

        Returns dictionary with metrics collected since agent initialization:
        - total_requests: Total number of generate_response() calls
        - successful_requests: Number of successful responses
        - failed_requests: Number of failed responses
        - success_rate: Success rate as percentage (0-100)
        - avg_response_time_ms: Average response time in milliseconds
        - errors: Dictionary of error types and their counts
        - avg_history_size: Average conversation history size

        Returns:
            Dictionary with agent metrics.

        Example:
            >>> metrics = agent.get_metrics()
            >>> print(f"Success rate: {metrics['success_rate']:.1f}%")
            >>> print(f"Avg latency: {metrics['avg_response_time_ms']:.0f}ms")
        """
        total = self._metrics["total_requests"]
        successful = self._metrics["successful_requests"]
        total_time = self._metrics["total_response_time_ms"]

        # Calculate derived metrics
        success_rate = (successful / total * 100) if total > 0 else 0.0
        avg_response_time = (total_time / total) if total > 0 else 0.0
        avg_history_size = (
            sum(self._metrics["history_sizes"]) / len(self._metrics["history_sizes"])
            if self._metrics["history_sizes"]
            else 0.0
        )

        return {
            "total_requests": total,
            "successful_requests": successful,
            "failed_requests": self._metrics["failed_requests"],
            "success_rate": success_rate,
            "avg_response_time_ms": avg_response_time,
            "errors": dict(self._metrics["errors"]),  # Copy to avoid mutation
            "avg_history_size": avg_history_size,
            "current_history_size": len(self.conversation_history),
        }

    def reset_metrics(self) -> None:
        """Reset all metrics to zero.

        Useful for:
        - Starting fresh metrics tracking
        - Clearing metrics between test runs
        - Resetting after debugging

        Example:
            >>> agent.reset_metrics()
            >>> # All metrics counters now at zero
        """
        self._metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_response_time_ms": 0.0,
            "errors": {},
            "history_sizes": [],
        }
        self.logger.debug(f"{self.agent_name} metrics reset")

    async def cleanup(self) -> None:
        """Cleanup resources and close client.

        Should be called when the agent is no longer needed. Performs cleanup:
        - Clears conversation history
        - Releases Gemini client
        - Resets generation config
        - Clears tool references
        - Resets metrics

        Example:
            >>> await agent.cleanup()
            >>> # Agent resources are now released
        """
        self.logger.info(f"Cleaning up {self.agent_name} resources")
        self.clear_history()
        self.reset_metrics()
        self.client = None
        self.generation_config = None
        self.mcp_tools = []
        self.logger.debug(f"{self.agent_name} cleanup completed")

    def __repr__(self) -> str:
        """String representation of agent for debugging.

        Returns:
            String showing agent configuration and state.

        Example:
            >>> repr(agent)
            'BookingAgent(model=gemini-2.5-flash, tools=5, history_len=10)'
        """
        return (
            f"{self.__class__.__name__}("
            f"model={self.model_name}, "
            f"tools={len(self.mcp_tools)}, "
            f"history_len={len(self.conversation_history)})"
        )
