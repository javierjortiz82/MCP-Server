#!/usr/bin/env python3
"""Test Booking Agent Modular Prompts System.

This test suite validates:
1. Base booking template loads correctly
2. Modular system includes all required sections
3. A/B test parameter injection (show_pre_confirmation_summary)

Author: Lab01-MCP Team
Created: 2025-10-11
"""

import sys
from pathlib import Path

# Add agent/src to path
agent_src = Path(__file__).parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent.prompt_manager import PromptManager


def test_booking_base_template_loads():
    """Test that booking base template loads correctly."""
    print("\n" + "=" * 80)
    print("TEST 1: Booking Base Template Loading")
    print("=" * 80)

    manager = PromptManager()

    # Get booking prompt (default version v1.0)
    prompt = manager.get_booking_prompt()

    # Validations
    checks = [
        ("Prompt is not empty", len(prompt) > 0),
        ("Contains booking identity", "RESERVAS Y CITAS" in prompt),
        ("Contains services section", "SERVICIOS DISPONIBLES" in prompt),
        ("Contains conversation flow", "FLUJO DE CONVERSACIÓN" in prompt),
        ("Contains data requirements", "DATOS REQUERIDOS PARA RESERVAR" in prompt),
        ("Contains rules section", "REGLAS IMPORTANTES" in prompt),
        ("Reasonable length (>500 chars)", len(prompt) > 500),
    ]

    print(f"\nPrompt length: {len(prompt)} characters")
    print("\nValidations:")

    all_passed = True
    for check_name, result in checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            all_passed = False

    if all_passed:
        print("\n✅ TEST 1 PASSED: Base template loads correctly")
    else:
        print("\n❌ TEST 1 FAILED: Some validations failed")
        raise AssertionError("Base template validation failed")

    return prompt


def test_booking_modular_system():
    """Test that modular system includes all required sections."""
    print("\n" + "=" * 80)
    print("TEST 2: Booking Modular System Structure")
    print("=" * 80)

    manager = PromptManager()

    # Get booking prompt with default parameters
    prompt = manager.get_booking_prompt()

    # Check for all module sections
    required_sections = {
        "Identity": "asistente especializado en RESERVAS",
        "Services": "SERVICIOS DISPONIBLES",
        "Conversation Flow": "FLUJO DE CONVERSACIÓN",
        "Create Booking": "Si el cliente quiere RESERVAR",
        "Cancel Booking": "Si quiere CANCELAR",
        "Reschedule": "Si quiere REPROGRAMAR",
        "Data Requirements": "DATOS REQUERIDOS PARA RESERVAR",
        "Rules": "REGLAS IMPORTANTES",
        "Response Format": "FORMATO DE RESPUESTAS",
    }

    print("\nChecking for required sections:")

    all_sections_present = True
    for section_name, expected_text in required_sections.items():
        present = expected_text in prompt
        status = "✅" if present else "❌"
        print(f"  {status} {section_name}: {expected_text[:50]}...")
        if not present:
            all_sections_present = False

    if all_sections_present:
        print("\n✅ TEST 2 PASSED: All modular sections present")
    else:
        print("\n❌ TEST 2 FAILED: Some sections missing")
        raise AssertionError("Modular system validation failed")


def test_booking_ab_parameter_injection():
    """Test A/B parameter injection (show_pre_confirmation_summary)."""
    print("\n" + "=" * 80)
    print("TEST 3: A/B Test Parameter Injection")
    print("=" * 80)

    manager = PromptManager()

    # Test Variant A (v1.0): Direct confirmation
    print("\n📋 Testing Variant A (v1.0): Direct confirmation")
    prompt_v1_0 = manager.get_booking_prompt(version="v1.0", show_pre_confirmation_summary=False)

    # Test Variant B (v1.1): Pre-confirmation summary
    print("📋 Testing Variant B (v1.1): Pre-confirmation summary")
    prompt_v1_1 = manager.get_booking_prompt(version="v1.1", show_pre_confirmation_summary=True)

    # Validations
    print("\nVariant A (Direct Confirmation) validations:")
    variant_a_checks = [
        ("Contains basic flow", "Crea la reserva usando create_booking" in prompt_v1_0),
        ("Does NOT contain summary block", "RESUMEN DE RESERVA" not in prompt_v1_0),
    ]

    variant_a_passed = True
    for check_name, result in variant_a_checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            variant_a_passed = False

    print("\nVariant B (Pre-Confirmation Summary) validations:")
    variant_b_checks = [
        ("Contains summary block", "RESUMEN DE RESERVA" in prompt_v1_1),
        ("Contains confirmation prompt", "¿Todos los datos son correctos?" in prompt_v1_1),
        ("Contains edit option", "permite editar datos" in prompt_v1_1),
        ("Contains formatted summary", "👤 Cliente:" in prompt_v1_1),
    ]

    variant_b_passed = True
    for check_name, result in variant_b_checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            variant_b_passed = False

    # Check that prompts are different
    print("\nDifference validation:")
    prompts_different = prompt_v1_0 != prompt_v1_1
    status = "✅ PASS" if prompts_different else "❌ FAIL"
    print(f"  {status}: Variant A and B prompts are different")

    # Summary
    all_passed = variant_a_passed and variant_b_passed and prompts_different

    if all_passed:
        print("\n✅ TEST 3 PASSED: A/B parameter injection working correctly")
        print(f"\n📊 Prompt size difference: {len(prompt_v1_1) - len(prompt_v1_0)} chars")
        print(f"   Variant A: {len(prompt_v1_0)} chars")
        print(f"   Variant B: {len(prompt_v1_1)} chars")
    else:
        print("\n❌ TEST 3 FAILED: A/B parameter validation failed")
        raise AssertionError("A/B parameter injection validation failed")


def main():
    """Run all booking modular prompt tests."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  BOOKING AGENT MODULAR PROMPTS TEST SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        # Test 1: Base template loading
        test_booking_base_template_loads()

        # Test 2: Modular system structure
        test_booking_modular_system()

        # Test 3: A/B parameter injection
        test_booking_ab_parameter_injection()

        # Summary
        print("\n" + "=" * 80)
        print("  ✅ ALL TESTS PASSED (3/3)")
        print("=" * 80)
        print("\n✨ Booking Agent modular prompts system is working correctly!")
        print("\nNext steps:")
        print("  1. Test A/B bucketing with user_id")
        print("  2. Run demo to see variants in action")
        print("  3. Enable experiment in production (prompt_versions.yaml)")

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("  ❌ TESTS FAILED")
        print("=" * 80)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
