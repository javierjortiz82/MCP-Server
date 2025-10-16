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
    CHOICE_CONFIDENCE_THRESHOLD = 0.6
    PARTIAL_MATCH_CONFIDENCE = 0.95
    MIN_KEYWORD_LENGTH = 3
    FUZZY_MATCH_THRESHOLD = 0.75
    CONFIRMATION_THRESHOLD = 0.6
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

    # Reschedule keywords (Spanish variants)
    RESCHEDULE_KEYWORDS = {
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
        "rescheduled",
        "change",
        "modify",
        "rescheduling",
        "reschedule",
        "a",  # Letter option
        "1",  # Numeric option
    }

    # Cancel keywords (Spanish variants)
    CANCEL_KEYWORDS = {
        "cancela",
        "cancelar",
        "cancelacion",
        "borrar",
        "eliminar",
        "quitar",
        "no deseo",  # For phrases like "no deseo ir"
        "delete",
        "remove",
        "b",  # Letter option
        "2",  # Numeric option
    }

    # Confirmation keywords (Yes/Confirm)
    CONFIRM_KEYWORDS = {
        "si",
        "sí",
        "yes",
        "confirmar",
        "confirmo",
        "aceptar",
        "acepto",
        "de acuerdo",
        "ok",
        "okay",
        "bueno",
        "claro",
        "adelante",
        "proceder",
    }

    # Denial keywords (No/Deny)
    DENY_KEYWORDS = {
        "no",
        "nope",
        "nada",
        "ninguno",
        "negativo",
        "rechazar",
        "rechazo",
        "cancelar",  # In confirmation context means "no, don't proceed"
    }

    @classmethod
    def parse_booking_choice(cls, user_input: str) -> Tuple[BookingChoice, float]:
        """
        Parse user input for reschedule/cancel decision.

        Args:
            user_input: Raw user response text

        Returns:
            Tuple of (BookingChoice, confidence_score)
            - confidence_score: 0.0 to 1.0 indicating confidence in classification
        """
        if not user_input:
            return BookingChoice.UNKNOWN, 0.0

        # Normalize input
        normalized = cls._normalize_input(user_input)

        # Check exact matches first (highest confidence)
        if normalized in RESCHEDULE_OPTIONS:
            return BookingChoice.RESCHEDULE, 1.0

        if normalized in CANCEL_OPTIONS:
            return BookingChoice.CANCEL, 1.0

        # Check keyword matches
        reschedule_score = cls._calculate_match_score(normalized, cls.RESCHEDULE_KEYWORDS)
        cancel_score = cls._calculate_match_score(normalized, cls.CANCEL_KEYWORDS)

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
        """
        if not user_input:
            return BookingChoice.UNKNOWN, 0.0

        normalized = cls._normalize_input(user_input)

        # Check confirmation
        confirm_score = cls._calculate_match_score(normalized, cls.CONFIRM_KEYWORDS)
        deny_score = cls._calculate_match_score(normalized, cls.DENY_KEYWORDS)

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

        Uses SequenceMatcher to handle typos and partial matches.

        Args:
            normalized_input: Normalized user input
            keywords: Set of keywords to match against

        Returns:
            Match score from 0.0 to 1.0
        """
        if not normalized_input or not keywords:
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

            # Substring match (only for multi-word keywords)
            # For short single-word inputs, require length match to avoid matching "no" in "bueno"
            if len(keyword) >= MIN_KEYWORD_LENGTH and len(normalized_input) >= MIN_KEYWORD_LENGTH:
                if keyword in normalized_input or normalized_input in keyword:
                    # For longer keywords, substring match is very confident
                    return 1.0

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
