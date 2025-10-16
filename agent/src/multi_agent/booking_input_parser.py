"""
Booking Input Parser - Flexible User Response Parsing

Parses user responses for booking operations with fuzzy matching:
- Reschedule/Cancel options (A/B, 1/2, keywords, typos)
- Date/Time selections
- Confirmation (Yes/No)
- Service selections

Author: Lab01-MCP Team
Created: 2025-10-16
Version: 1.0
"""

import re
from enum import Enum
from typing import Optional, Tuple
from difflib import SequenceMatcher
import logging

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
        if normalized in {"a", "1", "opcion a", "opcion 1"}:
            return BookingChoice.RESCHEDULE, 1.0

        if normalized in {"b", "2", "opcion b", "opcion 2"}:
            return BookingChoice.CANCEL, 1.0

        # Check keyword matches
        reschedule_score = cls._calculate_match_score(normalized, cls.RESCHEDULE_KEYWORDS)
        cancel_score = cls._calculate_match_score(normalized, cls.CANCEL_KEYWORDS)

        if reschedule_score > cancel_score and reschedule_score > 0.6:
            return BookingChoice.RESCHEDULE, reschedule_score

        if cancel_score > reschedule_score and cancel_score > 0.6:
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

        if confirm_score > deny_score and confirm_score > 0.6:
            return BookingChoice.CONFIRM, confirm_score

        if deny_score > confirm_score and deny_score > 0.6:
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
                best_score = max(best_score, 0.95)
                continue

            # Substring match (only for multi-word keywords)
            # For short single-word inputs, require length match to avoid matching "no" in "bueno"
            if len(keyword) >= 3 and len(normalized_input) >= 3:
                if keyword in normalized_input or normalized_input in keyword:
                    # For longer keywords, substring match is very confident
                    return 1.0

            # Fuzzy match using SequenceMatcher
            score = SequenceMatcher(
                None, normalized_input, keyword
            ).ratio()

            # Only accept fuzzy matches above a threshold
            if score > 0.75:
                best_score = max(best_score, score)

        return best_score

    @classmethod
    def should_show_error(cls, confidence: float, threshold: float = 0.6) -> bool:
        """
        Determine if agent should ask for clarification.

        Args:
            confidence: Confidence score (0.0 to 1.0)
            threshold: Minimum confidence threshold (default: 0.6)

        Returns:
            True if agent should ask for clarification
        """
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
