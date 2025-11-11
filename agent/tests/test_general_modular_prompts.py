#!/usr/bin/env python3
"""Test General Agent Modular Prompts System.

This test suite validates:
1. Base general template loads correctly
2. Modular system includes all required sections
3. A/B test parameter injection (response_detail_level)

Author: Lab01-MCP Team
Created: 2025-10-11
"""

import sys
from pathlib import Path

# Add agent/src to path
agent_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent.prompt_manager import PromptManager


def test_general_base_template_loads():
    """Test that general base template loads correctly."""
    print("\n" + "=" * 80)
    print("TEST 1: General Base Template Loading")
    print("=" * 80)

    manager = PromptManager()

    # Get general prompt (default version v1.0)
    prompt = manager.get_general_prompt()

    # Validations
    checks = [
        ("Prompt is not empty", len(prompt) > 0),
        ("Contains general identity", "información general" in prompt),
        ("Contains business info", "INFORMACIÓN DE LA EMPRESA" in prompt),
        ("Contains hours", "HORARIOS DE ATENCIÓN" in prompt),
        ("Contains payment methods", "MÉTODOS DE PAGO" in prompt),
        ("Contains shipping", "ENVÍOS Y ENTREGA" in prompt),
        ("Contains returns", "POLÍTICAS DE DEVOLUCIÓN" in prompt),
        ("Contains warranty", "GARANTÍA" in prompt),
        ("Contains contact", "SOPORTE Y CONTACTO" in prompt),
        ("Contains tone/style", "TONO Y ESTILO" in prompt),
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


def test_general_modular_system():
    """Test that modular system includes all required sections."""
    print("\n" + "=" * 80)
    print("TEST 2: General Modular System Structure")
    print("=" * 80)

    manager = PromptManager()

    # Get general prompt with default parameters
    prompt = manager.get_general_prompt()

    # Check for all module sections
    required_sections = {
        "Identity": "asistente de información general",
        "Business Info": "INFORMACIÓN DE LA EMPRESA",
        "Hours": "HORARIOS DE ATENCIÓN",
        "Contact": "SOPORTE Y CONTACTO",
        "Payment Methods": "MÉTODOS DE PAGO",
        "Shipping": "ENVÍOS Y ENTREGA",
        "Returns": "POLÍTICAS DE DEVOLUCIÓN",
        "Warranty": "GARANTÍA",
        "Redirection": "REDIRECCIÓN A OTROS AGENTES",
        "Tone and Style": "TONO Y ESTILO",
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


def test_general_ab_parameter_injection():
    """Test A/B parameter injection (response_detail_level)."""
    print("\n" + "=" * 80)
    print("TEST 3: A/B Test Parameter Injection")
    print("=" * 80)

    manager = PromptManager()

    # Test Variant A (v1.0): Detailed responses
    print("\n📋 Testing Variant A (v1.0): Detailed responses")
    prompt_v1_0 = manager.get_general_prompt(version="v1.0", response_detail_level="detailed")

    # Test Variant B (v1.1): Concise responses
    print("📋 Testing Variant B (v1.1): Concise responses")
    prompt_v1_1 = manager.get_general_prompt(version="v1.1", response_detail_level="concise")

    # Validations
    print("\nVariant A (Detailed) validations:")
    variant_a_checks = [
        ("Contains detailed style marker", "Amigable y profesional" in prompt_v1_0),
        (
            "Contains multiple examples",
            "Pregunta:" in prompt_v1_0 and prompt_v1_0.count("Respuesta:") >= 2,
        ),
        ("Contains help offer", "algo más en lo que pueda asistirte" in prompt_v1_0),
        ("Does NOT contain concise marker", "CONCISO y DIRECTO" not in prompt_v1_0),
    ]

    variant_a_passed = True
    for check_name, result in variant_a_checks:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not result:
            variant_a_passed = False

    print("\nVariant B (Concise) validations:")
    variant_b_checks = [
        ("Contains concise style marker", "Profesional y directo" in prompt_v1_1),
        ("Contains concise instruction", "CONCISO y DIRECTO" in prompt_v1_1),
        ("Has fewer examples", prompt_v1_1.count("Respuesta:") <= 1),
        (
            "Does NOT contain detailed elaboration",
            "algo más en lo que pueda asistirte" not in prompt_v1_1,
        ),
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
        print(f"\n📊 Prompt size difference: {abs(len(prompt_v1_1) - len(prompt_v1_0))} chars")
        print(f"   Variant A (detailed): {len(prompt_v1_0)} chars")
        print(f"   Variant B (concise): {len(prompt_v1_1)} chars")
    else:
        print("\n❌ TEST 3 FAILED: A/B parameter validation failed")
        raise AssertionError("A/B parameter injection validation failed")


def main():
    """Run all general modular prompt tests."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  GENERAL AGENT MODULAR PROMPTS TEST SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    try:
        # Test 1: Base template loading
        test_general_base_template_loads()

        # Test 2: Modular system structure
        test_general_modular_system()

        # Test 3: A/B parameter injection
        test_general_ab_parameter_injection()

        # Summary
        print("\n" + "=" * 80)
        print("  ✅ ALL TESTS PASSED (3/3)")
        print("=" * 80)
        print("\n✨ General Agent modular prompts system is working correctly!")
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
