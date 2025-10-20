"""Gemini Agent - Google Gemini AI Service Provider.

This package provides a standalone AI service for Google Gemini integration,
designed to be imported and used by other applications.

Components:
    - GeminiAgent: Direct Gemini API client (DEPRECATED - use BaseAgent instead)
    - BaseAgent: Abstract base class for specialized agents (recommended for new code)
    - settings: Configuration management

Example (BaseAgent - RECOMMENDED):
    >>> from gemini_agent import BaseAgent
    >>> class MyAgent(BaseAgent):
    ...     @property
    ...     def agent_name(self) -> str:
    ...         return "my_agent"
    ...     def get_system_prompt(self, **kwargs) -> str:
    ...         return "You are MyAgent..."
    >>> agent = MyAgent()
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Hello!")

Example (Specialized Agents - HIGHLY RECOMMENDED):
    >>> from multi_agent import BookingAgent, SalesAgent, GeneralAgent
    >>> agent = BookingAgent()  # or SalesAgent(), GeneralAgent()
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Hello!")

Deprecation Notice:
    GeminiAgent is deprecated as of v1.2.0 and will be removed on 2025-12-31.
    Use BaseAgent or specialized agents (BookingAgent, SalesAgent, GeneralAgent) instead.
    See: src/gemini_agent/agent.py for migration guide.
"""

import warnings

from gemini_agent.agent import GeminiAgent
from gemini_agent.base_agent import BaseAgent
from gemini_agent.config import settings

__version__ = "1.2.0"  # Bumped for GeminiAgent deprecation

__all__ = [
    "BaseAgent",
    "GeminiAgent",  # Kept for backward compatibility, but deprecated
    "settings",
]

# Emit deprecation warning at module import
warnings.warn(
    "GeminiAgent is deprecated and will be removed on 2025-12-31. "
    "Use BaseAgent or specialized agents (BookingAgent, SalesAgent, GeneralAgent) instead. "
    "See src/gemini_agent/agent.py for migration guide.",
    category=DeprecationWarning,
    stacklevel=2,
)
