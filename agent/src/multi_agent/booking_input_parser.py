"""
Booking Input Parser - Flexible User Response Parsing

Parses user responses for booking operations with fuzzy matching:
- Reschedule/Cancel options (A/B, 1/2, keywords, typos)
- Date/Time selections
- Confirmation (Yes/No)
- Service selections

Configuration thresholds are loaded from environment or mcp_server settings:
- BOOKING_CHOICE_CONFIDENCE_THRESHOLD: Minimum confidence for reschedule/cancel
- BOOKING_PARTIAL_MATCH_CONFIDENCE: Confidence for partial word matches
- BOOKING_MIN_KEYWORD_LENGTH: Minimum length for substring matching
- BOOKING_FUZZY_MATCH_THRESHOLD: Minimum score for fuzzy matching
- BOOKING_CONFIRMATION_THRESHOLD: Minimum confidence for yes/no
- BOOKING_CLARIFICATION_THRESHOLD: Below which to ask for clarification

Author: Lab01-MCP Team
Created: 2025-10-16
Version: 1.0
"""

import logging
import re
import sys
from difflib import SequenceMatcher
from enum import Enum
from pathlib import Path
from typing import Tuple

# Try to import settings from mcp_server
try:
    from config.settings import settings

    CHOICE_CONFIDENCE_THRESHOLD = settings.BOOKING_CHOICE_CONFIDENCE_THRESHOLD
    PARTIAL_MATCH_CONFIDENCE = settings.BOOKING_PARTIAL_MATCH_CONFIDENCE
    MIN_KEYWORD_LENGTH = settings.BOOKING_MIN_KEYWORD_LENGTH
    FUZZY_MATCH_THRESHOLD = settings.BOOKING_FUZZY_MATCH_THRESHOLD
    CONFIRMATION_THRESHOLD = settings.BOOKING_CONFIRMATION_THRESHOLD
    CLARIFICATION_THRESHOLD = settings.BOOKING_CLARIFICATION_THRESHOLD
except (ImportError, ModuleNotFoundError):
    # Fallback to hardcoded defaults if mcp_server settings not available
    # These should match the defaults in mcp_server/config/settings.py
    CHOICE_CONFIDENCE_THRESHOLD = 0.75  # Increased from 0.6 to reduce misclassification
    PARTIAL_MATCH_CONFIDENCE = 0.95
    MIN_KEYWORD_LENGTH = 3
    FUZZY_MATCH_THRESHOLD = 0.75
    CONFIRMATION_THRESHOLD = 0.75  # Increased from 0.6 to reduce misclassification
    CLARIFICATION_THRESHOLD = 0.6

# Try to import keyword constants
try:
    from config.booking_constants import BOOKING_CHOICE_OPTIONS

    RESCHEDULE_OPTIONS = set(BOOKING_CHOICE_OPTIONS.get("option_a", []))
    CANCEL_OPTIONS = set(BOOKING_CHOICE_OPTIONS.get("option_b", []))
except (ImportError, ModuleNotFoundError):
    # Fallback if constants not available
    RESCHEDULE_OPTIONS = {"a", "1", "opcion a", "opcion 1", "opción a", "opción 1"}
    CANCEL_OPTIONS = {"b", "2", "opcion b", "opcion b", "opción b", "opción b"}

# Setup logger
logger = logging.getLogger(__name__)


class BookingChoice(Enum):
    """User choices for booking operations."""

    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    CONFIRM = "confirm"
    DENY = "deny"
    UNKNOWN = "unknown"


