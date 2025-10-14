#!/usr/bin/env python3
"""Test BaseAgent integration with MemoryManager.

USAGE:
    python3 test_base_agent_memory.py
"""

import asyncio
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager
from multi_agent.general_agent import GeneralAgent

if not MEMORY_AVAILABLE:
    print("ERROR: MemoryManager not available")
    sys.exit(1)


async def test_base_agent_memory_integration():
    """Test BaseAgent with MemoryManager integration."""
    print("=" * 70)
    print("TESTING BASEAGENT + MEMORYMANAGER INTEGRATION")
    print("=" * 70)

    # 1. Initialize MemoryManager
    print("\n1. Initializing MemoryManager...")
    memory = MemoryManager()
    session_id = memory.create_session(
        customer_email="test@example.com", metadata={"source": "test"}
    )
    print(f"   ✅ Session created: {session_id[:8]}...")

    # 2. Initialize GeneralAgent with MemoryManager
    print("\n2. Initializing GeneralAgent with memory...")
    agent = GeneralAgent(session_id=session_id, memory_manager=memory)
    await agent.initialize()
    print(f"   ✅ Agent initialized (memory_enabled={agent._memory_enabled})")

    # 3. Generate response (should persist to DB)
    print("\n3. Generating response...")
    query = "¿Qué es Lab01-MCP?"
    response = await agent.generate_response(query)
    print(f"   ✅ Response generated ({len(response)} chars)")
    print(f"   Response: {response[:100]}...")

    # 4. Verify messages were persisted
    print("\n4. Verifying database persistence...")
    messages = memory.get_recent_messages(session_id, limit=10)
    print(f"   ✅ Retrieved {len(messages)} messages from DB")
    for msg in reversed(messages):
        role = msg["role"]
        text = msg["message_text"][:50]
        print(f"      - {role}: {text}...")

    # 5. Test load_history_from_db
    print("\n5. Testing load_history_from_db...")
    agent.clear_history()
    print(f"   History cleared (len={len(agent.conversation_history)})")
    loaded = agent.load_history_from_db(limit=5)
    print(f"   ✅ Loaded {loaded} messages from DB")
    print(f"   History length: {len(agent.conversation_history)}")

    # 6. Test save_memory_block
    print("\n6. Testing save_memory_block...")
    block_id = agent.save_memory_block(
        block_label="user_info",
        block_value="Usuario preguntó sobre Lab01-MCP",
        priority=7,
        agent_scope="general",
    )
    print(f"   ✅ Memory block saved (id={block_id})")

    # 7. Test get_memory_blocks
    print("\n7. Testing get_memory_blocks...")
    blocks = agent.get_memory_blocks()
    print(f"   ✅ Retrieved {len(blocks)} memory blocks")
    for block in blocks:
        label = block["block_label"]
        value = block["block_value"][:50]
        priority = block["priority"]
        print(f"      - [{label}] (p={priority}): {value}...")

    # 8. Session statistics
    print("\n8. Getting session statistics...")
    stats = memory.get_session_statistics(session_id)
    if stats:
        print("   ✅ Statistics:")
        print(f"      - Total messages: {stats['total_messages']}")
        print(f"      - User messages: {stats['user_messages']}")
        print(f"      - Model messages: {stats['model_messages']}")
        print(f"      - Memory blocks: {stats['memory_blocks']}")

    # Cleanup
    await agent.cleanup()

    print("\n" + "=" * 70)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_base_agent_memory_integration())
