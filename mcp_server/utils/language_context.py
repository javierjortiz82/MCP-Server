"""Language Context Manager for MCP handlers and agents.

Provides thread-local language context storage for propagating language preference
through the MCP call stack without passing it as a parameter to every function.

This is similar to i18n.py but focuses on runtime context management rather than
translation file loading.

Usage:
    from utils.language_context import set_current_language, get_current_language

    # Set language for current thread
    set_current_language("es")

    # Get current language in MCP handler or booking function
    lang = get_current_language()

    # In AgentOrchestrator before calling MCP tools
    set_current_language(self.language)

Author: Lab01-MCP Team
Created: 2025-10-17
Version: 1.0.0
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

# Setup logger
logger = logging.getLogger("language_context")

# Thread-local storage for current language context
_language_context = threading.local()

# Default language
DEFAULT_LANGUAGE = "es"


class LanguageContextManager:
    """Manages language context for multi-threaded environments."""

    def __init__(self):
        """Initialize language context manager."""
        self._default_lang = DEFAULT_LANGUAGE
        logger.info(f"🌐 LanguageContextManager initialized (default: {self._default_lang})")

    def set_language(self, lang: str) -> None:
        """Set the current language context for the thread.

        Args:
            lang: Language code ("es", "en", etc.)
        """
        if lang not in ("es", "en"):
            logger.warning(f"⚠️ Unknown language code: {lang}, using default {self._default_lang}")
            lang = self._default_lang

        _language_context.lang = lang
        logger.debug(f"🌐 Language context set to: {lang}")

    def get_language(self) -> str:
        """Get the current language context for the thread.

        Returns:
            Current language code or default if not set.
        """
        lang = getattr(_language_context, "lang", None)
        if lang is None:
            lang = self._default_lang
            logger.debug(f"🌐 No language context found, using default: {lang}")
        return lang

    def reset_language(self) -> None:
        """Reset language context to default."""
        _language_context.lang = None
        logger.debug(f"🌐 Language context reset to default")


# Global singleton instance
_manager = LanguageContextManager()


def set_current_language(lang: str) -> None:
    """Set the current language context for the thread.

    This should be called by AgentOrchestrator before making MCP tool calls
    to ensure all downstream functions (MCP handlers, booking tools, etc.)
    use the correct language.

    Args:
        lang: Language code ("es" or "en")

    Example:
        >>> from client_mcp.core.agent_orchestrator import AgentOrchestrator
        >>> orchestrator.language = "es"
        >>> set_current_language(orchestrator.language)
        >>> # Now all MCP tools will use Spanish
    """
    _manager.set_language(lang)


def get_current_language() -> str:
    """Get the current language context for the thread.

    This should be called by MCP handlers and booking functions to get
    the user's language preference without having it passed as a parameter.

    Returns:
        Current language code or default ("es") if not set.

    Example:
        >>> from mcp_server.utils.language_context import get_current_language
        >>> # In booking_handlers.py
        >>> user_lang = get_current_language()
        >>> result = find_first_available_slots_in_range(
        ...     service_type="consultation",
        ...     start_date="2025-10-20",
        ...     end_date="2025-10-27",
        ...     user_lang=user_lang
        ... )
    """
    return _manager.get_language()


def reset_current_language() -> None:
    """Reset language context to default.

    Useful for testing or when transitioning between different user contexts.

    Example:
        >>> reset_current_language()
        >>> assert get_current_language() == "es"
    """
    _manager.reset_language()


def with_language(lang: str):
    """Context manager for temporarily setting a language.

    Useful for testing or for code blocks that need to use a specific language
    without affecting the thread-global context.

    Args:
        lang: Language code to use temporarily

    Example:
        >>> from utils.language_context import with_language
        >>> with with_language("en"):
        ...     result = some_function()
        ...     # result will be in English
        >>> # Language context reset after block
    """
    class LanguageContextGuard:
        def __init__(self, new_lang: str):
            self.new_lang = new_lang
            self.old_lang = None

        def __enter__(self):
            self.old_lang = _manager.get_language()
            _manager.set_language(self.new_lang)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            _manager.set_language(self.old_lang)
            return False

    return LanguageContextGuard(lang)


# Export public API
__all__ = [
    "set_current_language",
    "get_current_language",
    "reset_current_language",
    "with_language",
    "DEFAULT_LANGUAGE",
]