class BookingInputParser:
    """Parser for flexible booking user responses."""

    # Spanish keywords
    RESCHEDULE_KEYWORDS_ES = {
        "reprograma",
        "reprogramar",
        "cambiar",
        "cambio",
        "modificar",
        "modificacion",
        "mover",
        "otra fecha",
        "otra hora",
        "nuevo horario",
        "nuevo tiempo",
    }

    CANCEL_KEYWORDS_ES = {
        "cancela",
        "cancelar",
        "cancelacion",
        "borrar",
        "eliminar",
        "quitar",
        "no deseo",
    }

    CONFIRM_KEYWORDS_ES = {
        "si",
        "sí",
        "confirmar",
        "confirmo",
        "aceptar",
        "acepto",
        "de acuerdo",
        "bueno",
        "claro",
        "adelante",
        "proceder",
    }

    DENY_KEYWORDS_ES = {
        "no",
        "nada",
        "ninguno",
        "negativo",
        "rechazar",
        "rechazo",
    }

    # English keywords
    RESCHEDULE_KEYWORDS_EN = {
        "reschedule",
        "rescheduled",
        "change",
        "modify",
        "rescheduling",
    }

    CANCEL_KEYWORDS_EN = {
        "delete",
        "remove",
        "cancel",
    }

    CONFIRM_KEYWORDS_EN = {
        "yes",
        "ok",
        "okay",
        "confirm",
        "accept",
        "agree",
    }

    DENY_KEYWORDS_EN = {
        "no",
        "nope",
        "reject",
        "deny",
    }

    # Combined keywords for backward compatibility
    RESCHEDULE_KEYWORDS = RESCHEDULE_KEYWORDS_ES | RESCHEDULE_KEYWORDS_EN | {"a", "1"}
    CANCEL_KEYWORDS = CANCEL_KEYWORDS_ES | CANCEL_KEYWORDS_EN | {"b", "2"}
    CONFIRM_KEYWORDS = CONFIRM_KEYWORDS_ES | CONFIRM_KEYWORDS_EN
    DENY_KEYWORDS = DENY_KEYWORDS_ES | DENY_KEYWORDS_EN

    # Language detection indicators
    ES_INDICATORS = {
        "que", "de", "el", "la", "los", "las", "en", "para", "por", "con",
        "una", "un", "unos", "unas", "mi", "mis", "tu", "tus", "su", "sus",
        "quisiera", "quiero", "necesito", "puedo", "puede", "tengo",
    }

    # Negative keywords (words that should NOT match common keywords)
    # Used to prevent false positives from substring matching
    NEGATIVE_KEYWORDS = {
        "bueno",  # Contains "no" but is a confirmation keyword
        "bien",  # Spanish: "well/good" - should not match "no"
        "malo",  # Spanish: "bad" - contains "no"
        "numero",  # Contains "no"
        "novela",  # Contains "no"
        "noviembre",  # Contains "no"
    }

    @classmethod
    def detect_language(cls, normalized_input: str) -> str:
        """
        Detect the language of the input (Spanish or English).

        Uses heuristic approach: counts Spanish indicators in the input.
        Returns 'es' for Spanish, 'en' for English.

        Args:
            normalized_input: Normalized user input

        Returns:
            'es' for Spanish, 'en' for English (default)
        """
        if not normalized_input:
            return 'en'  # Default to English

        words = set(normalized_input.split())
        es_count = len(words & cls.ES_INDICATORS)

        # If more than 30% of words are Spanish indicators, classify as Spanish
        if len(words) > 0 and es_count / len(words) > 0.3:
            return 'es'

        return 'en'

    @classmethod
    def _get_language_keywords(cls, language: str) -> Tuple[set, set, set, set]:
        """
        Get keyword sets for the specified language.

        Args:
            language: 'es' for Spanish, 'en' for English

        Returns:
            Tuple of (reschedule_kw, cancel_kw, confirm_kw, deny_kw)
        """
        if language == 'es':
            return (
                cls.RESCHEDULE_KEYWORDS_ES | {"a", "1"},
                cls.CANCEL_KEYWORDS_ES | {"b", "2"},
                cls.CONFIRM_KEYWORDS_ES,
                cls.DENY_KEYWORDS_ES,
            )
        else:  # 'en'
            return (
                cls.RESCHEDULE_KEYWORDS_EN | {"a", "1"},
                cls.CANCEL_KEYWORDS_EN | {"b", "2"},
                cls.CONFIRM_KEYWORDS_EN,
                cls.DENY_KEYWORDS_EN,
            )

    @classmethod
    def parse_booking_choice(cls, user_input: str) -> Tuple[BookingChoice, float]:
        """
        Parse user input for reschedule/cancel decision.

        Args:
            user_input: Raw user response text

        Returns:
            Tuple of (BookingChoice, confidence_score)
            - confidence_score: 0.0 to 1.0 indicating confidence in classification

        Raises:
            ValueError: If user_input is None or empty after normalization
        """
        if not user_input or not user_input.strip():
            raise ValueError("parse_booking_choice: User input cannot be empty or whitespace only")

        # Normalize input
        normalized = cls._normalize_input(user_input)

        # Validate that normalization didn't result in empty string
        if not normalized:
            raise ValueError(f"parse_booking_choice: Input '{user_input}' resulted in empty normalized string")

        # Detect language and get language-specific keywords
        language = cls.detect_language(normalized)
        reschedule_kw, cancel_kw, _, _ = cls._get_language_keywords(language)

        # Check exact matches first (highest confidence)
        if normalized in RESCHEDULE_OPTIONS:
            return BookingChoice.RESCHEDULE, 1.0

        if normalized in CANCEL_OPTIONS:
            return BookingChoice.CANCEL, 1.0

        # Check keyword matches using language-specific keywords
        reschedule_score = cls._calculate_match_score(normalized, reschedule_kw)
        cancel_score = cls._calculate_match_score(normalized, cancel_kw)

        if reschedule_score > cancel_score and reschedule_score > CHOICE_CONFIDENCE_THRESHOLD:
            return BookingChoice.RESCHEDULE, reschedule_score

        if cancel_score > reschedule_score and cancel_score > CHOICE_CONFIDENCE_THRESHOLD:
            return BookingChoice.CANCEL, cancel_score

        logger.warning(
            f"Could not parse booking choice with confidence. "
            f"Input: '{user_input}', "
            f"Reschedule score: {reschedule_score}, "
            f"Cancel score: {cancel_score}"
        )

        return BookingChoice.UNKNOWN, max(reschedule_score, cancel_score)

    @classmethod
    def parse_confirmation(cls, user_input: str) -> Tuple[BookingChoice, float]:
        """
        Parse user input for yes/no confirmation.

        Args:
            user_input: Raw user response text

        Returns:
            Tuple of (BookingChoice, confidence_score)
            - Confidence: 0.0 to 1.0

        Raises:
            ValueError: If user_input is None or empty after normalization
        """
        if not user_input or not user_input.strip():
            raise ValueError("parse_confirmation: User input cannot be empty or whitespace only")

        normalized = cls._normalize_input(user_input)

        # Validate that normalization didn't result in empty string
        if not normalized:
            raise ValueError(f"parse_confirmation: Input '{user_input}' resulted in empty normalized string")

        # Detect language and get language-specific keywords
        language = cls.detect_language(normalized)
        _, _, confirm_kw, deny_kw = cls._get_language_keywords(language)

        # Check confirmation using language-specific keywords
        confirm_score = cls._calculate_match_score(normalized, confirm_kw)
        deny_score = cls._calculate_match_score(normalized, deny_kw)

        if confirm_score > deny_score and confirm_score > CONFIRMATION_THRESHOLD:
            return BookingChoice.CONFIRM, confirm_score

        if deny_score > confirm_score and deny_score > CONFIRMATION_THRESHOLD:
            return BookingChoice.DENY, deny_score

        return BookingChoice.UNKNOWN, max(confirm_score, deny_score)

    @classmethod
    def _normalize_input(cls, text: str) -> str:
        """
        Normalize user input for comparison.

        - Remove accents
        - Convert to lowercase
        - Remove extra whitespace
        - Remove punctuation
        """
        if not text:
            return ""

        # Lowercase first
        text = text.lower()

        # Remove accents
        accents_map = {
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "ñ": "n",
        }
        for accented, unaccented in accents_map.items():
            text = text.replace(accented, unaccented)

        # Remove punctuation
        text = re.sub(r"[^\w\s]", "", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text

    @classmethod
    def _calculate_match_score(
        cls, normalized_input: str, keywords: set
    ) -> float:
        """
        Calculate match score between input and keyword set using fuzzy matching.

        Uses SequenceMatcher to handle typos and partial matches with smart filtering
        to avoid false positives from substring matching.

        Args:
            normalized_input: Normalized user input
            keywords: Set of keywords to match against

        Returns:
            Match score from 0.0 to 1.0
        """
        if not normalized_input or not keywords:
            return 0.0

        # Skip if input is in negative keyword list (false positive prevention)
        if normalized_input in cls.NEGATIVE_KEYWORDS:
            return 0.0

        best_score = 0.0
        input_words = set(normalized_input.split())

        for keyword in keywords:
            keyword_words = set(keyword.split())

            # Exact full match
            if normalized_input == keyword:
                return 1.0

            # Word-level matching (for phrases)
            if len(keyword_words) > 1 and input_words == keyword_words:
                return 1.0

            # Check for partial word matches in multi-word inputs
            if len(keyword_words) > 1 and input_words.issubset(keyword_words):
                best_score = max(best_score, PARTIAL_MATCH_CONFIDENCE)
                continue

            # Substring match with improved filtering
            # Only for keywords >= 4 chars to avoid matching short substrings like "no"
            if (
                len(keyword) >= 4  # Increased from MIN_KEYWORD_LENGTH (3) for safety
                and len(normalized_input) >= 4
                and (keyword in normalized_input or normalized_input in keyword)
            ):
                # Use lower confidence for substring matches (not 1.0)
                # This prevents false positives while still recognizing partial matches
                best_score = max(best_score, 0.9)
                continue

            # Fuzzy match using SequenceMatcher
            score = SequenceMatcher(
                None, normalized_input, keyword
            ).ratio()

            # Only accept fuzzy matches above a threshold
            if score > FUZZY_MATCH_THRESHOLD:
                best_score = max(best_score, score)

        return best_score

    @classmethod
    def should_show_error(cls, confidence: float, threshold: float = None) -> bool:
        """
        Determine if agent should ask for clarification.

        Args:
            confidence: Confidence score (0.0 to 1.0)
            threshold: Minimum confidence threshold (default: from CLARIFICATION_THRESHOLD)

        Returns:
            True if agent should ask for clarification
        """
        if threshold is None:
            threshold = CLARIFICATION_THRESHOLD
        return confidence < threshold


# Convenience functions
def parse_booking_choice(user_input: str) -> Tuple[BookingChoice, float]:
    """Parse reschedule/cancel choice. Returns (choice, confidence)."""
    return BookingInputParser.parse_booking_choice(user_input)


def parse_confirmation(user_input: str) -> Tuple[BookingChoice, float]:
    """Parse yes/no confirmation. Returns (choice, confidence)."""
    return BookingInputParser.parse_confirmation(user_input)


def should_ask_for_clarification(confidence: float) -> bool:
    """Check if agent should ask user to clarify."""
    return BookingInputParser.should_show_error(confidence)
