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
    sys.exit(1)


async def test_base_agent_memory_integration():
    """Test BaseAgent with MemoryManager integration."""
    # 1. Initialize MemoryManager
    memory = MemoryManager()
    session_id = memory.create_session(
        customer_email="test@example.com",
        metadata={"source": "test"},
    )

    # 2. Initialize GeneralAgent with MemoryManager
    agent = GeneralAgent(session_id=session_id, memory_manager=memory)
    await agent.initialize()

    # 3. Generate response (should persist to DB)
    query = "¿Qué es Lab01-MCP?"
    await agent.generate_response(query)

    # 4. Verify messages were persisted
    messages = memory.get_recent_messages(session_id, limit=10)
    for msg in reversed(messages):
        msg["role"]
        msg["message_text"][:50]

    # 5. Test load_history_from_db
    agent.clear_history()
    agent.load_history_from_db(limit=5)

    # 6. Test save_memory_block
    agent.save_memory_block(
        block_label="user_info",
        block_value="Usuario preguntó sobre Lab01-MCP",
        priority=7,
        agent_scope="general",
    )

    # 7. Test get_memory_blocks
    blocks = agent.get_memory_blocks()
    for block in blocks:
        block["block_label"]
        block["block_value"][:50]
        block["priority"]

    # 8. Session statistics
    stats = memory.get_session_statistics(session_id)
    if stats:
        pass

    # Cleanup
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_base_agent_memory_integration())
