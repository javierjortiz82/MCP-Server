"""Agent Orchestrator - Multi-Agent Routing Manager.

This module provides the AgentOrchestrator class that manages the multi-agent
system with feature flag support. It handles:
- Intent classification using AgentRouter
- Routing to specialized agents (Sales, Booking, General)
- Single-agent mode with SalesAgent only (ENABLE_AGENT_ROUTING=false)
- Gradual rollout capability
- AgentFactory integration for consistent agent creation

The orchestrator acts as the entry point for all user queries and directs them
to the appropriate specialized agent based on intent classification. All agents
are created using the AgentFactory pattern for consistency and maintainability.

Architecture:
    - Uses AgentFactory.create() for all agent instantiation
    - Supports dependency injection (MCP clients, tools, etc.)
    - Automatic initialization via factory (auto_initialize=True)
    - Graceful degradation when MCP unavailable

References:
    - https://ai.google.dev/gemini-api/docs/function-calling
    - https://googleapis.github.io/python-genai/
    - https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp

Author: Lab01-MCP Team
Created: 2025-10-11
Updated: 2025-10-12 (Integrated AgentFactory pattern)
Version: 2.0.0 (Breaking: Now uses AgentFactory)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Add agent directory to path for imports
agent_path = Path(__file__).parent.parent.parent / "agent" / "src"
if str(agent_path) not in sys.path:
    sys.path.insert(0, str(agent_path))

from multi_agent.agent_factory import AgentFactory  # noqa: E402
from multi_agent.agent_router import AgentRouter, Intent  # noqa: E402
from multi_agent.booking_agent import BookingAgent  # noqa: E402
from multi_agent.general_agent import GeneralAgent  # noqa: E402
from multi_agent.sales_agent import SalesAgent  # noqa: E402

from client_mcp.config.settings import settings  # noqa: E402
from client_mcp.core.mcp_connector import MCPConnector  # noqa: E402
from client_mcp.utils.logger import get_logger  # noqa: E402

# Observability imports (OPCIÓN 8)
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

# Import language context for setting language in MCP handlers
try:
    mcp_server_lang_path = Path(__file__).parent.parent.parent / "mcp_server"
    if str(mcp_server_lang_path) not in sys.path:
        sys.path.insert(0, str(mcp_server_lang_path))
    from utils.language_context import set_current_language  # noqa: E402

    LANGUAGE_CONTEXT_AVAILABLE = True
except ImportError:
    LANGUAGE_CONTEXT_AVAILABLE = False

    def set_current_language(lang: str) -> None:  # noqa: F811,ARG001
        """No-op when language context not available.

        Note: Parameter 'lang' is intentionally unused - this is a fallback stub
        when contextvars is not available. The real implementation is above.
        """
        pass


# Setup logger BEFORE using it
logger = get_logger("agent_orchestrator")

# Import MemoryManager for persistent memory support
try:
    # Add mcp_server to path for MemoryManager import
    mcp_server_path = Path(__file__).parent.parent.parent / "mcp_server"
    if str(mcp_server_path) not in sys.path:
        sys.path.insert(0, str(mcp_server_path))
    from utils.memory_manager import MemoryManager  # noqa: E402

    MEMORY_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ MemoryManager not available - agents will run without persistent memory")
    MemoryManager = None
    MEMORY_AVAILABLE = False

if TYPE_CHECKING:
    from google.genai import types


class AgentOrchestrator:
    """Multi-agent orchestrator with feature flag support.

    This class manages the routing between single-agent mode (SalesAgent only)
    and multi-agent mode (Sales, Booking, General). It provides flexibility
    for gradual rollout of the multi-agent architecture.

    The orchestrator:
    - Checks ENABLE_AGENT_ROUTING feature flag
    - Routes to SalesAgent only if flag is false (single-agent mode)
    - Routes to specialized agents if flag is true (multi-agent mode)
    - Handles agent initialization and cleanup
    - Provides unified interface for both modes

    Example:
        >>> orchestrator = AgentOrchestrator()
        >>> await orchestrator.initialize()
        >>> response = await orchestrator.process_query("Busco una laptop")
        >>> await orchestrator.cleanup()
    """

    def __init__(self) -> None:
        """Initialize Agent Orchestrator.

        Reads feature flags to determine operational mode:
        - ENABLE_AGENT_ROUTING: Multi-agent routing vs single-agent mode
        """
        # Initialize observability (OPCIÓN 8)
        if OBSERVABILITY_AVAILABLE:
            self.structured_logger = get_structured_logger("agent_orchestrator")
            self.metrics = get_metrics_collector()
        else:
            self.structured_logger = None
            self.metrics = None

        self.routing_enabled = settings.ENABLE_AGENT_ROUTING
        self.router_temperature = settings.ROUTER_TEMPERATURE

        # Single-agent mode (SalesAgent only)
        self.sales_bot: SalesAgent | None = None

        # Multi-agent mode
        self.router: AgentRouter | None = None
        self.sales_agent: SalesAgent | None = None  # Sales agent
        self.booking_agent: BookingAgent | None = None
        self.general_agent: GeneralAgent | None = None

        # MCP resources for booking agent
        self.booking_mcp_client: MCPConnector | None = None
        self.booking_mcp_tools: list[types.FunctionDeclaration] | None = None

        # MCP resources for sales agent
        self.sales_mcp_client: MCPConnector | None = None
        self.sales_mcp_tools: list[types.FunctionDeclaration] | None = None
        self.sales_mcp_tools_raw: list[dict] | None = None

        # Context tracking for sticky sessions
        self.last_intent: Intent | None = None
        self.last_bot_message: str | None = None

        # Memory management (persistent memory system)
        self.memory_manager: MemoryManager | None = None
        self.session_id: str | None = None
        self.customer_email: str | None = None

        # Language preference (es or en, default: es)
        self.language: str = "es"
        self._session_language_detected: bool = False  # Track if we've detected language for this session

        logger.info(
            f"AgentOrchestrator initialized - "
            f"Routing: {'ENABLED' if self.routing_enabled else 'DISABLED (single-agent mode)'}, "
            f"Observability: {'✅ Enabled' if OBSERVABILITY_AVAILABLE else '❌ Disabled'}"
        )

        if self.structured_logger:
            self.structured_logger.info(
                "Orchestrator initialization started",
                routing_enabled=self.routing_enabled,
                mode="multi_agent" if self.routing_enabled else "single_agent"
            )

    async def initialize(self, customer_email: str | None = None) -> None:
        """Initialize orchestrator and agents based on feature flag.

        Args:
            customer_email: Optional customer email for persistent memory sessions.
                          If provided, enables memory for all agents.

        Raises:
            RuntimeError: If initialization fails.
        """
        try:
            # Initialize memory system if available and customer_email provided
            if MEMORY_AVAILABLE and customer_email and MemoryManager:
                try:
                    logger.info("🧠 Initializing MemoryManager for persistent memory...")
                    self.memory_manager = MemoryManager()
                    self.customer_email = customer_email

                    # Get existing session or create new one
                    self.session_id = self.memory_manager.get_or_create_session(customer_email=customer_email)
                    logger.info(f"✅ Memory session active: {self.session_id}")

                    # Try to load session language from previous conversation first
                    # This is the PRIMARY source of language for returning sessions
                    retrieved_session_language = None
                    try:
                        retrieved_session_language = self.memory_manager.get_session_language(
                            self.session_id
                        )
                        if retrieved_session_language in ("es", "en"):
                            self.language = retrieved_session_language
                            logger.info(f"🌐 Session language loaded from DB: {self.language.upper()}")
                            self._session_language_detected = True
                    except Exception as session_lang_error:
                        logger.debug(f"Could not load session language from DB: {session_lang_error}")

                    # Fallback: Try user preferred language from memory blocks
                    # This is the SECONDARY source (cross-session preference)
                    if not retrieved_session_language:
                        try:
                            detected_language = self.memory_manager.get_user_preferred_language(
                                customer_email=customer_email, default_language="es"
                            )
                            if detected_language in ("es", "en"):
                                self.language = detected_language
                                logger.info(f"🌐 User language preference loaded: {self.language.upper()}")
                        except Exception as lang_error:
                            logger.debug(f"Could not detect user language: {lang_error}, using default 'es'")
                            self.language = "es"
                    else:
                        # Session language found, use it as default
                        self.language = retrieved_session_language

                except Exception as mem_error:
                    logger.warning(f"⚠️ Failed to initialize memory system: {mem_error}")
                    logger.warning("   Agents will run without persistent memory (graceful degradation)")
                    self.memory_manager = None
                    self.session_id = None
            elif not MEMORY_AVAILABLE:
                logger.info("ℹ️  MemoryManager not available - agents will run without persistent memory")
            elif not customer_email:
                logger.info("ℹ️  No customer_email provided - agents will run without persistent memory")

            if not self.routing_enabled:
                # Single-agent mode: Initialize only SalesAgent using factory
                logger.info("🔄 Initializing in SINGLE-AGENT mode (SalesAgent only)")
                self.sales_bot = await AgentFactory.create(
                    "sales",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info("✅ Single-agent mode initialized successfully")

            else:
                # Multi-agent mode: Initialize router and specialized agents
                logger.info("🔄 Initializing in MULTI-AGENT mode")

                # Initialize router
                logger.debug("Initializing AgentRouter...")
                self.router = AgentRouter()
                await self.router.initialize()

                # Initialize sales agent with MCP connection (centralized)
                logger.debug("Initializing Sales Agent with MCP...")
                await self._initialize_sales_agent_with_mcp()

                # Initialize booking agent with MCP connection
                logger.debug("Initializing Booking Agent with MCP...")
                await self._initialize_booking_agent_with_mcp()

                # Initialize general agent using factory (WITH MEMORY)
                logger.debug("Initializing General Agent...")
                self.general_agent = await AgentFactory.create(
                    "general",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )

                logger.info("✅ Multi-agent mode initialized successfully (Router + 3 specialized agents)")

        except Exception as e:
            logger.exception(f"Failed to initialize AgentOrchestrator: {e}")
            raise RuntimeError(f"Orchestrator initialization failed: {e}") from e

    async def process_query(
        self,
        query: str,
        *,
        customer_email: str | None = None,
        include_history: bool = True,
    ) -> str:
        """Process user query through appropriate agent(s).

        This is the main entry point for all user queries. It:
        1. Routes to SalesAgent if routing disabled (single-agent mode)
        2. Classifies intent and routes to specialized agent if enabled

        Args:
            query: User query text.
            customer_email: Optional customer email for personalization.
            include_history: Whether to include conversation history.

        Returns:
            Response text from the appropriate agent.

        Raises:
            RuntimeError: If orchestrator not initialized or processing fails.

        Example:
            >>> response = await orchestrator.process_query(
            ...     "Quiero reservar una cita",
            ...     customer_email="maria@example.com"
            ... )
        """
        if not self.routing_enabled:
            # Single-agent mode: Route to SalesAgent only
            return await self._process_legacy(query)

        else:
            # Multi-agent mode: Classify and route
            return await self._process_multi_agent(
                query,
                customer_email=customer_email,
                include_history=include_history,
            )

    async def _process_legacy(self, query: str) -> str:
        """Process query using single-agent mode (SalesAgent only).

        Args:
            query: User query text.

        Returns:
            Response from SalesAgent.

        Raises:
            RuntimeError: If SalesAgent not initialized.

        Note:
            Language detection is now handled automatically by Gemini via system instructions.
            The language parameter passed during initialization is used for template selection,
            but Gemini will automatically respond in the language of the user's query.
        """
        if not self.sales_bot:
            logger.error("SalesAgent not initialized in single-agent mode")
            raise RuntimeError("SalesAgent not initialized")

        logger.debug(f"Processing query in SINGLE-AGENT mode: '{query[:50]}...'")
        logger.debug(f"🌐 Agent configured for language: {self.language.upper()} (Gemini handles auto-detection)")

        # Set language context for MCP handlers (for tool responses)
        set_current_language(self.language)

        # Call SalesAgent's send_message method
        # Gemini will automatically respond in the language of the query
        response = await self.sales_bot.send_message(query)
        return response

    async def _process_multi_agent(
        self,
        query: str,
        *,
        customer_email: str | None = None,
        include_history: bool = True,
    ) -> str:
        """Process query using multi-agent routing.

        Args:
            query: User query text.
            customer_email: Optional customer email.
            include_history: Whether to include history.

        Returns:
            Response from specialized agent.

        Raises:
            RuntimeError: If agents not initialized.

        Note:
            Language detection is now handled automatically by Gemini via system instructions.
            The language parameter is used for template selection and MCP context, but Gemini
            will automatically respond in the language of the user's query.
        """
        if not self.router:
            logger.error("AgentRouter not initialized in multi-agent mode")
            raise RuntimeError("AgentRouter not initialized")

        logger.debug(f"Processing query in MULTI-AGENT mode: '{query[:50]}...'")
        logger.debug(f"🌐 Session language: {self.language.upper()}")

        # Step 1: Classify intent with context
        try:
            # PHASE 1: Detect language on first query and cache it
            if not self._session_language_detected:
                from gemini_agent.utils.language_detector import detect_language_async

                # Try to retrieve language from existing session first (persistence)
                retrieved_language = None
                if self.memory_manager and self.session_id:
                    try:
                        retrieved_language = self.memory_manager.get_session_language(self.session_id)
                        if retrieved_language:
                            self.language = retrieved_language
                            logger.info(f"🌐 Language retrieved from session: {self.language.upper()}")
                    except Exception as retrieve_error:
                        logger.debug(f"Could not retrieve language from session: {retrieve_error}")

                # If not found in session, detect from first query
                if not retrieved_language:
                    self.language = await detect_language_async(query)
                    logger.info(f"🌐 Language detected on first query: {self.language.upper()}")

                    # PHASE 2: Save language to database for persistence
                    if self.memory_manager and self.session_id:
                        try:
                            self.memory_manager.save_session_language(self.session_id, self.language)
                            logger.debug(f"💾 Language '{self.language}' saved to session {self.session_id[:8]}")
                        except Exception as lang_save_error:
                            logger.warning(f"⚠️ Failed to save language to DB: {lang_save_error}")

                self._session_language_detected = True

            # Build context for router
            context = {}
            if self.last_intent:
                context["last_intent"] = self.last_intent.value
            if self.last_bot_message:
                context["last_bot_message"] = self.last_bot_message

            # Pass cached session language to router (prevents re-detection of ambiguous queries)
            intent, detected_language = await self.router.classify_intent(
                query,
                context=context if context else None,
                session_language=self.language  # ← Use cached language, don't re-detect
            )
            logger.info(f"Intent classified: {intent.value}")
            logger.info(f"🌐 Language (from session cache): {detected_language}")

            # CRITICAL FIX: Update orchestrator language if router detected a language switch
            # This ensures subsequent queries use the correct language
            if detected_language != self.language:
                logger.warning(
                    f"⚠️ Router detected language switch: {self.language} → {detected_language}. "
                    f"Updating session language for next requests."
                )
                self.language = detected_language
                # Persist language change to DB for next session
                if self.memory_manager and self.session_id:
                    try:
                        self.memory_manager.save_session_language(self.session_id, detected_language)
                        logger.debug(f"💾 Language updated and persisted to DB: {detected_language}")
                    except Exception as lang_save_error:
                        logger.warning(f"⚠️ Failed to update language in DB: {lang_save_error}")

            # Save current intent for next iteration
            self.last_intent = intent

        except Exception as e:
            logger.exception(f"Intent classification failed: {e}")

            # CRITICAL FIX: Better fallback strategy for classification errors
            # Try sticky session (previous intent) for short queries (< 5 chars)
            is_very_short = len(query.strip()) < 5
            if is_very_short and self.last_intent:
                logger.warning(
                    f"⚠️ Classification failed on short query. "
                    f"Maintaining previous intent: {self.last_intent.value} (sticky session fallback)"
                )
                intent = self.last_intent
                detected_language = self.language  # Use current session language
            else:
                # For longer queries, fallback to general agent
                logger.warning("⚠️ Falling back to general agent due to classification error")
                intent = Intent.GENERAL
                # Use session language as fallback (avoid nested language detection in error context)
                detected_language = self.language

        # Step 2: Route to specialized agent and save response
        try:
            response = None
            if intent == Intent.SALES:
                response = await self._route_to_sales(query, include_history=include_history, language=detected_language)

            elif intent == Intent.BOOKING:
                response = await self._route_to_booking(
                    query,
                    customer_email=customer_email,
                    include_history=include_history,
                    language=detected_language,
                )

            elif intent == Intent.GENERAL:
                response = await self._route_to_general(query, include_history=include_history, language=detected_language)

            else:
                # Unknown intent - fallback to general
                logger.warning(f"Unknown intent: {intent}, falling back to general")
                response = await self._route_to_general(query, include_history=include_history, language=detected_language)

            # Save last bot message for context in next classification
            self.last_bot_message = response[:200] if response else None  # First 200 chars

            return response

        except Exception as e:
            logger.exception(f"Agent routing failed: {e}")
            raise

    async def _fetch_tool_category(
        self,
        mcp_client: MCPConnector,
        category: str,
    ) -> set[str] | None:
        """Fetch tool names for a category from MCP resource.

        This method queries the MCP server's tool-categories:// resources to
        dynamically discover which tools belong to each category. This eliminates
        the need for hardcoded tool lists in client code.

        Args:
            mcp_client: Connected MCP client instance.
            category: Category name (e.g., "products", "bookings").

        Returns:
            Set of tool names for the category, or None if fetch fails.

        Example:
            >>> tools = await self._fetch_tool_category(mcp_client, "products")
            >>> # tools = {"fetch_by_sku", "search_products", ...}
        """
        try:
            resource_uri = f"tool-categories://{category}"
            logger.debug(f"📥 Fetching tool category from resource: {resource_uri}")

            # Read resource from MCP server
            resource_data = await mcp_client.read_resource(resource_uri)

            # Extract text from TextResourceContents object
            resource_text = resource_data.text if hasattr(resource_data, "text") else str(resource_data)

            # Parse JSON response
            category_info = json.loads(resource_text)

            if "error" in category_info:
                logger.error(f"❌ Error in category resource: {category_info['error']}")
                return None

            tool_names = category_info.get("tools", [])
            tool_count = category_info.get("count", len(tool_names))

            logger.info(f"✅ Fetched {tool_count} tool names for category '{category}' from MCP resource")
            logger.debug(f"   Tools: {tool_names}")

            return set(tool_names)

        except Exception as e:
            logger.exception(f"Error fetching tool category '{category}': {e}")
            logger.warning("⚠️ Falling back to all tools (category filter failed)")
            return None

    async def _connect_to_mcp_server(
        self,
        agent_name: str,
        agent_class: type,
        tool_category: str | None = None,
    ) -> tuple[MCPConnector | None, list[types.FunctionDeclaration] | None, list[dict] | None]:
        """Connect to MCP server and autodiscover tools (centralized method).

        This centralized method eliminates code duplication between different agents.
        It handles the complete MCP connection lifecycle:
        - Health checks
        - Connection establishment
        - Tool autodiscovery
        - Tool filtering by category (optional)
        - Tool conversion to GenAI format

        Args:
            agent_name: Name of agent for logging (e.g., "BookingAgent", "SalesAgent").
            agent_class: Agent class for tool conversion (e.g., BookingAgent, SalesAgent).
            tool_category: Optional category to filter tools by (e.g., "products", "bookings").
                          If None, returns all tools (backward compatible).

        Returns:
            Tuple of (mcp_client, mcp_tools, mcp_tools_raw):
            - mcp_client: Connected MCPConnector instance or None
            - mcp_tools: Tools in GenAI FunctionDeclaration format or None
            - mcp_tools_raw: Raw tool definitions from MCP or None

        Example:
            >>> mcp_client, tools, tools_raw = await self._connect_to_mcp_server(
            ...     agent_name="BookingAgent",
            ...     agent_class=BookingAgent,
            ...     tool_category="bookings"
            ... )
        """
        try:
            # Step 1: Build MCP URL
            mcp_url = f"http://{settings.MCP_HOST}:{settings.MCP_PORT}/mcp"
            logger.info(f"🔗 Connecting to MCP server for {agent_name}: {mcp_url}")

            # Step 2: Health check (verify server is available)
            logger.debug(f"🏥 Checking MCP server health for {agent_name}...")
            health = await MCPConnector.check_server_health(mcp_url)

            if health["status"] == "unreachable":
                logger.warning(
                    f"⚠️ MCP server unreachable at {mcp_url}: {health.get('error')}. "
                    f"{agent_name} will run without tools (graceful degradation)."
                )
                return None, None, None

            elif health["status"] == "unhealthy":
                logger.error(f"❌ MCP server is UNHEALTHY for {agent_name}")
                if "checks" in health and "database" in health["checks"]:
                    db_check = health["checks"]["database"]
                    logger.error(f"   Database status: {db_check.get('status')}")

                logger.warning(f"⚠️ MCP server unhealthy. {agent_name} will run without tools (graceful degradation).")
                return None, None, None

            elif health["status"] == "degraded":
                logger.warning(f"⚠️ MCP server DEGRADED for {agent_name} (continuing with limited capabilities)")

            else:
                # Healthy
                logger.info(f"✅ MCP server healthy for {agent_name}")
                if "checks" in health and "database" in health["checks"]:
                    db_check = health["checks"]["database"]
                    product_count = db_check.get("product_count", 0)
                    booking_count = db_check.get("booking_count", 0)
                    logger.info(f"   📦 Products: {product_count}, 📅 Bookings: {booking_count}")

            # Step 3: Connect to MCP server
            logger.debug(f"🔌 Establishing MCP connection for {agent_name}...")
            mcp_client = MCPConnector(mcp_url)
            await mcp_client.__aenter__()

            # Step 4: Autodiscover tools
            logger.debug(f"🔍 Discovering tools for {agent_name}...")
            all_tools_raw = await mcp_client.list_tools()
            logger.info(f"📋 Discovered {len(all_tools_raw)} total MCP tools")

            # Step 5: Filter tools by category (if specified) - DYNAMIC DISCOVERY
            if tool_category:
                logger.debug(f"🔍 Filtering tools by category: '{tool_category}'")

                # Fetch tool names dynamically from MCP resource
                allowed_tools = await self._fetch_tool_category(mcp_client, tool_category)

                if allowed_tools:
                    # Filter tools using dynamically fetched category
                    mcp_tools_raw = [tool for tool in all_tools_raw if tool.get("name") in allowed_tools]
                    logger.info(
                        f"✅ Filtered to {len(mcp_tools_raw)} tools for category '{tool_category}' "
                        f"(dynamically discovered from MCP resource)"
                    )
                else:
                    # Fallback: Return all tools if category fetch failed
                    logger.warning(f"⚠️ Failed to fetch category '{tool_category}' from MCP, returning all tools")
                    mcp_tools_raw = all_tools_raw
            else:
                # No filtering - return all tools (backward compatible)
                mcp_tools_raw = all_tools_raw
                logger.debug("No category filter - returning all tools")

            # Log available tools (for debugging)
            if mcp_tools_raw:
                logger.debug(f"Available tools for {agent_name}:")
                for tool in mcp_tools_raw:
                    tool_name = tool.get("name", "unknown")
                    tool_desc = tool.get("description", "")
                    desc_first_line = tool_desc.split("\n")[0] if tool_desc else "No description"
                    logger.debug(f"  - {tool_name}: {desc_first_line[:80]}...")

            # Step 6: Convert tools to GenAI format
            logger.debug(f"🔄 Converting tools to Gemini format for {agent_name}...")
            # Create temporary agent instance for conversion utility
            temp_agent = agent_class()
            mcp_tools = temp_agent.convert_tools_to_genai(mcp_tools_raw)
            logger.info(f"✅ Converted {len(mcp_tools)} tools to GenAI format for {agent_name}")

            return mcp_client, mcp_tools, mcp_tools_raw

        except Exception as e:
            logger.exception(f"Error connecting to MCP server for {agent_name}: {e}")
            logger.warning(f"⚠️ {agent_name} will run without MCP tools (graceful degradation)")
            return None, None, None

    async def _initialize_booking_agent_with_mcp(self) -> None:
        """Initialize BookingAgent with MCP connection and tools.

        Uses centralized _connect_to_mcp_server() method to eliminate code duplication.
        Handles graceful degradation if MCP connection fails.

        Raises:
            RuntimeError: If critical initialization fails.
        """
        try:
            # Connect to MCP server and autodiscover tools (centralized method)
            # Filter to only booking-related tools using metadata category
            (
                self.booking_mcp_client,
                self.booking_mcp_tools,
                mcp_tools_raw,
            ) = await self._connect_to_mcp_server(
                agent_name="BookingAgent",
                agent_class=BookingAgent,
                tool_category="bookings",  # Only get booking tools
            )

            # Initialize agent with or without MCP tools (using factory)
            if self.booking_mcp_client and self.booking_mcp_tools:
                # Success: Initialize with MCP tools via factory
                logger.debug("🚀 Initializing BookingAgent with MCP tools via factory...")
                self.booking_agent = await AgentFactory.create(
                    "booking",
                    mcp_tools=self.booking_mcp_tools,
                    mcp_client=self.booking_mcp_client,
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info(f"✅ BookingAgent initialized with {len(self.booking_mcp_tools)} MCP tools")
            else:
                # Graceful degradation: Initialize without tools via factory
                logger.warning("⚠️ Initializing BookingAgent without MCP tools via factory")
                self.booking_agent = await AgentFactory.create(
                    "booking",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info("✅ BookingAgent initialized in standalone mode (no tools)")

        except Exception as e:
            logger.exception(f"Error initializing BookingAgent: {e}")

            # Last resort: Try to initialize without tools via factory
            try:
                logger.warning("⚠️ Attempting fallback initialization without MCP via factory...")
                self.booking_agent = await AgentFactory.create(
                    "booking",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info("✅ BookingAgent initialized in fallback mode (no tools)")

            except Exception as fallback_error:
                logger.exception(f"Failed to initialize BookingAgent even in fallback mode: {fallback_error}")
                raise RuntimeError(
                    f"BookingAgent initialization failed completely: {fallback_error}"
                ) from fallback_error

    async def _initialize_sales_agent_with_mcp(self) -> None:
        """Initialize Sales Agent (SalesAgent) with MCP connection and tools.

        Uses centralized _connect_to_mcp_server() method to eliminate code duplication.
        Handles graceful degradation if MCP connection fails.

        Raises:
            RuntimeError: If critical initialization fails.
        """
        try:
            # Connect to MCP server and autodiscover tools (centralized method)
            # Filter to only product-related tools using metadata category
            (
                self.sales_mcp_client,
                self.sales_mcp_tools,
                self.sales_mcp_tools_raw,
            ) = await self._connect_to_mcp_server(
                agent_name="SalesAgent",
                agent_class=SalesAgent,
                tool_category="products",  # Only get product tools
            )

            # Initialize agent with or without MCP tools (using factory)
            if self.sales_mcp_client and self.sales_mcp_tools:
                # Success: Initialize with MCP tools via factory
                logger.debug("🚀 Initializing SalesAgent with MCP tools via factory...")
                self.sales_agent = await AgentFactory.create(
                    "sales",
                    mcp_client=self.sales_mcp_client,
                    mcp_tools=self.sales_mcp_tools,
                    mcp_tools_raw=self.sales_mcp_tools_raw,
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info(f"✅ SalesAgent initialized with {len(self.sales_mcp_tools)} MCP tools")
            else:
                # Graceful degradation: Initialize without tools via factory
                logger.warning("⚠️ Initializing SalesAgent without MCP tools via factory")
                self.sales_agent = await AgentFactory.create(
                    "sales",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info("✅ SalesAgent initialized in standalone mode (no tools)")

        except Exception as e:
            logger.exception(f"Error initializing SalesAgent: {e}")

            # Last resort: Try to initialize without tools via factory
            try:
                logger.warning("⚠️ Attempting fallback initialization without MCP via factory...")
                self.sales_agent = await AgentFactory.create(
                    "sales",
                    session_id=self.session_id,
                    memory_manager=self.memory_manager,
                    language=self.language,
                )
                logger.info("✅ SalesAgent initialized in fallback mode (no tools)")

            except Exception as fallback_error:
                logger.exception(f"Failed to initialize SalesAgent even in fallback mode: {fallback_error}")
                raise RuntimeError(f"SalesAgent initialization failed completely: {fallback_error}") from fallback_error

    async def _route_to_sales(
        self,
        query: str,
        *,
        include_history: bool = True,
        language: str = "en",
    ) -> str:
        """Route query to sales agent (SalesAgent).

        Args:
            query: User query.
            include_history: Include conversation history.
            language: Detected user language ("en" or "es").

        Returns:
            Response from sales agent.
        """
        if not self.sales_agent:
            logger.error("SalesAgent not initialized")
            raise RuntimeError("SalesAgent not initialized")

        logger.debug("Routing to SALES agent (SalesAgent)")

        # Set language context for MCP handlers (sales tool calls)
        set_current_language(language)
        logger.debug(f"🌐 Language context set to: {language}")

        # Call SalesAgent's send_message method with language and intent parameters
        response = await self.sales_agent.send_message(
            query,
            language=language,
            intent="sales",  # Pass classified intent for future DB storage support
        )
        return response

    async def _route_to_booking(
        self,
        query: str,
        *,
        customer_email: str | None = None,
        include_history: bool = True,
        language: str = "en",
    ) -> str:
        """Route query to booking agent.

        Args:
            query: User query.
            customer_email: Customer email (uses session email if not provided).
            include_history: Include conversation history.
            language: Detected user language ("en" or "es").

        Returns:
            Response from booking agent.
        """
        if not self.booking_agent:
            logger.error("Booking agent not initialized")
            raise RuntimeError("Booking agent not initialized")

        logger.debug("Routing to BOOKING agent")

        # Set language context for MCP handlers (booking tool calls)
        set_current_language(language)
        logger.debug(f"🌐 Language context set to: {language}")

        # Use stored session email if not provided explicitly
        effective_email = customer_email or self.customer_email

        if effective_email:
            logger.debug(f"Using customer_email: {effective_email}")
        else:
            logger.debug("No customer_email available (session or parameter)")

        response = await self.booking_agent.generate_response(
            query,
            customer_email=effective_email,
            include_history=include_history,
            intent="booking",  # Pass classified intent for DB storage
            language=language,  # Pass language to agent for dynamic template selection
        )

        return response

    async def _route_to_general(
        self,
        query: str,
        *,
        include_history: bool = True,
        language: str = "en",
    ) -> str:
        """Route query to general agent.

        Args:
            query: User query.
            include_history: Include conversation history.
            language: Detected user language ("en" or "es").

        Returns:
            Response from general agent.
        """
        if not self.general_agent:
            logger.error("General agent not initialized")
            raise RuntimeError("General agent not initialized")

        logger.debug("Routing to GENERAL agent")

        # Set language context for MCP handlers (general tool calls)
        set_current_language(language)
        logger.debug(f"🌐 Language context set to: {language}")

        response = await self.general_agent.generate_response(
            query,
            include_history=include_history,
            intent="general",  # Pass classified intent for DB storage
            language=language,  # Pass language to agent for dynamic template selection
        )

        return response

    async def run_interactive(self) -> None:
        """Run interactive chat mode.

        Provides command-line interface for testing the orchestrator.
        """
        print("\n" + "=" * 70)
        print("🤖 Lab01-MCP Multi-Agent System")
        print("=" * 70)

        if self.routing_enabled:
            print("Mode: MULTI-AGENT (Router + Specialized Agents)")
            print("Agents: Sales (SalesAgent) | Booking | General")
        else:
            print("Mode: SINGLE-AGENT (SalesAgent only)")

        print("\nCommands:")
        print("  /help    - Show this help message")
        print("  /clear   - Clear conversation history")
        print("  /stats   - Show routing statistics (multi-agent mode)")
        print("  /quit    - Exit the program")
        print("=" * 70)

        # Track intents for statistics
        intent_history: list[Intent] = []

        while True:
            try:
                # Get user input
                user_query = input("\n👤 You: ").strip()

                if not user_query:
                    continue

                # Handle commands
                if user_query.startswith("/"):
                    if user_query == "/quit":
                        print("\n👋 ¡Hasta luego!")
                        break

                    elif user_query == "/help":
                        print("\n📖 Available commands:")
                        print("  /help  - Show help")
                        print("  /clear - Clear history")
                        print("  /stats - Show statistics")
                        print("  /quit  - Exit")
                        continue

                    elif user_query == "/clear":
                        if self.routing_enabled:
                            if self.sales_agent:
                                self.sales_agent.conversation_history = []
                            if self.booking_agent:
                                self.booking_agent.clear_history()
                            if self.general_agent:
                                self.general_agent.clear_history()
                        else:
                            if self.sales_bot:
                                self.sales_bot.conversation_history = []

                        intent_history = []
                        print("✅ Conversation history cleared")
                        continue

                    elif user_query == "/stats":
                        if not self.routing_enabled:
                            print("ℹ️  Statistics only available in multi-agent mode")
                            continue

                        if not intent_history:
                            print("ℹ️  No queries processed yet")
                            continue

                        if self.router:
                            stats = self.router.get_intent_statistics(intent_history)
                            print("\n📊 Routing Statistics:")
                            print(f"  Total queries: {stats['total']}")
                            print(f"  Sales: {stats['sales_count']} ({stats['sales_percentage']:.1f}%)")
                            print(f"  Booking: {stats['booking_count']} ({stats['booking_percentage']:.1f}%)")
                            print(f"  General: {stats['general_count']} ({stats['general_percentage']:.1f}%)")
                        continue

                    else:
                        print(f"❌ Unknown command: {user_query}")
                        print("   Type /help for available commands")
                        continue

                # Process query
                print("🤔 Processing...")

                # Process query (this will handle intent classification with context)
                response = await self.process_query(user_query)

                # Track intent for statistics (after process_query has classified it)
                if self.routing_enabled and self.last_intent:
                    intent_history.append(self.last_intent)
                    print(f"   Intent: {self.last_intent.value}")

                print(f"\n🤖 Bot: {response}")

            except KeyboardInterrupt:
                print("\n\n👋 ¡Hasta luego!")
                break

            except Exception as e:
                logger.exception(f"Error processing query: {e}")
                print(f"\n❌ Error: {e}")

    async def cleanup(self) -> None:
        """Cleanup all agents and resources.

        Should be called when shutting down the orchestrator.
        """
        logger.info("Cleaning up AgentOrchestrator resources")

        try:
            if not self.routing_enabled:
                # Cleanup single-agent mode
                if self.sales_bot:
                    await self.sales_bot.cleanup()
                    self.sales_bot = None

            else:
                # Cleanup multi-agent mode
                if self.router:
                    await self.router.cleanup()
                    self.router = None

                if self.sales_agent:
                    await self.sales_agent.cleanup()
                    self.sales_agent = None

                if self.booking_agent:
                    await self.booking_agent.cleanup()
                    self.booking_agent = None

                # Cleanup sales MCP connection
                if self.sales_mcp_client:
                    try:
                        await self.sales_mcp_client.__aexit__(None, None, None)
                        logger.info("🔌 Disconnected from sales MCP server")
                    except Exception as mcp_error:
                        logger.warning(f"Error disconnecting sales MCP client: {mcp_error}")
                    finally:
                        self.sales_mcp_client = None
                        self.sales_mcp_tools = None
                        self.sales_mcp_tools_raw = None

                # Cleanup booking MCP connection
                if self.booking_mcp_client:
                    try:
                        await self.booking_mcp_client.__aexit__(None, None, None)
                        logger.info("🔌 Disconnected from booking MCP server")
                    except Exception as mcp_error:
                        logger.warning(f"Error disconnecting booking MCP client: {mcp_error}")
                    finally:
                        self.booking_mcp_client = None
                        self.booking_mcp_tools = None

                if self.general_agent:
                    await self.general_agent.cleanup()
                    self.general_agent = None

            logger.info("✅ AgentOrchestrator cleanup completed")

        except Exception as e:
            logger.exception(f"Error during cleanup: {e}")

    def __repr__(self) -> str:
        """String representation of AgentOrchestrator."""
        mode = "MULTI-AGENT" if self.routing_enabled else "LEGACY"
        return f"AgentOrchestrator(mode={mode}, temperature={self.router_temperature})"
