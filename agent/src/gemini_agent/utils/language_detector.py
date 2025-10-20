"""Language Detection Utility for Multi-Language Support.

This module provides automatic language detection for user inputs,
enabling the system to maintain the correct language context throughout
the conversation without manual specification.

Features:
    - Automatic detection of English and Spanish
    - Graceful fallback to Spanish on detection failure
    - Lightweight and fast (no ML models required)
    - Integration with user query analysis

Author: Lab01-MCP Team
Created: 2025-10-20
Version: 1.0.0
"""

from __future__ import annotations

import logging
from typing import Literal

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    LangDetectException = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger("language_detector")


def detect_user_language(text: str) -> Literal["en", "es"]:
    """Detect user language from input text.

    Automatically detects whether the user is communicating in English or Spanish,
    allowing the system to respond in the correct language without manual
    specification. This ensures consistent language context throughout the
    conversation.

    The detection uses the langdetect library which:
    - Works with short text (>3 characters)
    - Handles mixed language input (returns dominant language)
    - Is fast and doesn't require ML models
    - Is accurate for English/Spanish detection

    Args:
        text: User input text to analyze for language detection.
              Should be at least 3 characters for accurate detection.

    Returns:
        "en" for English input
        "es" for Spanish input
        "es" as default if detection fails or text is too short

    Examples:
        >>> detect_user_language("i want to reserve a meeting")
        'en'

        >>> detect_user_language("Quiero reservar una reunión")
        'es'

        >>> detect_user_language("Hello hola")  # Mixed
        'en'  # Dominant language

        >>> detect_user_language("ok")  # Too short
        'es'  # Falls back to default

    Logging:
        - WARNING: When detection fails or langdetect is unavailable
        - INFO: When language is successfully detected (via parent logger)

    Notes:
        - Requires langdetect library (pip install langdetect)
        - If langdetect is not available, defaults to Spanish
        - Minimum recommended text length: 10+ characters for high accuracy
        - Works best with sentences, not single words
    """
    # Handle case where langdetect is not available
    if not LANGDETECT_AVAILABLE:
        logger.warning(
            "langdetect not available for language detection. "
            "Install with: pip install langdetect>=1.0.11. "
            "Defaulting to Spanish."
        )
        return "es"

    # Validate input
    if not text or len(text.strip()) < 3:
        logger.debug(
            f"Input text too short for reliable detection (length: {len(text)}). "
            f"Defaulting to Spanish."
        )
        return "es"

    try:
        # Detect language from text
        detected_lang = detect(text)

        # Map detected language code to our supported languages
        # langdetect returns ISO 639-1 codes (e.g., 'en', 'es', 'fr', etc.)
        if detected_lang.startswith("en"):
            return "en"
        elif detected_lang.startswith("es"):
            return "es"
        else:
            # Unknown language detected - default to Spanish
            logger.debug(
                f"Unsupported language detected: {detected_lang}. "
                f"Supported: en, es. Defaulting to Spanish."
            )
            return "es"

    except LangDetectException as e:
        # Detection failed (e.g., input not in any known language)
        logger.warning(
            f"Language detection failed: {e}. "
            f"Defaulting to Spanish."
        )
        return "es"
    except Exception as e:
        # Unexpected error during detection
        logger.error(
            f"Unexpected error during language detection: {type(e).__name__}: {e}. "
            f"Defaulting to Spanish."
        )
        return "es"


def get_language_name(lang_code: str) -> str:
    """Get human-readable name for language code.

    Args:
        lang_code: Language code ("en" or "es")

    Returns:
        Human-readable language name

    Examples:
        >>> get_language_name("en")
        'English'

        >>> get_language_name("es")
        'Spanish'
    """
    language_names = {
        "en": "English",
        "es": "Spanish",
    }
    return language_names.get(lang_code, "Unknown")
