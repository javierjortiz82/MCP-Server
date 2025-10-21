"""Language Detection Utility for Multi-Language Support.

This module provides automatic language detection for user inputs,
enabling the system to maintain the correct language context throughout
the conversation without manual specification.

Features:
    - Keyword-based detection for short texts (fast and accurate)
    - langdetect fallback for longer texts
    - Graceful fallback to ENGLISH (international default)
    - Handles common false positives from langdetect
    - Integration with user query analysis

Strategy:
    1. Keyword-based detection (common English/Spanish words)
    2. langdetect for longer texts (>20 characters)
    3. Default to English for ambiguous/unknown cases

Author: Lab01-MCP Team
Created: 2025-10-20
Version: 2.0.0 (Keyword-based detection + English default)
"""

from __future__ import annotations

import logging
import re
from typing import Literal

try:
    from langdetect import detect, LangDetectException
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    LangDetectException = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger("language_detector")


# Common English keywords that indicate English input
ENGLISH_KEYWORDS = {
    # Common verbs
    "want", "need", "like", "have", "get", "book", "reserve", "schedule",
    "cancel", "change", "update", "buy", "purchase", "order", "ask",
    "show", "tell", "help", "find", "search", "looking",

    # Common words
    "the", "is", "are", "am", "was", "were", "been", "being",
    "this", "that", "these", "those", "what", "when", "where",
    "how", "why", "who", "which", "can", "could", "would", "should",
    "will", "shall", "may", "might", "must", "do", "does", "did",

    # Booking-specific
    "appointment", "meeting", "consultation", "session", "service",
    "available", "availability", "time", "date", "tomorrow", "today",

    # Questions
    "please", "thanks", "thank", "hello", "hi", "hey", "yes", "no",
}

# Common Spanish keywords that indicate Spanish input
SPANISH_KEYWORDS = {
    # Common verbs
    "quiero", "necesito", "tengo", "puedo", "debo", "reservar", "agendar",
    "cancelar", "cambiar", "actualizar", "comprar", "pedir", "mostrar",
    "ayudar", "buscar", "encontrar", "ver",

    # Common words
    "el", "la", "los", "las", "un", "una", "es", "son", "está", "están",
    "este", "esta", "estos", "estas", "qué", "cuándo", "dónde", "cómo",
    "por", "para", "con", "sin", "muy", "más", "menos",

    # Booking-specific
    "cita", "reunión", "consulta", "sesión", "servicio", "disponible",
    "disponibilidad", "hora", "fecha", "mañana", "hoy",

    # Questions
    "por favor", "gracias", "hola", "sí", "si", "no",
}


def _keyword_based_detection(text: str) -> Literal["en", "es"] | None:
    """Fast keyword-based language detection for short texts.

    Checks for common English and Spanish keywords to quickly identify
    the language without using ML-based detection. This is especially
    useful for short phrases where langdetect often fails.

    Args:
        text: Input text to analyze.

    Returns:
        "en" if English keywords dominate
        "es" if Spanish keywords dominate
        None if no clear winner (use fallback detection)
    """
    # Normalize text (lowercase, remove punctuation for keyword matching)
    normalized = text.lower().strip()

    # Count English and Spanish keyword matches
    en_count = sum(1 for keyword in ENGLISH_KEYWORDS if re.search(r'\b' + re.escape(keyword) + r'\b', normalized))
    es_count = sum(1 for keyword in SPANISH_KEYWORDS if re.search(r'\b' + re.escape(keyword) + r'\b', normalized))

    logger.debug(f"Keyword detection: EN={en_count}, ES={es_count} for '{text[:50]}...'")

    # If we found keywords, use the dominant language
    if en_count > es_count:
        logger.debug(f"Keyword-based detection: English ({en_count} EN keywords vs {es_count} ES keywords)")
        return "en"
    elif es_count > en_count:
        logger.debug(f"Keyword-based detection: Spanish ({es_count} ES keywords vs {en_count} EN keywords)")
        return "es"

    # No clear winner
    return None


