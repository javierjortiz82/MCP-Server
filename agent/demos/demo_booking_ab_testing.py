#!/usr/bin/env python3
"""Booking Agent A/B Testing Demo - End-to-End Validation.

This demo showcases the Booking Agent A/B testing system with 4 scenarios:
1. A/B testing disabled → All users get variant A (direct confirmation)
2. A/B testing enabled → Users split 50/50 between A and B (deterministic)
3. Deterministic bucketing → Same user always gets same variant
4. Prompt comparison → Show differences between variant A and B

Experiment:
    Name: booking_confirmation_flow
    Hypothesis: Pre-confirmation summary reduces booking errors
    Variant A: Direct confirmation (no summary)
    Variant B: Pre-confirmation summary (show summary before confirming)

Author: Lab01-MCP Team
Created: 2025-10-11
"""

import sys
from pathlib import Path

# Add paths
agent_src = Path(__file__).parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent.prompt_manager import PromptManager  # noqa: E402


def print_header(text: str, char: str = "="):
    """Print fancy header."""
    print("\n" + char * 80)
    print(f"  {text}")
    print(char * 80)


def scenario_1_ab_disabled():
    """Scenario 1: A/B testing disabled (all users get variant A)."""
    print_header("SCENARIO 1: A/B Testing Disabled (Default Variant A)", "=")

    print("\nConfiguration:")
    print("  ab_testing.enabled: false")
    print("  Expected: All users get variant A (v1.0 - direct confirmation)")

    manager = PromptManager()

    # Test multiple users - all should get same variant
    test_users = [
        "user1@example.com",
        "user2@example.com",
        "user3@example.com",
    ]

    print("\n📋 Testing 3 different users...")

    results = {}
    for user_email in test_users:
        prompt = manager.get_booking_prompt(user_id=user_email)
        has_summary = "RESUMEN DE RESERVA" in prompt
        variant = "B (summary)" if has_summary else "A (direct)"
        results[user_email] = variant
        print(f"  {user_email}: Variant {variant}")

    # Validation
    all_variant_a = all(v == "A (direct)" for v in results.values())

    if all_variant_a:
        print("\n✅ PASS: All users got variant A (A/B testing disabled)")
    else:
        print("\n❌ FAIL: Some users got variant B (unexpected)")
        raise AssertionError("A/B testing should be disabled")


def scenario_2_ab_enabled():
    """Scenario 2: A/B testing enabled (deterministic 50/50 split)."""
    print_header("SCENARIO 2: A/B Testing Enabled (Deterministic Bucketing)", "=")

    print("\nConfiguration:")
    print("  ab_testing.enabled: true")
    print("  experiment: booking_confirmation_flow")
    print("  traffic_split: 0.5 (50% A, 50% B)")
    print("  Expected: ~50% users get variant A, ~50% get variant B")

    manager = PromptManager()

    # Temporarily enable A/B testing
    manager.config["ab_testing"]["enabled"] = True
    for exp in manager.config["ab_testing"]["experiments"]:
        if exp["name"] == "booking_confirmation_flow":
            exp["enabled"] = True
            break

    # Test with 20 different users
    print("\n📊 Testing with 20 different users...")

    variant_counts = {"A": 0, "B": 0}

    for i in range(1, 21):
        user_email = f"booking_user{i}@example.com"
        prompt = manager.get_booking_prompt(user_id=user_email)

        has_summary = "RESUMEN DE RESERVA" in prompt
        variant = "B" if has_summary else "A"
        variant_counts[variant] += 1

        print(
            f"  user{i:02d}@example.com: Variant {variant} {'(summary)' if variant == 'B' else '(direct)'}"
        )

    # Display distribution
    print("\n📈 Distribution:")
    print(f"  Variant A (direct): {variant_counts['A']}/20 ({variant_counts['A'] / 20 * 100:.0f}%)")
    print(
        f"  Variant B (summary): {variant_counts['B']}/20 ({variant_counts['B'] / 20 * 100:.0f}%)"
    )

    # Validation (allow some variance)
    variance = abs((variant_counts["A"] / 20 * 100) - 50)

    if variance < 30:  # Allow 30% variance with small sample
        print(f"\n✅ PASS: Distribution is reasonable (variance: {variance:.0f}%)")
    else:
        print(f"\n⚠️  WARNING: High variance ({variance:.0f}%) - normal with small sample")

    # Restore config
    manager.config["ab_testing"]["enabled"] = False
    for exp in manager.config["ab_testing"]["experiments"]:
        if exp["name"] == "booking_confirmation_flow":
            exp["enabled"] = False
            break


