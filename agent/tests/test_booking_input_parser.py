"""
Test suite for BookingInputParser

Tests flexible input parsing for booking operations.

Author: Lab01-MCP Team
Created: 2025-10-16
"""

import sys
from pathlib import Path

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from multi_agent.booking_input_parser import (
    BookingChoice,
    BookingInputParser,
    parse_booking_choice,
    parse_confirmation,
)


class TestRescheduleKeywordParsing:
    """Test reschedule keyword parsing."""

    def test_reschedule_exact_matches(self):
        """Test exact keyword matches for reschedule."""
        reschedule_inputs = [
            "reprograma",
            "reprogramar",
            "cambiar",
            "modificar",
            "mover",
            "a",
            "1",
        ]

        for user_input in reschedule_inputs:
            choice, confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.RESCHEDULE
            assert confidence >= 0.8, f"Low confidence for '{user_input}'"

    def test_reschedule_with_typos(self):
        """Test reschedule keywords with typos."""
        typo_inputs = [
            "reprogama",  # Missing 'r'
            "caambiar",  # Extra 'a'
            "reporogramar",  # Extra 'o'
        ]

        for user_input in typo_inputs:
            choice, confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.RESCHEDULE
            assert confidence > 0.6, f"Should handle typo in '{user_input}'"

    def test_reschedule_case_insensitive(self):
        """Test case insensitivity."""
        inputs = ["REPROGRAMA", "RePrOgRaM", "Cambiar", "MODIFICAR"]

        for user_input in inputs:
            choice, _confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.RESCHEDULE

    def test_reschedule_with_accents(self):
        """Test accent handling."""
        inputs = ["reprogramá", "cambíar", "modificár"]

        for user_input in inputs:
            choice, _confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.RESCHEDULE


class TestCancelKeywordParsing:
    """Test cancel keyword parsing."""

    def test_cancel_exact_matches(self):
        """Test exact keyword matches for cancel."""
        cancel_inputs = [
            "cancela",
            "cancelar",
            "borrar",
            "eliminar",
            "quitar",
            "b",
            "2",
        ]

        for user_input in cancel_inputs:
            choice, confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.CANCEL
            assert confidence >= 0.8, f"Low confidence for '{user_input}'"

    def test_cancel_with_typos(self):
        """Test cancel keywords with typos."""
        typo_inputs = [
            "canecla",  # Typo
            "borrar",
            "climinar",  # Typo in eliminar
        ]

        for user_input in typo_inputs:
            choice, confidence = parse_booking_choice(user_input)
            assert choice == BookingChoice.CANCEL
            assert confidence > 0.6


class TestConfirmationParsing:
    """Test yes/no confirmation parsing."""

    def test_confirm_inputs(self):
        """Test confirmation inputs."""
        confirm_inputs = ["si", "sí", "yes", "confirmar", "acepto", "ok", "claro"]

        for user_input in confirm_inputs:
            choice, confidence = parse_confirmation(user_input)
            assert choice == BookingChoice.CONFIRM
            assert confidence > 0.7

    def test_deny_inputs(self):
        """Test denial inputs."""
        deny_inputs = ["no", "nope", "cancelar", "negativo", "rechazo"]

        for user_input in deny_inputs:
            choice, confidence = parse_confirmation(user_input)
            assert choice == BookingChoice.DENY
            assert confidence > 0.7


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_input(self):
        """Test empty input handling."""
        choice, confidence = parse_booking_choice("")
        assert choice == BookingChoice.UNKNOWN
        assert confidence == 0.0

    def test_none_input(self):
        """Test None input handling."""
        choice, _confidence = parse_booking_choice("")
        assert choice == BookingChoice.UNKNOWN

    def test_ambiguous_input(self):
        """Test ambiguous input."""
        choice, confidence = parse_booking_choice("maybe")
        assert choice == BookingChoice.UNKNOWN
        assert confidence < 0.6

    def test_spanish_phrases(self):
        """Test Spanish phrases."""
        inputs = [
            ("quiero cambiar mi cita", BookingChoice.RESCHEDULE),
            ("no deseo ir", BookingChoice.CANCEL),
            ("quiero reprogramar", BookingChoice.RESCHEDULE),
        ]

        for user_input, expected_choice in inputs:
            choice, _ = parse_booking_choice(user_input)
            assert choice == expected_choice


class TestNumericAndLetterOptions:
    """Test numeric and letter option parsing."""

    def test_numeric_options(self):
        """Test numeric option parsing."""
        choice_1, _ = parse_booking_choice("1")
        choice_2, _ = parse_booking_choice("2")

        assert choice_1 == BookingChoice.RESCHEDULE
        assert choice_2 == BookingChoice.CANCEL

    def test_letter_options(self):
        """Test letter option parsing."""
        choice_a, _ = parse_booking_choice("A")
        choice_b, _ = parse_booking_choice("B")

        assert choice_a == BookingChoice.RESCHEDULE
        assert choice_b == BookingChoice.CANCEL

    def test_option_with_labels(self):
        """Test option with label text."""
        inputs = [
            ("opcion a", BookingChoice.RESCHEDULE),
            ("opcion b", BookingChoice.CANCEL),
            ("opcion 1", BookingChoice.RESCHEDULE),
            ("opcion 2", BookingChoice.CANCEL),
        ]

        for user_input, expected in inputs:
            choice, confidence = parse_booking_choice(user_input)
            assert choice == expected
            assert confidence == 1.0


class TestNormalization:
    """Test input normalization."""

    def test_accent_removal(self):
        """Test accent removal."""
        parser = BookingInputParser()
        normalized = parser._normalize_input("Reprogramación")
        assert "á" not in normalized
        assert normalized == "reprogramacion"

    def test_punctuation_removal(self):
        """Test punctuation removal."""
        parser = BookingInputParser()
        inputs = ["Reprograma!", "¿Cambiar?", "Cancelar..."]

        for user_input in inputs:
            normalized = parser._normalize_input(user_input)
            assert not any(c in normalized for c in "!?.,")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