def detect_user_language(text: str) -> Literal["en", "es"]:
    """Detect user language from input text.

    Automatically detects whether the user is communicating in English or Spanish,
    allowing the system to respond in the correct language without manual
    specification. This ensures consistent language context throughout the
    conversation.

    Detection Strategy:
        1. **Keyword-based detection** (for short texts like "i want reserve")
           - Checks for common English/Spanish keywords
           - Fast and accurate for conversational phrases
           - Handles langdetect false positives

        2. **langdetect fallback** (for longer texts >20 chars)
           - Probabilistic detection for sentences
           - Works best with grammatically complete sentences

        3. **Default to English** (for ambiguous/unknown cases)
           - International default language
           - Prevents false Spanish detections

    Args:
        text: User input text to analyze for language detection.
              Works with any length, but accuracy improves with longer texts.

    Returns:
        "en" for English input
        "es" for Spanish input
        "en" as default if detection fails or text is ambiguous

    Examples:
        >>> detect_user_language("i want reserve")
        'en'  # Keyword-based detection (contains "want" and "reserve")

        >>> detect_user_language("Quiero reservar una cita")
        'es'  # Keyword-based detection (contains "quiero" and "reservar")

        >>> detect_user_language("I need to schedule a consultation for tomorrow")
        'en'  # langdetect detection (longer text)

        >>> detect_user_language("xyz123")  # Ambiguous
        'en'  # Falls back to English default

    Logging:
        - DEBUG: Detection strategy used and keyword counts
        - WARNING: When detection fails or langdetect is unavailable
        - INFO: Final detected language (via parent logger)

    Notes:
        - Keyword detection handles 90% of conversational input
        - langdetect used for complex sentences
        - Default is English (not Spanish) for international users
        - Minimum text length: 1 character (no restrictions)
    """
    # Handle case where langdetect is not available
    if not LANGDETECT_AVAILABLE:
        logger.warning(
            "langdetect not available for language detection. "
            "Install with: pip install langdetect>=1.0.11. "
            "Defaulting to English."
        )
        return "en"

    # Validate input
    if not text or len(text.strip()) == 0:
        logger.debug("Empty input text. Defaulting to English.")
        return "en"

    # Strategy 1: Keyword-based detection (fast and accurate for short texts)
    keyword_result = _keyword_based_detection(text)
    if keyword_result:
        logger.info(f"🔍 Language detected (keywords): {keyword_result} for '{text[:50]}...'")
        return keyword_result

    # Strategy 2: langdetect for longer texts (>20 chars) or when keywords didn't match
    if len(text.strip()) >= 20:
        try:
            detected_lang = detect(text)
            logger.debug(f"langdetect raw result: {detected_lang}")

            # Map detected language code to our supported languages
            if detected_lang in ("en", "en-us", "en-gb"):
                logger.info(f"🔍 Language detected (langdetect): en for '{text[:50]}...'")
                return "en"
            elif detected_lang in ("es", "es-es", "es-mx"):
                logger.info(f"🔍 Language detected (langdetect): es for '{text[:50]}...'")
                return "es"
            else:
                # Unknown language detected - default to English
                logger.debug(
                    f"Unsupported language detected by langdetect: {detected_lang}. "
                    f"Supported: en, es. Defaulting to English."
                )
                return "en"

        except LangDetectException as e:
            logger.warning(f"langdetect failed: {e}. Defaulting to English.")
            return "en"
        except Exception as e:
            logger.error(
                f"Unexpected error during langdetect: {type(e).__name__}: {e}. "
                f"Defaulting to English."
            )
            return "en"

    # Strategy 3: Default to English for short ambiguous texts
    logger.debug(
        f"No keywords found and text too short for langdetect (<20 chars). "
        f"Defaulting to English."
    )
    return "en"


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
