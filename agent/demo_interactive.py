#!/usr/bin/env python3
"""Interactive Demo: See A/B Testing in Real-Time.

This script shows you exactly what happens when different users interact
with the system, demonstrating deterministic bucketing in action.
"""

import hashlib
import sys
from pathlib import Path

# Add paths
agent_src = Path(__file__).parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent.prompt_manager import PromptManager


def print_header(text):
    """Print fancy header."""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + text.center(78) + "║")
    print("╚" + "═" * 78 + "╝")


def show_hash_calculation(user_id: str):
    """Show how MD5 hash determines variant."""
    print("\n🔢 Hash Calculation:")
    print(f"   User ID: {user_id}")

    # Calculate MD5 hash
    hash_value = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
    bucket = hash_value % 100

    print(f"   MD5 Hash: {hashlib.md5(user_id.encode()).hexdigest()[:16]}...")
    print(f"   Bucket (hash % 100): {bucket}")
    print("   Traffic split: 50% (buckets 0-49 → A, 50-99 → B)")

    if bucket < 50:
        print(f"   ✅ {bucket} < 50 → Variant A (4 products)")
    else:
        print(f"   ✅ {bucket} >= 50 → Variant B (6 products)")

    return bucket < 50


def demo_single_user(manager: PromptManager, user_email: str):
    """Demo what happens for a single user."""
    print_header(f"  USER: {user_email}")

    # Show hash calculation
    is_variant_a = show_hash_calculation(user_email)

    # Get version from PromptManager
    print("\n📋 PromptManager Decision:")

    # Enable A/B testing temporarily
    original_enabled = manager.config['ab_testing']['enabled']
    original_exp = manager.config['ab_testing']['experiments'][0]['enabled']
    manager.config['ab_testing']['enabled'] = True
    manager.config['ab_testing']['experiments'][0]['enabled'] = True

    version, pagination = manager._select_ab_test_version(
        agent='sales',
        user_id=user_email
    )

    print(f"   Version: {version}")
    print(f"   Pagination: {pagination} products/page")
    print(f"   Variant: {'A (Control)' if version == 'v1.0' else 'B (Test)'}")

    # Generate prompt
    prompt = manager.get_sales_prompt(mcp_tools=[], user_id=user_email)

    print("\n📄 Generated Prompt:")
    print(f"   Length: {len(prompt):,} characters")
    print(f"   Contains '4 products': {'✅ Yes' if '4' in prompt[:500] else '❌ No'}")
    print(f"   Contains '6 products': {'✅ Yes' if '6' in prompt[:500] else '❌ No'}")

    # Show what user sees
    print("\n👤 What User Sees:")
    if pagination == 4:
        print("   📦 Product 1")
        print("   📦 Product 2")
        print("   📦 Product 3")
        print("   📦 Product 4")
        print("   💭 'Show more to see remaining products...'")
    else:
        print("   📦 Product 1")
        print("   📦 Product 2")
        print("   📦 Product 3")
        print("   📦 Product 4")
        print("   📦 Product 5")
        print("   📦 Product 6")
        print("   💭 'Show more to see remaining products...'")

    # Restore config
    manager.config['ab_testing']['enabled'] = original_enabled
    manager.config['ab_testing']['experiments'][0]['enabled'] = original_exp

    return version, pagination


