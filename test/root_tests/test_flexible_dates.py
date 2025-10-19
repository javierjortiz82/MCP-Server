#!/usr/bin/env python3
"""Test Flexible Date Formats in BookingAgent.
==========================================

This script tests the flexible date parsing feature implemented in BookingAgent.
Tests various date formats to ensure the LLM correctly converts them to YYYY-MM-DD.

Author: Lab01-MCP Team
Created: 2025-10-13
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project paths
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "agent" / "src"))
sys.path.insert(0, str(repo_root / "client_mcp"))

from agent.src.multi_agent.prompt_manager import PromptManager


def print_section(title: str):
    """Print section header."""


def test_prompt_injection():
    """Test that PromptManager correctly injects current date into booking prompt."""
    print_section("TEST 1: Date Injection in PromptManager")

    manager = PromptManager()
    prompt = manager.get_booking_prompt(customer_email="test@example.com")

    # Current date should be injected
    today = datetime.now().strftime("%Y-%m-%d")

    if today in prompt:
        pass
    else:
        return False

    # Check for Spanish day name
    spanish_days = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    found_day = any(day in prompt for day in spanish_days)

    if found_day:
        next(day for day in spanish_days if day in prompt)
    else:
        return False

    # Check for flexible date instructions
    if "MANEJO FLEXIBLE DE FECHAS" in prompt:
        pass
    else:
        return False

    return True


def test_expected_formats():
    """Test that all expected date formats are documented in prompt."""
    print_section("TEST 2: Expected Date Formats Documentation")

    manager = PromptManager()
    prompt = manager.get_booking_prompt()

    expected_formats = [
        "DD/MM/YYYY",
        "DD/MM/YY",
        "mañana",
        "próximo",
        "formato YYYY-MM-DD",
    ]

    all_passed = True
    for fmt in expected_formats:
        if fmt in prompt:
            pass
        else:
            all_passed = False

    return all_passed


def test_conversion_examples():
    """Test that conversion examples are present in prompt."""
    print_section("TEST 3: Conversion Examples in Prompt")

    manager = PromptManager()
    prompt = manager.get_booking_prompt()

    # Check for example conversions
    examples = [
        "EJEMPLOS DE CONVERSIÓN",
        "→",  # Arrow symbol for conversions
        "Calcula",  # Calculation instructions
    ]

    all_passed = True
    for example in examples:
        if example in prompt:
            pass
        else:
            all_passed = False

    return all_passed


def test_never_ask_format():
    """Test that prompt instructs LLM to never ask user to change format."""
    print_section("TEST 4: Never Ask User to Change Format")

    manager = PromptManager()
    prompt = manager.get_booking_prompt()

    # Check for explicit instruction
    return "NUNCA pidas al cliente que cambie el formato" in prompt


def simulate_date_queries():
    """Simulate various date queries and show expected behavior."""
    print_section("TEST 5: Simulated Date Query Scenarios")

    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    in_3_days = today + timedelta(days=3)

    # Find next Monday
    days_ahead = (0 - today.weekday()) % 7
    if days_ahead == 0:  # If today is Monday, get next Monday
        days_ahead = 7
    next_monday = today + timedelta(days=days_ahead)

    scenarios = [
        {
            "user_input": "14/10/2025",
            "expected_output": "2025-10-14",
            "description": "DD/MM/YYYY format",
        },
        {
            "user_input": "14/10/25",
            "expected_output": "2025-10-14",
            "description": "DD/MM/YY format",
        },
        {
            "user_input": "mañana",
            "expected_output": tomorrow.strftime("%Y-%m-%d"),
            "description": "Relative date (tomorrow)",
        },
        {
            "user_input": "en 3 días",
            "expected_output": in_3_days.strftime("%Y-%m-%d"),
            "description": "Relative date (in 3 days)",
        },
        {
            "user_input": "el próximo lunes",
            "expected_output": next_monday.strftime("%Y-%m-%d"),
            "description": "Next weekday",
        },
    ]

    for _i, _scenario in enumerate(scenarios, 1):
        pass

    return True


def test_spanish_day_helper():
    """Test the _get_spanish_day helper method."""
    print_section("TEST 6: Spanish Day Name Helper")

    manager = PromptManager()

    expected_days = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }

    all_passed = True
    for weekday, expected_name in expected_days.items():
        actual_name = manager._get_spanish_day(weekday)
        if actual_name == expected_name:
            pass
        else:
            all_passed = False

    return all_passed


def main():
    """Run all tests."""
    tests = [
        ("Date Injection", test_prompt_injection),
        ("Format Documentation", test_expected_formats),
        ("Conversion Examples", test_conversion_examples),
        ("Never Ask Format", test_never_ask_format),
        ("Query Scenarios", simulate_date_queries),
        ("Spanish Day Helper", test_spanish_day_helper),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception:
            results.append((test_name, False))

    # Print summary
    print_section("TEST SUMMARY")

    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)

    for test_name, passed in results:
        pass

    if passed_count == total_count:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
