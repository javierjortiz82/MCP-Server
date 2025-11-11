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

        CRITICAL FIX: Includes memory blocks and conversation context in system prompt
        to help agent understand user preferences and previous conversation state.

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
        user_lang = kwargs.get("user_lang", "es")
        prompt = self._prompt_manager.get_general_prompt(
            user_id=kwargs.get("user_id"),
            user_lang=user_lang,  # Pass language context for template selection
        )

        # CRITICAL FIX: Append memory blocks context to system prompt
        # This helps the agent understand user preferences and conversation history
        customer_email = kwargs.get("customer_email")
        if self._memory_enabled:
            try:
                # Get session-level memory blocks (this conversation)
                session_blocks = self.get_memory_blocks(agent_scope="general")
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

        self.logger.debug(f"Loaded general prompt from Jinja2 ({len(prompt)} chars)")
        return prompt

    def __repr__(self) -> str:
        """String representation of GeneralAgent."""
        return (
            f"GeneralAgent(model={self.model_name}, history_len={len(self.conversation_history)})"
        )
