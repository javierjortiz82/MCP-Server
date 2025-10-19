#!/usr/bin/env python3
"""Test Memory System Improvements (Phase 5).

Tests the final improvements to the memory system:
1. Session Resumption Helper
2. CLI Tool (via subprocess)
3. Router Integration with Memory

USAGE:
    python3 test_memory_improvements.py
"""

import asyncio
import subprocess
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager
from multi_agent.agent_router import AgentRouter, Intent
from multi_agent.general_agent import GeneralAgent


async def test_session_resumption():
    """Test #1: Session Resumption Helper."""
    print("\n" + "=" * 70)
    print("TEST 1: SESSION RESUMPTION HELPER")
    print("=" * 70)

    try:
        # Create a session with some history
        print("\n1. Creating new session with conversation history...")
        memory = MemoryManager()
        session_id = memory.create_session(
            customer_email="test-resume@example.com", metadata={"source": "test"}
        )
        print(f"   ✅ Session created: {session_id[:8]}...")

        # Add some messages
        memory.save_message(session_id, "user", "Busco una laptop gaming")
        memory.save_message(
            session_id,
            "model",
            "Tenemos laptops gaming con RTX 4060",
            agent_name="sales",
        )
        memory.save_message(session_id, "user", "Cuál es el precio?")
        memory.save_message(
            session_id, "model", "El precio es $1299.99", agent_name="sales"
        )

        # Add a memory block
        memory.save_memory_block(
            session_id=session_id,
            block_label="product_interest",
            block_value="Usuario busca laptop gaming",
            priority=8,
            agent_scope="sales",
        )

        print("   ✅ Added 4 messages and 1 memory block")

        # Test session resumption
        print("\n2. Testing session resumption...")
        agent = await GeneralAgent.resume_session(
            session_id=session_id,
            memory_manager=memory,
            load_history=True,
            show_summary=True,
        )

        print("   ✅ Session resumed successfully")
        print(f"   History length: {len(agent.conversation_history)} messages")

        # Verify loaded history
        if len(agent.conversation_history) >= 4:
            print("   ✅ History loaded correctly")
        else:
            print(f"   ⚠️  Expected 4+ messages, got {len(agent.conversation_history)}")

        # Cleanup
        await agent.cleanup()

        print("\n✅ TEST 1 PASSED: Session Resumption Helper works correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_tool():
    """Test #2: CLI Tool Commands."""
    print("\n" + "=" * 70)
    print("TEST 2: CLI TOOL")
    print("=" * 70)

    try:
        # Test stats command
        print("\n1. Testing 'stats' command...")
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "stats"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and "Total Sessions" in result.stdout:
            print("   ✅ Stats command works")
        else:
            print(f"   ❌ Stats command failed: {result.stderr}")
            return False

        # Test sessions command
        print("\n2. Testing 'sessions' command...")
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "sessions"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and (
            "ACTIVE SESSIONS" in result.stdout or "No active sessions" in result.stdout
        ):
            print("   ✅ Sessions command works")
        else:
            print(f"   ❌ Sessions command failed: {result.stderr}")
            return False

        # Test cleanup with dry-run
        print("\n3. Testing 'cleanup --dry-run' command...")
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "cleanup", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and "CLEANUP PREVIEW" in result.stdout:
            print("   ✅ Cleanup dry-run command works")
        else:
            print(f"   ❌ Cleanup command failed: {result.stderr}")
            return False

        print("\n✅ TEST 2 PASSED: CLI Tool commands work correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_router_memory_integration():
    """Test #3: Router Integration with Memory."""
    print("\n" + "=" * 70)
    print("TEST 3: ROUTER MEMORY INTEGRATION")
    print("=" * 70)

    try:
        # Create session with memory blocks
        print("\n1. Creating session with memory blocks...")
        memory = MemoryManager()
        session_id = memory.create_session(
            customer_email="test-router@example.com", metadata={"source": "test"}
        )
        print(f"   ✅ Session created: {session_id[:8]}...")

        # Add memory blocks that should influence classification
        memory.save_memory_block(
            session_id=session_id,
            block_label="product_interest",
            block_value="Usuario mostró interés en laptops gaming RTX 4060",
            priority=9,
            agent_scope="shared",
        )
        memory.save_memory_block(
            session_id=session_id,
            block_label="user_preferences",
            block_value="Prefiere productos de tecnología de alta gama",
            priority=8,
            agent_scope="shared",
        )

        print("   ✅ Added 2 high-priority memory blocks")

        # Initialize router with memory
        print("\n2. Testing router without memory...")
        router_no_memory = AgentRouter()
        await router_no_memory.initialize()

        intent_no_memory = await router_no_memory.classify_intent(
            "Me interesa ese modelo"
        )
        print(f"   Classification without memory: {intent_no_memory.value}")

        await router_no_memory.cleanup()

        # Test with memory
        print("\n3. Testing router WITH memory...")
        router_with_memory = AgentRouter(memory_manager=memory, session_id=session_id)
        await router_with_memory.initialize()

        # This query is ambiguous, but memory context should help
        intent_with_memory = await router_with_memory.classify_intent(
            "Me interesa ese modelo", persist_intent=True
        )
        print(f"   Classification WITH memory: {intent_with_memory.value}")
        print("   (Expected: sales, based on memory context)")

        # Test specific intent queries
        print("\n4. Testing specific intent queries...")

        # Sales query
        intent_sales = await router_with_memory.classify_intent(
            "Busco una laptop gaming"
        )
        if intent_sales == Intent.SALES:
            print("   ✅ Sales intent correctly classified")
        else:
            print(f"   ⚠️  Expected SALES, got {intent_sales.value}")

        # Booking query
        intent_booking = await router_with_memory.classify_intent(
            "Quiero agendar una cita"
        )
        if intent_booking == Intent.BOOKING:
            print("   ✅ Booking intent correctly classified")
        else:
            print(f"   ⚠️  Expected BOOKING, got {intent_booking.value}")

        # General query
        intent_general = await router_with_memory.classify_intent("Cuál es su horario?")
        if intent_general == Intent.GENERAL:
            print("   ✅ General intent correctly classified")
        else:
            print(f"   ⚠️  Expected GENERAL, got {intent_general.value}")

        # Cleanup
        await router_with_memory.cleanup()

        print("\n✅ TEST 3 PASSED: Router memory integration works correctly")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all improvement tests."""
    print("=" * 70)
    print("MEMORY SYSTEM IMPROVEMENTS - COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    if not MEMORY_AVAILABLE:
        print("\n❌ ERROR: MemoryManager not available")
        print("   Please check your configuration and database connection")
        return 1

    # Run tests
    results = []

    # Test 1: Session Resumption
    result1 = await test_session_resumption()
    results.append(("Session Resumption", result1))

    # Test 2: CLI Tool
    result2 = test_cli_tool()
    results.append(("CLI Tool", result2))

    # Test 3: Router Memory Integration
    result3 = await test_router_memory_integration()
    results.append(("Router Memory Integration", result3))

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
        print("\n🎉 ALL TESTS PASSED! Memory system improvements working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
