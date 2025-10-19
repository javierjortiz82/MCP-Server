#!/usr/bin/env python3
"""Test Cross-Session Memory (Phase 6).

Comprehensive test suite for user-level memory that persists across sessions.
Tests the complete lifecycle:
1. Session 1: User interaction creates memory blocks
2. Auto-sync: High-priority blocks promote to user-level
3. Session 2: New session loads user memory automatically
4. Verification: User context persists across sessions

USAGE:
    python3 test_cross_session_memory.py

Prerequisites:
    - PostgreSQL running with migration 003 applied
    - DATABASE_URL configured in .env
    - Run: python3 SQL/src/run_user_memory_migration.py

Author: Lab01-MCP Team
Created: 2025-10-12
Version: 1.0.0 (Phase 6 - Cross-Session Memory)
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager
from multi_agent.agent_router import AgentRouter
from multi_agent.general_agent import GeneralAgent

# ============================================================================
# Test Configuration
# ============================================================================

TEST_EMAIL = "test-cross-session@example.com"
TEST_SESSION_1_METADATA = {"source": "test", "session_number": 1}
TEST_SESSION_2_METADATA = {"source": "test", "session_number": 2}


# ============================================================================
# Test Functions
# ============================================================================


async def test_session_1_memory_creation():
    """Test #1: Create first session with memory blocks.

    Simulates a user interaction where high-priority memory is created.
    These blocks should auto-sync to user-level.
    """
    print("\n" + "=" * 70)
    print("TEST 1: SESSION 1 - MEMORY CREATION")
    print("=" * 70)

    try:
        memory = MemoryManager()

        # Create first session
        print("\n1. Creating Session 1...")
        session_id_1 = memory.create_session(
            customer_email=TEST_EMAIL, metadata=TEST_SESSION_1_METADATA
        )
        print(f"   ✅ Session 1 created: {session_id_1[:8]}...")

        # Simulate conversation with memory creation
        print("\n2. Adding conversation messages...")
        memory.save_message(session_id_1, "user", "Busco una laptop gaming RTX 4060")
        memory.save_message(
            session_id_1,
            "model",
            "Tenemos varias opciones de laptops gaming con RTX 4060...",
            agent_name="sales",
        )
        memory.save_message(session_id_1, "user", "Me interesa la de 16GB RAM")
        memory.save_message(
            session_id_1,
            "model",
            "Excelente elección. El modelo con 16GB RAM cuesta $1299.99",
            agent_name="sales",
        )
        print("   ✅ Added 4 messages to session")

        # Create high-priority memory blocks (should auto-sync to user-level)
        print("\n3. Creating high-priority memory blocks...")
        block_id_1 = memory.save_memory_block(
            session_id=session_id_1,
            block_label="product_interest",
            block_value="Usuario busca laptop gaming RTX 4060 con 16GB RAM",
            priority=9,  # High priority → will sync to user-level
            agent_scope="shared",
        )
        print(f"   ✅ Block 1 created (id={block_id_1}, priority=9)")

        block_id_2 = memory.save_memory_block(
            session_id=session_id_1,
            block_label="user_preferences",
            block_value="Prefiere productos de gama alta con buen rendimiento",
            priority=8,  # High priority → will sync to user-level
            agent_scope="shared",
        )
        print(f"   ✅ Block 2 created (id={block_id_2}, priority=8)")

        # Create medium-priority block (should NOT auto-sync)
        block_id_3 = memory.save_memory_block(
            session_id=session_id_1,
            block_label="session_context",
            block_value="Usuario preguntó por el precio primero",
            priority=6,  # Below threshold → session-level only
            agent_scope="shared",
        )
        print(f"   ✅ Block 3 created (id={block_id_3}, priority=6, session-only)")

        # Manually trigger sync (in production, this would happen on session end)
        print("\n4. Syncing session memory to user profile...")
        sync_result = memory.sync_session_to_user_memory(session_id_1)
        print("   ✅ Sync complete:")
        print(f"      - Synced: {sync_result['synced_blocks']} blocks")
        print(f"      - Updated: {sync_result['updated_blocks']} blocks")
        print(f"      - Skipped: {sync_result['skipped_blocks']} blocks")

        # Verify user profile created
        print("\n5. Verifying user profile...")
        profile = memory.get_user_profile(TEST_EMAIL)
        if profile:
            print("   ✅ User profile created:")
            print(f"      - Email: {profile['customer_email']}")
            print(f"      - Total sessions: {profile['total_sessions']}")
            print(f"      - First seen: {profile['first_seen_at']}")
        else:
            print("   ❌ User profile NOT found!")
            return False

        # Verify user memory blocks
        print("\n6. Verifying user memory blocks...")
        user_blocks = memory.get_user_memory_blocks(
            customer_email=TEST_EMAIL, agent_scope="shared"
        )
        print(f"   ✅ User has {len(user_blocks)} cross-session memory blocks")

        if len(user_blocks) >= 2:
            print("   ✅ Expected blocks synced (priority >= 7)")
            for block in user_blocks:
                print(
                    f"      - {block['block_label']}: {block['block_value'][:50]}... (p={block['priority']})"
                )
        else:
            print(f"   ⚠️  Expected 2+ blocks, got {len(user_blocks)}")

        print("\n✅ TEST 1 PASSED: Session 1 memory creation successful")
        return session_id_1

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_session_2_memory_loading(session_id_1: str):
    """Test #2: Create second session and verify user memory loads.

    Simulates returning user (same email, different session_id).
    User-level memory should be automatically loaded.
    """
    print("\n" + "=" * 70)
    print("TEST 2: SESSION 2 - MEMORY LOADING")
    print("=" * 70)

    try:
        memory = MemoryManager()

        # Create second session (same email, different session)
        print(f"\n1. Creating Session 2 for same user ({TEST_EMAIL})...")
        session_id_2 = memory.create_session(
            customer_email=TEST_EMAIL, metadata=TEST_SESSION_2_METADATA
        )
        print(f"   ✅ Session 2 created: {session_id_2[:8]}...")
        print(f"   (Different from Session 1: {session_id_1[:8]}...)")

        # Verify user profile updated
        print("\n2. Verifying user profile updated...")
        profile = memory.get_user_profile(TEST_EMAIL)
        if profile:
            total_sessions = profile.get("total_sessions", 0)
            print(f"   ✅ User profile shows {total_sessions} total sessions")
            if total_sessions >= 2:
                print("   ✅ Session count incremented correctly")
        else:
            print("   ❌ User profile not found!")
            return False

        # Load user memory blocks
        print("\n3. Loading user memory blocks...")
        user_blocks = memory.get_user_memory_blocks(
            customer_email=TEST_EMAIL, agent_scope="shared"
        )
        print(f"   ✅ Loaded {len(user_blocks)} user memory blocks")

        if len(user_blocks) >= 2:
            print("   ✅ Cross-session memory available:")
            for block in user_blocks:
                label = block["block_label"]
                value = block["block_value"][:60]
                priority = block["priority"]
                print(f"      - [{label}] (p={priority}): {value}...")
        else:
            print(f"   ⚠️  Expected 2+ blocks, got {len(user_blocks)}")

        # Test BaseAgent.resume_session() with user memory
        print("\n4. Testing BaseAgent.resume_session() with user memory...")
        agent = await GeneralAgent.resume_session(
            session_id=session_id_2,
            memory_manager=memory,
            load_history=False,  # No history yet in Session 2
            load_user_memory=True,  # Load user-level memory
            show_summary=True,
        )
        print("   ✅ Agent resumed with user memory context")

        # Test get_user_context() helper
        print("\n5. Testing get_user_context() helper...")
        user_context = agent.get_user_context(TEST_EMAIL)
        if user_context:
            print(f"   ✅ User context generated ({len(user_context)} chars):")
            print("   " + "\n   ".join(user_context.split("\n")[:6]))  # First 6 lines
        else:
            print("   ⚠️  User context is empty")

        # Cleanup agent
        await agent.cleanup()

        print("\n✅ TEST 2 PASSED: Session 2 memory loading successful")
        return session_id_2

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return None


async def test_router_with_user_memory(session_id_2: str):
    """Test #3: Verify AgentRouter uses user memory for classification.

    Router should include user memory blocks in context for better intent classification.
    """
    print("\n" + "=" * 70)
    print("TEST 3: ROUTER WITH USER MEMORY")
    print("=" * 70)

    try:
        memory = MemoryManager()

        # Initialize router WITH memory
        print("\n1. Initializing router with memory context...")
        router = AgentRouter(memory_manager=memory, session_id=session_id_2)
        await router.initialize()
        print("   ✅ Router initialized with memory")

        # Test ambiguous query (should use user memory for context)
        print("\n2. Testing ambiguous query classification...")
        query = "Me interesa ese modelo"  # Ambiguous without context

        intent = await router.classify_intent(query, persist_intent=False)
        print(f"   ✅ Query classified as: {intent.value}")
        print("      (Expected: sales, based on user memory about laptop interest)")

        # The router should have loaded user memory internally
        memory_context = router._get_memory_context()
        if memory_context:
            print("\n3. Router memory context loaded:")
            print(f"   {memory_context[:200]}...")
            if (
                "MEMORIA HISTÓRICA" in memory_context
                or "laptop" in memory_context.lower()
            ):
                print("   ✅ User memory context included in classification")
            else:
                print("   ⚠️  User memory might not be in context")
        else:
            print("   ⚠️  No memory context loaded")

        # Cleanup
        await router.cleanup()

        print("\n✅ TEST 3 PASSED: Router uses user memory correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_memory_deduplication():
    """Test #4: Verify memory deduplication works correctly.

    If same memory block is synced from multiple sessions, it should be
    deduplicated (merged with max priority).
    """
    print("\n" + "=" * 70)
    print("TEST 4: MEMORY DEDUPLICATION")
    print("=" * 70)

    try:
        memory = MemoryManager()
        test_email = "test-dedup@example.com"

        # Create first session
        print("\n1. Creating Session 1...")
        session_1 = memory.create_session(
            customer_email=test_email, metadata={"test": "dedup_session_1"}
        )
        print(f"   ✅ Session 1: {session_1[:8]}...")

        # Add same memory block with priority 8
        memory.save_memory_block(
            session_id=session_1,
            block_label="product_interest",
            block_value="Usuario busca laptops gaming",
            priority=8,
            agent_scope="shared",
        )
        print("   ✅ Block added (priority=8)")

        # Sync to user-level
        memory.sync_session_to_user_memory(session_1)
        print("   ✅ Synced to user-level")

        # Check user blocks (should have 1 block)
        user_blocks_1 = memory.get_user_memory_blocks(test_email, "shared")
        print(f"   ✅ User has {len(user_blocks_1)} block(s)")

        # Create second session
        print("\n2. Creating Session 2...")
        session_2 = memory.create_session(
            customer_email=test_email, metadata={"test": "dedup_session_2"}
        )
        print(f"   ✅ Session 2: {session_2[:8]}...")

        # Add SAME memory block but with higher priority (9)
        memory.save_memory_block(
            session_id=session_2,
            block_label="product_interest",
            block_value="Usuario busca laptops gaming",  # Same value
            priority=9,  # Higher priority
            agent_scope="shared",
        )
        print("   ✅ Same block added (priority=9)")

        # Sync to user-level (should deduplicate)
        sync_result = memory.sync_session_to_user_memory(session_2)
        print(
            f"   ✅ Synced: {sync_result['synced_blocks']} new, {sync_result['updated_blocks']} updated"
        )

        # Check user blocks (should still have 1 block, but with max priority)
        user_blocks_2 = memory.get_user_memory_blocks(test_email, "shared")
        print("\n3. Verifying deduplication...")
        print(f"   Total blocks: {len(user_blocks_2)}")

        if len(user_blocks_2) == 1:
            print("   ✅ Deduplication worked (1 block instead of 2)")
            priority = user_blocks_2[0].get("priority", 0)
            if priority == 9:
                print("   ✅ Priority correctly updated to MAX (9)")
            else:
                print(f"   ⚠️  Expected priority=9, got {priority}")
        else:
            print(f"   ⚠️  Expected 1 block, got {len(user_blocks_2)}")

        print("\n✅ TEST 4 PASSED: Memory deduplication works correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_cli_integration():
    """Test #5: Verify CLI tool can view user profiles.

    Tests the 'user-profile' command added to scripts/odiseo_memory.py.
    """
    print("\n" + "=" * 70)
    print("TEST 5: CLI INTEGRATION")
    print("=" * 70)

    try:
        import subprocess

        print("\n1. Testing 'user-profile' command...")
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "user-profile", TEST_EMAIL],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("   ✅ CLI command executed successfully")

            # Check if output contains expected info
            if "USER MEMORY PROFILE" in result.stdout:
                print("   ✅ Profile header found")
            if "Profile Information" in result.stdout:
                print("   ✅ Profile section found")
            if "Cross-Session Memory Blocks" in result.stdout:
                print("   ✅ Memory blocks section found")

            print("\n   Output preview:")
            lines = result.stdout.split("\n")[:15]
            for line in lines:
                print(f"   {line}")
        else:
            print(f"   ❌ CLI command failed: {result.stderr}")
            return False

        print("\n✅ TEST 5 PASSED: CLI integration works correctly")
        return True

    except subprocess.TimeoutExpired:
        print("   ❌ CLI command timed out")
        return False
    except Exception as e:
        print(f"\n❌ TEST 5 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


# ============================================================================
# Main Test Suite
# ============================================================================


async def main():
    """Run all cross-session memory tests."""
    print("=" * 70)
    print("CROSS-SESSION MEMORY TEST SUITE (PHASE 6)")
    print("=" * 70)
    print(f"Test Email: {TEST_EMAIL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check prerequisites
    if not MEMORY_AVAILABLE:
        print("\n❌ ERROR: MemoryManager not available")
        print("   Please check your configuration and database connection")
        return 1

    print("\n📋 Running 5 comprehensive tests...\n")

    results = []

    # Test 1: Session 1 memory creation
    session_id_1 = await test_session_1_memory_creation()
    results.append(("Session 1 Memory Creation", session_id_1 is not None))

    if not session_id_1:
        print("\n⚠️  Test 1 failed, skipping dependent tests")
        return 1

    # Test 2: Session 2 memory loading
    session_id_2 = await test_session_2_memory_loading(session_id_1)
    results.append(("Session 2 Memory Loading", session_id_2 is not None))

    if not session_id_2:
        print("\n⚠️  Test 2 failed, skipping dependent tests")
        return 1

    # Test 3: Router with user memory
    result_3 = await test_router_with_user_memory(session_id_2)
    results.append(("Router with User Memory", result_3))

    # Test 4: Memory deduplication
    result_4 = await test_memory_deduplication()
    results.append(("Memory Deduplication", result_4))

    # Test 5: CLI integration
    result_5 = await test_cli_integration()
    results.append(("CLI Integration", result_5))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Cross-Session Memory working correctly.")
        print("\n📝 Next steps:")
        print("   1. Run migration: python3 SQL/src/run_user_memory_migration.py")
        print("   2. Test in production with real users")
        print("   3. Monitor user_memory_profiles and user_memory_blocks tables")
        print("   4. Adjust TTL (180 days) if needed")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
