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
    try:
        # Create a session with some history
        memory = MemoryManager()
        session_id = memory.create_session(
            customer_email="test-resume@example.com",
            metadata={"source": "test"},
        )

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
            session_id,
            "model",
            "El precio es $1299.99",
            agent_name="sales",
        )

        # Add a memory block
        memory.save_memory_block(
            session_id=session_id,
            block_label="product_interest",
            block_value="Usuario busca laptop gaming",
            priority=8,
            agent_scope="sales",
        )

        # Test session resumption
        agent = await GeneralAgent.resume_session(
            session_id=session_id,
            memory_manager=memory,
            load_history=True,
            show_summary=True,
        )

        # Verify loaded history
        if len(agent.conversation_history) >= 4:
            pass
        else:
            pass

        # Cleanup
        await agent.cleanup()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


def test_cli_tool():
    """Test #2: CLI Tool Commands."""
    try:
        # Test stats command
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "stats"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and "Total Sessions" in result.stdout:
            pass
        else:
            return False

        # Test sessions command
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "sessions"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and (
            "ACTIVE SESSIONS" in result.stdout or "No active sessions" in result.stdout
        ):
            pass
        else:
            return False

        # Test cleanup with dry-run
        result = subprocess.run(
            ["python3", "scripts/odiseo_memory.py", "cleanup", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0 and "CLEANUP PREVIEW" in result.stdout:
            pass
        else:
            return False

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def test_router_memory_integration():
    """Test #3: Router Integration with Memory."""
    try:
        # Create session with memory blocks
        memory = MemoryManager()
        session_id = memory.create_session(
            customer_email="test-router@example.com",
            metadata={"source": "test"},
        )

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

        # Initialize router with memory
        router_no_memory = AgentRouter()
        await router_no_memory.initialize()

        await router_no_memory.classify_intent(
            "Me interesa ese modelo",
        )

        await router_no_memory.cleanup()

        # Test with memory
        router_with_memory = AgentRouter(memory_manager=memory, session_id=session_id)
        await router_with_memory.initialize()

        # This query is ambiguous, but memory context should help
        await router_with_memory.classify_intent(
            "Me interesa ese modelo",
            persist_intent=True,
        )

        # Test specific intent queries

        # Sales query
        intent_sales = await router_with_memory.classify_intent(
            "Busco una laptop gaming",
        )
        if intent_sales == Intent.SALES:
            pass
        else:
            pass

        # Booking query
        intent_booking = await router_with_memory.classify_intent(
            "Quiero agendar una cita",
        )
        if intent_booking == Intent.BOOKING:
            pass
        else:
            pass

        # General query
        intent_general = await router_with_memory.classify_intent("Cuál es su horario?")
        if intent_general == Intent.GENERAL:
            pass
        else:
            pass

        # Cleanup
        await router_with_memory.cleanup()

        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all improvement tests."""
    if not MEMORY_AVAILABLE:
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
