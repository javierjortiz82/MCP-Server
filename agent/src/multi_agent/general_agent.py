"""General Agent - FAQ and General Information Handler.

This module provides the GeneralAgent class that handles general information
queries, FAQ, company policies, and support questions. Uses Gemini 2.5 Flash
without specialized tools, focusing on knowledge-based responses.

The agent specializes in:
- Company information and policies
- Frequently asked questions (FAQ)
- Business hours and contact information
- Shipping and payment methods
- Return and warranty policies
- General customer support

Architecture:
    GeneralAgent inherits from BaseAgent, eliminating ~280 lines of duplicated code.
    Only agent-specific functionality is implemented here:
    - System prompt via PromptManager (with A/B testing support)
    - General information business logic

References:
    - https://ai.google.dev/gemini-api/docs/function-calling
    - https://googleapis.github.io/python-genai/
    - https://github.com/anthropics/anthropic-quickstarts/tree/main/mcp

Author: Lab01-MCP Team
Created: 2025-10-11
Version: 2.0.0 (Refactored to inherit from BaseAgent)
"""

from __future__ import annotations

from typing import Any

from gemini_agent.base_agent import BaseAgent
from multi_agent.prompt_manager import PromptManager


class GeneralAgent(BaseAgent):
    """Specialized agent for handling general information and FAQ queries.

    Inherits all common functionality from BaseAgent:
    - Gemini client initialization and lifecycle
    - Conversation history management
    - Base generation configuration
    - Response generation pipeline

    GeneralAgent-specific additions:
    - General information system prompt via PromptManager (with A/B testing)
    - Knowledge-based responses (no MCP tools needed)

    Example:
        >>> agent = GeneralAgent()
        >>> await agent.initialize()
        >>> response = await agent.generate_response(
        ...     "Cuál es su horario de atención?"
        ... )
    """

    # PromptManager instance (shared across all GeneralAgent instances)
    _prompt_manager: PromptManager | None = None

    def __init__(self, **kwargs: Any) -> None:
        """Initialize GeneralAgent with response_handler disabled.

        GeneralAgent doesn't use function calling or complex error handling,
        so response_handler is disabled to reduce overhead.

        Args:
            **kwargs: Arguments passed to BaseAgent.__init__()
        """
        # Disable response_handler for GeneralAgent (no function calling, simpler logic)
        super().__init__(enable_response_handler=False, **kwargs)

    @property
    def agent_name(self) -> str:
        """Return agent name for logging.

        Required by BaseAgent abstract property.
        """
        return "general_agent"

    def get_system_prompt(self, **kwargs: Any) -> str:
        """Get system prompt for GeneralAgent using PromptManager (Jinja2).

        Implements BaseAgent's abstract method.

        Args:
            **kwargs: Additional parameters (user_id for A/B testing, etc.).

        Returns:
            System prompt text for GeneralAgent.

        Example:
            >>> prompt = agent.get_system_prompt()
        """
        # Initialize PromptManager if not already done
        if self._prompt_manager is None:
            self.logger.debug("Initializing PromptManager for GeneralAgent (Jinja2)")
            self._prompt_manager = PromptManager()

        # Get prompt from PromptManager (supports A/B testing and multilingual)
        prompt = self._prompt_manager.get_general_prompt(
            user_id=kwargs.get("user_id"),
            user_lang=kwargs.get("user_lang", "es"),  # Pass language context for template selection
        )
        self.logger.debug(f"Loaded general prompt from Jinja2 ({len(prompt)} chars)")
        return prompt

    def __repr__(self) -> str:
        """String representation of GeneralAgent."""
        return (
            f"GeneralAgent(model={self.model_name}, history_len={len(self.conversation_history)})"
        )
