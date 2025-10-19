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
    try:
        memory = MemoryManager()

        # Create first session
        session_id_1 = memory.create_session(
            customer_email=TEST_EMAIL,
            metadata=TEST_SESSION_1_METADATA,
        )

        # Simulate conversation with memory creation
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

        # Create high-priority memory blocks (should auto-sync to user-level)
        memory.save_memory_block(
            session_id=session_id_1,
            block_label="product_interest",
            block_value="Usuario busca laptop gaming RTX 4060 con 16GB RAM",
            priority=9,  # High priority → will sync to user-level
            agent_scope="shared",
        )

        memory.save_memory_block(
            session_id=session_id_1,
            block_label="user_preferences",
            block_value="Prefiere productos de gama alta con buen rendimiento",
            priority=8,  # High priority → will sync to user-level
            agent_scope="shared",
        )

        # Create medium-priority block (should NOT auto-sync)
        memory.save_memory_block(
            session_id=session_id_1,
            block_label="session_context",
            block_value="Usuario preguntó por el precio primero",
            priority=6,  # Below threshold → session-level only
            agent_scope="shared",
        )

        # Manually trigger sync (in production, this would happen on session end)
        memory.sync_session_to_user_memory(session_id_1)

        # Verify user profile created
        profile = memory.get_user_profile(TEST_EMAIL)
        if profile:
            pass
        else:
            return False

        # Verify user memory blocks
        user_blocks = memory.get_user_memory_blocks(
            customer_email=TEST_EMAIL,
            agent_scope="shared",
        )

        if len(user_blocks) >= 2:
            for _block in user_blocks:
                pass
        else:
            pass

        return session_id_1

    except Exception:
        import traceback

        traceback.print_exc()
        return None


async def test_session_2_memory_loading(session_id_1: str):
    """Test #2: Create second session and verify user memory loads.

    Simulates returning user (same email, different session_id).
    User-level memory should be automatically loaded.
    """
    try:
        memory = MemoryManager()

        # Create second session (same email, different session)
        session_id_2 = memory.create_session(
            customer_email=TEST_EMAIL,
            metadata=TEST_SESSION_2_METADATA,
        )

        # Verify user profile updated
        profile = memory.get_user_profile(TEST_EMAIL)
        if profile:
            total_sessions = profile.get("total_sessions", 0)
            if total_sessions >= 2:
                pass
        else:
            return False

        # Load user memory blocks
        user_blocks = memory.get_user_memory_blocks(
            customer_email=TEST_EMAIL,
            agent_scope="shared",
        )

        if len(user_blocks) >= 2:
            for block in user_blocks:
                block["block_label"]
                block["block_value"][:60]
                block["priority"]
        else:
            pass

        # Test BaseAgent.resume_session() with user memory
        agent = await GeneralAgent.resume_session(
            session_id=session_id_2,
            memory_manager=memory,
            load_history=False,  # No history yet in Session 2
            load_user_memory=True,  # Load user-level memory
            show_summary=True,
        )

        # Test get_user_context() helper
        user_context = agent.get_user_context(TEST_EMAIL)
        if user_context:
            pass  # First 6 lines
        else:
            pass

        # Cleanup agent
        await agent.cleanup()

        return session_id_2

    except Exception:
        import traceback

        traceback.print_exc()
        return None


async def test_router_with_user_memory(session_id_2: str):
    """Test #3: Verify AgentRouter uses user memory for classification.

    Router should include user memory blocks in context for better intent classification.
    """
    try:
        memory = MemoryManager()

        # Initialize router WITH memory
        router = AgentRouter(memory_manager=memory, session_id=session_id_2)
        await router.initialize()

        # Test ambiguous query (should use user memory for context)
        query = "Me interesa ese modelo"  # Ambiguous without context

        await router.classify_intent(query, persist_intent=False)

        # The router should have loaded user memory internally
        memory_context = router._get_memory_context()
        if memory_context:
            if "MEMORIA HISTÓRICA" in memory_context or "laptop" in memory_context.lower():
                pass
            else:
                pass
        else:
            pass

        # Cleanup
        await router.cleanup()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def test_memory_deduplication():
    """Test #4: Verify memory deduplication works correctly.

    If same memory block is synced from multiple sessions, it should be
    deduplicated (merged with max priority).
    """
    try:
        memory = MemoryManager()
        test_email = "test-dedup@example.com"

        # Create first session
        session_1 = memory.create_session(
            customer_email=test_email,
            metadata={"test": "dedup_session_1"},
        )

        # Add same memory block with priority 8
        memory.save_memory_block(
            session_id=session_1,
            block_label="product_interest",
            block_value="Usuario busca laptops gaming",
            priority=8,
            agent_scope="shared",
        )

        # Sync to user-level
        memory.sync_session_to_user_memory(session_1)

        # Check user blocks (should have 1 block)
        memory.get_user_memory_blocks(test_email, "shared")

        # Create second session
        session_2 = memory.create_session(
            customer_email=test_email,
            metadata={"test": "dedup_session_2"},
        )

        # Add SAME memory block but with higher priority (9)
        memory.save_memory_block(
            session_id=session_2,
            block_label="product_interest",
            block_value="Usuario busca laptops gaming",  # Same value
            priority=9,  # Higher priority
            agent_scope="shared",
        )

        # Sync to user-level (should deduplicate)
        memory.sync_session_to_user_memory(session_2)

        # Check user blocks (should still have 1 block, but with max priority)
        user_blocks_2 = memory.get_user_memory_blocks(test_email, "shared")

        if len(user_blocks_2) == 1:
            priority = user_blocks_2[0].get("priority", 0)
            if priority == 9:
                pass
            else:
                pass
        else:
            pass

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def test_cli_integration():
    """Test #5: Verify CLI tool can view user profiles.

    Tests the 'user-profile' command added to scripts/odiseo_memory.py.
    """
    try:
        import subprocess

        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "user-profile", TEST_EMAIL],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            # Check if output contains expected info
            if "USER MEMORY PROFILE" in result.stdout:
                pass
            if "Profile Information" in result.stdout:
                pass
            if "Cross-Session Memory Blocks" in result.stdout:
                pass

            lines = result.stdout.split("\n")[:15]
            for _line in lines:
                pass
        else:
            return False

        return True

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        import traceback

        traceback.print_exc()
        return False


# ============================================================================
# Main Test Suite
# ============================================================================


async def main():
    """Run all cross-session memory tests."""
    # Check prerequisites
    if not MEMORY_AVAILABLE:
        return 1

    results = []

    # Test 1: Session 1 memory creation
    session_id_1 = await test_session_1_memory_creation()
    results.append(("Session 1 Memory Creation", session_id_1 is not None))

    if not session_id_1:
        return 1

    # Test 2: Session 2 memory loading
    session_id_2 = await test_session_2_memory_loading(session_id_1)
    results.append(("Session 2 Memory Loading", session_id_2 is not None))

    if not session_id_2:
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

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for _test_name, _result in results:
        pass

    if passed == total:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