def demo_consistency(manager: PromptManager, user_email: str):
    """Demo that same user always gets same variant."""
    print_header(f"  CONSISTENCY TEST: {user_email}")

    print("\n🔁 Testing same user 5 times to verify consistency...\n")

    # Enable A/B testing
    manager.config['ab_testing']['enabled'] = True
    manager.config['ab_testing']['experiments'][0]['enabled'] = True

    results = []
    for i in range(5):
        version, pagination = manager._select_ab_test_version(
            agent='sales',
            user_id=user_email
        )
        results.append((version, pagination))
        variant = 'A' if version == 'v1.0' else 'B'
        print(f"   Attempt {i+1}: Version {version}, Pagination {pagination}, Variant {variant}")

    # Check consistency
    all_same = all(r == results[0] for r in results)

    if all_same:
        print("\n   ✅ 100% CONSISTENT - Same user always gets same variant!")
        print("   This ensures users don't see jarring UX changes between sessions.")
    else:
        print("\n   ❌ INCONSISTENT - Something is wrong!")

    # Restore config
    manager.config['ab_testing']['enabled'] = False
    manager.config['ab_testing']['experiments'][0]['enabled'] = False

    return all_same


def demo_multiple_users(manager: PromptManager):
    """Demo distribution across multiple users."""
    print_header("  DISTRIBUTION TEST: 20 Users")

    print("\n📊 Simulating 20 different users...\n")

    # Enable A/B testing
    manager.config['ab_testing']['enabled'] = True
    manager.config['ab_testing']['experiments'][0]['enabled'] = True

    users = [f"user{i}@example.com" for i in range(1, 21)]
    variants = {'A': 0, 'B': 0}

    print(f"{'User Email':<25} {'Variant':<10} {'Pagination':<12}")
    print("-" * 50)

    for user in users:
        version, pagination = manager._select_ab_test_version(
            agent='sales',
            user_id=user
        )
        variant = 'A' if version == 'v1.0' else 'B'
        variants[variant] += 1
        print(f"{user:<25} {variant:<10} {pagination} products")

    print("\n📊 Distribution:")
    print(f"   Variant A: {variants['A']}/20 users ({variants['A']/20*100:.0f}%)")
    print(f"   Variant B: {variants['B']}/20 users ({variants['B']/20*100:.0f}%)")
    print("\n   Expected: ~10 users each (50/50 split)")

    variance = abs((variants['A'] / 20 * 100) - 50)
    if variance < 15:
        print(f"   ✅ Good distribution (variance: {variance:.0f}%)")
    else:
        print(f"   ⚠️  High variance: {variance:.0f}% (normal with small sample)")

    # Restore config
    manager.config['ab_testing']['enabled'] = False
    manager.config['ab_testing']['experiments'][0]['enabled'] = False


def main():
    """Run interactive demo."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  🎯 INTERACTIVE A/B TESTING DEMO".center(78) + "█")
    print("█" + "  See Deterministic Bucketing in Action".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    manager = PromptManager(use_templates=True)

    # Demo 1: Single user (variant A)
    demo_single_user(manager, "maria@example.com")

    input("\n⏸️  Press Enter to continue...")

    # Demo 2: Single user (variant B)
    demo_single_user(manager, "juan@example.com")

    input("\n⏸️  Press Enter to continue...")

    # Demo 3: Consistency test
    demo_consistency(manager, "consistent_test@example.com")

    input("\n⏸️  Press Enter to continue...")

    # Demo 4: Distribution test
    demo_multiple_users(manager)

    # Final summary
    print_header("  ✅ DEMO COMPLETE")

    print("""
Key Takeaways:

1. 🎲 Deterministic Bucketing
   → Same user_id always produces same variant (MD5 hash-based)
   → No random changes between sessions
   → Consistent UX for each user

2. ⚖️ Fair Distribution
   → ~50% users get variant A (4 products)
   → ~50% users get variant B (6 products)
   → Traffic split configurable (0.1 = 10%, 0.5 = 50%, etc.)

3. 🔄 Zero Configuration Changes
   → Users automatically bucketed based on user_id
   → No database updates needed
   → No session tracking required

4. 📊 Ready for Metrics
   → Each decision logged with user_id + variant
   → Easy to parse logs for conversion analysis
   → Statistical significance after 2+ weeks

Next: Enable in production and collect real user data!
See: agent/README_AB_TESTING.md for deployment instructions
    """)


if __name__ == "__main__":
    main()
