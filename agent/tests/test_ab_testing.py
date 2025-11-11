#!/usr/bin/env python3
"""Test script for A/B Testing infrastructure.

This script tests the A/B testing capabilities of PromptManager,
including version selection, user bucketing, and parameter injection.

Usage:
    python test_ab_testing.py
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from multi_agent.prompt_manager import PromptManager


def test_ab_testing_disabled():
    """Test that when A/B testing is disabled, default version is used."""
    print("=" * 80)
    print("TEST 1: A/B Testing Disabled (Default Behavior)")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Verify A/B testing is disabled
        ab_config = manager.config.get("ab_testing", {})
        is_enabled = ab_config.get("enabled", False)

        print(f"\n✅ A/B testing enabled: {is_enabled}")
        print(f"✅ Active sales version: {manager.config['active_versions']['sales']}")

        # Test with user_id (should still use default since AB testing disabled)
        prompt = manager.get_sales_prompt(user_id="test_user_123", mcp_tools=None)

        # Should use default pagination (4)
        checks = [
            ("Prompt rendered", len(prompt) > 0),
            ("Default pagination", "4" in prompt),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_version_selector():
    """Test the _select_ab_test_version method."""
    print("\n" + "=" * 80)
    print("TEST 2: Version Selector Logic")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Test with A/B testing disabled
        version, pagination = manager._select_ab_test_version(
            agent="sales", user_id="test_user_123"
        )

        print(f"\n✅ Selected version: {version}")
        print(f"✅ Selected pagination: {pagination}")

        checks = [
            ("Version is v1.0 (default)", version == "v1.0"),
            ("Pagination is 4 (default)", pagination == 4),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_experiment_config_loading():
    """Test loading experiment configuration."""
    print("\n" + "=" * 80)
    print("TEST 3: Experiment Configuration Loading")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Get pagination experiment config
        exp = manager.get_experiment_config("sales_pagination_6_products")

        if exp:
            print(f"\n✅ Experiment found: {exp['name']}")
            print(f"✅ Description: {exp['description']}")
            print(f"✅ Agent: {exp['agent']}")
            print(f"✅ Enabled: {exp['enabled']}")
            print(f"✅ Traffic split: {exp['traffic_split']}")
            print(
                f"✅ Version A: {exp['version_a']} (pagination: {exp['version_a_params']['pagination_page_size']})"
            )
            print(
                f"✅ Version B: {exp['version_b']} (pagination: {exp['version_b_params']['pagination_page_size']})"
            )

            checks = [
                ("Experiment found", exp is not None),
                ("Correct agent", exp["agent"] == "sales"),
                ("Has version_a", "version_a" in exp),
                ("Has version_b", "version_b" in exp),
                ("Has traffic_split", "traffic_split" in exp),
                ("Version A pagination is 4", exp["version_a_params"]["pagination_page_size"] == 4),
                ("Version B pagination is 6", exp["version_b_params"]["pagination_page_size"] == 6),
            ]

            print("\nChecks:")
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"  {status} {check_name}")

            all_passed = all(result for _, result in checks)
            return all_passed
        else:
            print("❌ Experiment 'sales_pagination_6_products' not found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ab_testing_enabled_simulation():
    """Test A/B testing enabled scenario (simulation)."""
    print("\n" + "=" * 80)
    print("TEST 4: A/B Testing Enabled (Simulation)")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Simulate enabling A/B testing by modifying config
        print("\nSimulating A/B test enabled...")
        original_config = manager.config.copy()

        # Enable A/B testing temporarily
        manager.config["ab_testing"]["enabled"] = True
        manager.config["ab_testing"]["experiments"][0]["enabled"] = True

        print(f"✅ A/B testing enabled: {manager.config['ab_testing']['enabled']}")
        print(f"✅ Experiment enabled: {manager.config['ab_testing']['experiments'][0]['enabled']}")

        # Test with multiple users (should bucket into variants)
        test_users = ["user_1", "user_2", "user_3", "user_4", "user_5"]
        results = {}

        for user_id in test_users:
            version, pagination = manager._select_ab_test_version(agent="sales", user_id=user_id)
            results[user_id] = {
                "version": version,
                "pagination": pagination,
                "variant": "A" if version == "v1.0" else "B",
            }

        print("\nUser Bucketing Results:")
        for user_id, result in results.items():
            print(f"  {user_id}: {result['variant']} (pagination={result['pagination']})")

        # Count variants
        variant_a_count = sum(1 for r in results.values() if r["variant"] == "A")
        variant_b_count = sum(1 for r in results.values() if r["variant"] == "B")

        print(f"\n✅ Variant A: {variant_a_count} users (4 products)")
        print(f"✅ Variant B: {variant_b_count} users (6 products)")

        checks = [
            ("Both variants used", variant_a_count > 0 and variant_b_count > 0),
            (
                "Variant A has pagination 4",
                all(r["pagination"] == 4 for r in results.values() if r["variant"] == "A"),
            ),
            (
                "Variant B has pagination 6",
                all(r["pagination"] == 6 for r in results.values() if r["variant"] == "B"),
            ),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        # Restore original config
        manager.config = original_config

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_deterministic_bucketing():
    """Test that same user always gets same variant (deterministic)."""
    print("\n" + "=" * 80)
    print("TEST 5: Deterministic User Bucketing")
    print("=" * 80)

    try:
        manager = PromptManager()

        # Enable A/B testing
        manager.config["ab_testing"]["enabled"] = True
        manager.config["ab_testing"]["experiments"][0]["enabled"] = True

        # Test same user multiple times
        user_id = "consistent_user_123"
        results = []

        for i in range(5):
            version, pagination = manager._select_ab_test_version(agent="sales", user_id=user_id)
            results.append((version, pagination))

        print(f"\n✅ User '{user_id}' tested 5 times:")
        for i, (version, pagination) in enumerate(results, 1):
            print(f"  Attempt {i}: version={version}, pagination={pagination}")

        # All results should be identical
        all_same = all(r == results[0] for r in results)

        checks = [
            ("All results identical (deterministic)", all_same),
            ("Consistent version", len({r[0] for r in results}) == 1),
            ("Consistent pagination", len({r[1] for r in results}) == 1),
        ]

        print("\nChecks:")
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")

        all_passed = all(result for _, result in checks)
        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all A/B testing tests."""
    print("\n" + "=" * 80)
    print("A/B TESTING INFRASTRUCTURE - TEST SUITE")
    print("Testing version selection, user bucketing, and parameter injection")
    print("=" * 80)

    results = []

    # Run tests
    results.append(("A/B Testing Disabled", test_ab_testing_disabled()))
    results.append(("Version Selector", test_version_selector()))
    results.append(("Experiment Config Loading", test_experiment_config_loading()))
    results.append(("A/B Testing Enabled", test_ab_testing_enabled_simulation()))
    results.append(("Deterministic Bucketing", test_deterministic_bucketing()))

    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL TESTS PASSED - A/B testing infrastructure ready!")
        print("\nTo enable A/B testing in production:")
        print("1. Edit prompts/config/prompt_versions.yaml")
        print("2. Set ab_testing.enabled: true")
        print("3. Set sales_pagination_6_products.enabled: true")
        print("4. Monitor metrics and adjust traffic_split as needed")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