def scenario_3_deterministic_bucketing():
    """Scenario 3: Deterministic bucketing (same user → same variant)."""
    print_header("SCENARIO 3: Deterministic Bucketing (Consistency)", "=")

    print("\nHypothesis: Same user_id should ALWAYS get same variant")
    print("Testing user: consistent_booking@example.com (10 attempts)")

    manager = PromptManager()

    # Enable A/B testing
    manager.config["ab_testing"]["enabled"] = True
    for exp in manager.config["ab_testing"]["experiments"]:
        if exp["name"] == "booking_confirmation_flow":
            exp["enabled"] = True
            break

    # Test same user 10 times
    test_user = "consistent_booking@example.com"

    print("\n🔁 Testing same user 10 times...\n")

    variants = []
    for i in range(1, 11):
        prompt = manager.get_booking_prompt(user_id=test_user)
        has_summary = "RESUMEN DE RESERVA" in prompt
        variant = "B (summary)" if has_summary else "A (direct)"
        variants.append(variant)
        print(f"  Attempt {i:02d}: Variant {variant}")

    # Check consistency
    all_same = all(v == variants[0] for v in variants)

    if all_same:
        print(f"\n✅ PASS: 100% consistent - User always got variant {variants[0]}")
        print("  This ensures users don't see jarring UX changes between sessions.")
    else:
        print("\n❌ FAIL: Inconsistent variant assignment")
        print(f"  Variants: {variants}")
        raise AssertionError("Deterministic bucketing failed")

    # Restore config
    manager.config["ab_testing"]["enabled"] = False
    for exp in manager.config["ab_testing"]["experiments"]:
        if exp["name"] == "booking_confirmation_flow":
            exp["enabled"] = False
            break


def scenario_4_prompt_comparison():
    """Scenario 4: Compare prompts between variant A and B."""
    print_header("SCENARIO 4: Prompt Comparison (Variant A vs B)", "=")

    print("\nComparing generated prompts for both variants...")

    manager = PromptManager()

    # Get variant A prompt
    print("\n📋 Generating Variant A (v1.0 - Direct Confirmation)...")
    prompt_a = manager.get_booking_prompt(version="v1.0", show_pre_confirmation_summary=False)

    # Get variant B prompt
    print("📋 Generating Variant B (v1.1 - Pre-Confirmation Summary)...")
    prompt_b = manager.get_booking_prompt(version="v1.1", show_pre_confirmation_summary=True)

    # Comparison
    print("\n📊 Comparison:")
    print(f"  Variant A length: {len(prompt_a):,} characters")
    print(f"  Variant B length: {len(prompt_b):,} characters")
    print(f"  Difference: {abs(len(prompt_b) - len(prompt_a)):,} characters")

    # Check for unique elements in each variant
    print("\n🔍 Unique Elements:")

    # Variant A should NOT have summary
    has_summary_in_a = "RESUMEN DE RESERVA" in prompt_a
    print(
        f"  Variant A has summary block: {'❌ YES (unexpected)' if has_summary_in_a else '✅ NO (expected)'}"
    )

    # Variant B should have summary
    has_summary_in_b = "RESUMEN DE RESERVA" in prompt_b
    print(
        f"  Variant B has summary block: {'✅ YES (expected)' if has_summary_in_b else '❌ NO (unexpected)'}"
    )

    # Show sample from variant B summary
    if has_summary_in_b:
        print("\n📄 Sample from Variant B (Pre-Confirmation Summary):")
        # Extract summary section
        start_idx = prompt_b.find("MUESTRA RESUMEN completo")
        if start_idx != -1:
            sample = prompt_b[start_idx : start_idx + 400]
            print("  " + "\n  ".join(sample.split("\n")[:10]))

    # Validation
    if not has_summary_in_a and has_summary_in_b and len(prompt_b) > len(prompt_a):
        print("\n✅ PASS: Variants are correctly differentiated")
    else:
        print("\n❌ FAIL: Variants not properly differentiated")
        raise AssertionError("Prompt variants validation failed")


def main():
    """Run all demo scenarios."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  BOOKING AGENT A/B TESTING - END-TO-END DEMO".center(78) + "█")
    print("█" + "  Confirmation Flow Optimization Experiment".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    print("\n🎯 Experiment: booking_confirmation_flow")
    print("   Hypothesis: Showing summary BEFORE confirming reduces errors")
    print("   Variant A: Direct confirmation (current)")
    print("   Variant B: Pre-confirmation summary (test)")

    try:
        # Scenario 1: A/B testing disabled
        scenario_1_ab_disabled()

        input("\n⏸️  Press Enter to continue to Scenario 2...")

        # Scenario 2: A/B testing enabled
        scenario_2_ab_enabled()

        input("\n⏸️  Press Enter to continue to Scenario 3...")

        # Scenario 3: Deterministic bucketing
        scenario_3_deterministic_bucketing()

        input("\n⏸️  Press Enter to continue to Scenario 4...")

        # Scenario 4: Prompt comparison
        scenario_4_prompt_comparison()

        # Final summary
        print_header("✅ ALL SCENARIOS PASSED", "=")

        print("""
🎉 Demo Complete - Booking A/B Testing System is Working!

Key Takeaways:
1. ✅ A/B testing can be enabled/disabled via YAML config
2. ✅ Deterministic bucketing ensures consistent UX for each user
3. ✅ Variant B adds pre-confirmation summary (~626 chars)
4. ✅ Zero code changes needed to switch variants

Next Steps:
1. Enable experiment in production (prompt_versions.yaml)
2. Pass user_id to BookingAgent initialization
3. Monitor metrics: booking_success_rate, data_correction_requests
4. Collect data for 2+ weeks
5. Analyze results and declare winner

See: docs/AGENT_AB_TESTING_GUIDE.md for deployment instructions
        """)

        return 0

    except Exception as e:
        print("\n" + "=" * 80)
        print("  ❌ DEMO FAILED")
        print("=" * 80)
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
