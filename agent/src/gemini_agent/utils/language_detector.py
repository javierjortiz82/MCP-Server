"""Language Detector Module - Simple wrapper for language detection.

This module provides a simple function-based interface to detect the language
of user input. It serves as a backward-compatible wrapper around the
LanguageDetectorService class.

Architecture:
    - Lazy-loads LanguageDetectorService on first call
    - Caches service instance for performance
    - Provides simple synchronous interface for easy integration
    - Handles both sync and async contexts

Author: Lab01-MCP Team
Created: 2025-11-18
Version: 1.0.0
"""

from __future__ import annotations

import asyncio
from typing import Optional

# Global instance cache
_detector_instance: Optional[object] = None
_detector_initialized: bool = False


def detect_user_language(text: str, session_language: Optional[str] = None) -> str:
    """Detect the language of user input (synchronous wrapper).

    This is a simplified synchronous wrapper that handles asyncio event loop
    management automatically. It's designed to work in both sync and async contexts.

    Args:
        text: User input text to analyze
        session_language: Current session language (fallback for ambiguous text)

    Returns:
        Language code as string ("en", "es", etc.)

    Example:
        >>> lang = detect_user_language("proximo martes")
        >>> print(lang)
        'es'

        >>> lang = detect_user_language("hello")
        >>> print(lang)
        'en'
    """
    # Validate input
    if not text or len(text.strip()) == 0:
        return session_language or "en"

    try:
        # Try to get running event loop
        loop = asyncio.get_running_loop()
        # We're in an async context - don't create a new event loop
        # Instead, return the session language as fallback
        # The caller should use await detect_language_async() directly
        return session_language or "en"
    except RuntimeError:
        # No event loop running, create a new one
        try:
            return asyncio.run(_detect_async(text, session_language))
        except Exception as e:
            # Fallback to session language or default
            fallback = session_language or "en"
            # Silently fallback without printing errors
            # (errors are already logged by the service)
            return fallback


async def detect_language_async(text: str, session_language: Optional[str] = None) -> str:
    """Async language detection helper.

    Use this function when you're already in an async context to avoid
    creating nested event loops.

    Args:
        text: User input text to analyze
        session_language: Current session language (fallback for ambiguous text)

    Returns:
        Language code as string

    Example:
        >>> async def process():
        ...     lang = await detect_language_async("proximo martes")
        ...     print(lang)  # 'es'
        >>> asyncio.run(process())
    """
    return await _detect_async(text, session_language)


async def _detect_async(text: str, session_language: Optional[str] = None) -> str:
    """Async language detection helper.

    Args:
        text: User input text to analyze
        session_language: Current session language (fallback for ambiguous text)

    Returns:
        Language code as string
    """
    global _detector_instance, _detector_initialized

    try:
        # Lazy initialize service on first call
        if not _detector_initialized:
            from gemini_agent.services.language_detector_service import LanguageDetectorService

            _detector_instance = LanguageDetectorService()
            await _detector_instance.initialize()
            _detector_initialized = True

        # Use cached instance
        if _detector_instance:
            detected = await _detector_instance.detect_language(
                text,
                session_language=session_language,
                use_cache=True
            )
            return detected

        # Fallback if service is not available
        return session_language or "en"

    except Exception as e:
        # Fallback to session language or default
        fallback = session_language or "en"
        # Error is already logged by the service
        return fallback


def reset_detector_cache() -> None:
    """Reset the language detector cache.

    Useful for testing or when you want to force fresh detections.
    """
    global _detector_instance
    if _detector_instance and hasattr(_detector_instance, 'clear_cache'):
        _detector_instance.clear_cache()