"""Agent Factory - Simplified Agent Creation Pattern.

This module provides a factory pattern for creating and initializing agents.
Instead of manually instantiating and initializing agents, use the factory
for a streamlined experience.

Example:
    >>> # Before (manual)
    >>> from multi_agent import BookingAgent
    >>> agent = BookingAgent(mcp_tools=tools)
    >>> await agent.initialize()

    >>> # After (factory)
    >>> from multi_agent import AgentFactory
    >>> agent = await AgentFactory.create("booking", mcp_tools=tools)

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 1.0.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gemini_agent.base_agent import BaseAgent
from gemini_agent.utils.logger import setup_logging

# Observability imports (OPCIÓN 7)
try:
    from email_service.observability.metrics import get_metrics_collector
    from email_service.observability.structured_logger import get_structured_logger
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False

if TYPE_CHECKING:
    from google.genai import types

logger = setup_logging("agent_factory")

# Initialize observability for factory
if OBSERVABILITY_AVAILABLE:
    _structured_logger = get_structured_logger("agent_factory")
    _metrics = get_metrics_collector()
else:
    _structured_logger = None
    _metrics = None


class AgentFactory:
    """Factory for creating and initializing agents.

    This class provides a centralized way to create agents with automatic
    initialization, validation, and best practices enforcement.

    Supported agent types:
    - "booking": BookingAgent for reservations
    - "general": GeneralAgent for FAQ and info
    - "sales": SalesAgent for product sales and recommendations

    Example:
        >>> # Create booking agent
        >>> agent = await AgentFactory.create("booking", mcp_tools=tools)

        >>> # Create general agent (no tools needed)
        >>> agent = await AgentFactory.create("general")

        >>> # Create with custom parameters
        >>> agent = await AgentFactory.create(
        ...     "sales",
        ...     mcp_tools=tools,
        ...     api_key="custom-key",
        ...     temperature=0.7
        ... )
    """

    # Registry of available agent types
    _AGENT_REGISTRY: dict[str, type[BaseAgent]] = {}

    # Flag to track if registry is initialized
    _registry_initialized: bool = False

    @classmethod
    def _initialize_registry(cls) -> None:
        """Initialize the agent registry (lazy loading).

        This method imports agent classes only when needed to avoid
        circular imports and improve startup time.
        """
        if cls._registry_initialized:
            return

        # Import agents (lazy to avoid circular imports)
        from multi_agent.booking_agent import BookingAgent
        from multi_agent.general_agent import GeneralAgent
        from multi_agent.sales_agent import SalesAgent

        # Register agents
        cls._AGENT_REGISTRY = {
            "booking": BookingAgent,
            "general": GeneralAgent,
            "sales": SalesAgent,
        }

        cls._registry_initialized = True
        logger.debug(f"Agent registry initialized with {len(cls._AGENT_REGISTRY)} agent types")

    @classmethod
    def get_available_agents(cls) -> list[str]:
        """Get list of available agent types.

        Returns:
            List of agent type names that can be created.

        Example:
            >>> AgentFactory.get_available_agents()
            ['booking', 'general', 'sales']
        """
        cls._initialize_registry()
        return list(cls._AGENT_REGISTRY.keys())

    @classmethod
    async def create(
        cls,
        agent_type: str,
        *,
        mcp_tools: list[types.FunctionDeclaration] | None = None,
        mcp_client: Any | None = None,
        mcp_tools_raw: list[dict] | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        auto_initialize: bool = True,
        **kwargs: Any,
    ) -> BaseAgent:
        """Create and initialize an agent with advanced dependency injection.

        This is the main factory method for creating agents. It handles:
        - Agent instantiation
        - Parameter validation
        - Automatic initialization
        - Dependency injection (MCP clients, tools, etc.)
        - Error handling

        Args:
            agent_type: Type of agent to create ("booking", "general", "sales").
            mcp_tools: Optional list of MCP tools in GenAI format.
            mcp_client: Optional MCP client instance (MCPConnector).
            mcp_tools_raw: Optional list of raw MCP tool definitions (for SalesAgent).
            api_key: Optional Google API key (uses settings if not provided).
            model_name: Optional model name (uses settings if not provided).
            auto_initialize: Whether to automatically initialize the agent (default: True).
            **kwargs: Additional parameters passed to agent constructor.

        Returns:
            Initialized agent instance ready to use.

        Raises:
            ValueError: If agent_type is not recognized.
            RuntimeError: If agent initialization fails.

        Example:
            >>> # Create booking agent with MCP tools
            >>> agent = await AgentFactory.create(
            ...     "booking",
            ...     mcp_tools=tools,
            ...     mcp_client=client
            ... )
            >>> response = await agent.generate_response("Quiero reservar")

            >>> # Create general agent (no tools needed)
            >>> agent = await AgentFactory.create("general")

            >>> # Create sales agent with full MCP integration
            >>> agent = await AgentFactory.create(
            ...     "sales",
            ...     mcp_client=client,
            ...     mcp_tools=tools,
            ...     mcp_tools_raw=raw_tools,
            ...     temperature=0.7
            ... )
        """
        # Initialize registry if needed
        cls._initialize_registry()

        # Validate agent type
        if agent_type not in cls._AGENT_REGISTRY:
            available = ", ".join(cls._AGENT_REGISTRY.keys())
            raise ValueError(f"Unknown agent type: '{agent_type}'. Available types: {available}")

        # Get agent class
        agent_class = cls._AGENT_REGISTRY[agent_type]

        logger.info(f"Creating {agent_type} agent...")

        # Track creation attempt (OPCIÓN 7)
        if _metrics:
            _metrics.increment_counter(f"factory_create_{agent_type}_attempted", 1)
        if _structured_logger:
            _structured_logger.info("Agent creation started", agent_type=agent_type)

        try:
            # Prepare constructor arguments
            init_args = {}

            # Add MCP tools if provided
            if mcp_tools is not None:
                init_args["mcp_tools"] = mcp_tools

            # Add MCP client if provided (for agents with function calling)
            if mcp_client is not None:
                init_args["mcp_client"] = mcp_client

            # Add raw MCP tools if provided (SalesAgent needs this)
            if mcp_tools_raw is not None:
                init_args["mcp_tools_raw"] = mcp_tools_raw

            # Add API key if provided
            if api_key is not None:
                init_args["api_key"] = api_key

            # Add model name if provided
            if model_name is not None:
                init_args["model_name"] = model_name

            # Add any additional kwargs (temperature, top_k, etc.)
            init_args.update(kwargs)

            # Instantiate agent
            agent = agent_class(**init_args)

            logger.debug(f"Agent instantiated: {agent_class.__name__}")

            # Auto-initialize if requested
            if auto_initialize:
                await agent.initialize()
                logger.info(f"✅ {agent_type} agent created and initialized successfully")

                if _metrics:
                    _metrics.increment_counter(f"factory_create_{agent_type}_successful", 1)
                if _structured_logger:
                    _structured_logger.info("Agent creation successful", agent_type=agent_type)
            else:
                logger.info(f"✅ {agent_type} agent created (not initialized)")

                if _metrics:
                    _metrics.increment_counter(f"factory_create_{agent_type}_not_initialized", 1)

            return agent

        except Exception as e:
            logger.exception(f"Failed to create {agent_type} agent: {e}")

            if _metrics:
                _metrics.increment_counter(f"factory_create_{agent_type}_failed", 1)
            if _structured_logger:
                _structured_logger.exception("Agent creation failed", agent_type=agent_type)

            raise RuntimeError(f"Agent creation failed for type '{agent_type}': {e}") from e

    @classmethod
    async def create_booking_agent(
        cls, mcp_tools: list[types.FunctionDeclaration] | None = None, **kwargs: Any
    ) -> BaseAgent:
        """Create a BookingAgent (convenience method).

        Args:
            mcp_tools: Optional list of booking MCP tools.
            **kwargs: Additional parameters for agent creation.

        Returns:
            Initialized BookingAgent instance.

        Example:
            >>> agent = await AgentFactory.create_booking_agent(mcp_tools=tools)
        """
        return await cls.create("booking", mcp_tools=mcp_tools, **kwargs)

    @classmethod
    async def create_general_agent(cls, **kwargs: Any) -> BaseAgent:
        """Create a GeneralAgent (convenience method).

        Args:
            **kwargs: Additional parameters for agent creation.

        Returns:
            Initialized GeneralAgent instance.

        Example:
            >>> agent = await AgentFactory.create_general_agent()
        """
        return await cls.create("general", **kwargs)

    @classmethod
    async def create_sales_agent(
        cls, mcp_tools: list[types.FunctionDeclaration] | None = None, **kwargs: Any
    ) -> BaseAgent:
        """Create a SalesAgent (convenience method).

        Args:
            mcp_tools: Optional list of product/sales MCP tools.
            **kwargs: Additional parameters for agent creation.

        Returns:
            Initialized SalesAgent instance with advanced features.

        Example:
            >>> agent = await AgentFactory.create_sales_agent(mcp_tools=tools)
        """
        return await cls.create("sales", mcp_tools=mcp_tools, **kwargs)

    @classmethod
    def register_agent(cls, agent_type: str, agent_class: type[BaseAgent]) -> None:
        """Register a new agent type (for extensions).

        This method allows you to register custom agent types that can be
        created via the factory.

        Args:
            agent_type: Unique identifier for the agent type.
            agent_class: Agent class (must inherit from BaseAgent).

        Raises:
            ValueError: If agent_type already registered or agent_class invalid.

        Example:
            >>> class CustomAgent(BaseAgent):
            ...     # Custom implementation
            ...     pass
            >>>
            >>> AgentFactory.register_agent("custom", CustomAgent)
            >>> agent = await AgentFactory.create("custom")
        """
        cls._initialize_registry()

        # Validate agent_class is a subclass of BaseAgent
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class must inherit from BaseAgent, got {agent_class}")

        # Check if already registered
        if agent_type in cls._AGENT_REGISTRY:
            logger.warning(f"Agent type '{agent_type}' already registered, overwriting...")

        # Register
        cls._AGENT_REGISTRY[agent_type] = agent_class
        logger.info(f"Registered new agent type: '{agent_type}' -> {agent_class.__name__}")

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """Check if an agent type is registered.

        Args:
            agent_type: Agent type to check.

        Returns:
            True if registered, False otherwise.

        Example:
            >>> AgentFactory.is_registered("booking")
            True
            >>> AgentFactory.is_registered("unknown")
            False
        """
        cls._initialize_registry()
        return agent_type in cls._AGENT_REGISTRY
