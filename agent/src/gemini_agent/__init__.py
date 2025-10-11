"""Gemini Agent - Google Gemini AI Service Provider.

This package provides a standalone AI service for Google Gemini integration,
designed to be imported and used by other applications.

Example:
    >>> from gemini_agent import GeminiAgent
    >>> agent = GeminiAgent(api_key="your-key")
    >>> await agent.initialize()
    >>> response = await agent.generate_response("Hello!")
"""

from gemini_agent.agent import GeminiAgent
from gemini_agent.config import settings

__version__ = "1.0.0"

__all__ = [
    "GeminiAgent",
    "settings",
]
