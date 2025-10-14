"""Gemini Agent - Google Gemini AI Service Provider.

This package provides a standalone AI service for Google Gemini integration,
designed to be imported and used by other applications.

Components:
    - GeminiAgent: Direct Gemini API client (legacy, backward compatible)
    - BaseAgent: Abstract base class for specialized agents (recommended for new code)
    - settings: Configuration management

Example (Legacy GeminiAgent):
    >>> from gemini_agent import GeminiAgent
    >>> agent = GeminiAgent(api_key="your-key")
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Hello!")

Example (BaseAgent - Recommended):
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
"""

from gemini_agent.agent import GeminiAgent
from gemini_agent.base_agent import BaseAgent
from gemini_agent.config import settings

__version__ = "1.1.0"  # Bumped for BaseAgent addition

__all__ = [
    "BaseAgent",
    "GeminiAgent",
    "settings",
]
