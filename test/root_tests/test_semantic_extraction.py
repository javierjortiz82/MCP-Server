#!/usr/bin/env python3
"""Test Semantic Extraction (Fase 4) - LLM-based memory extraction.

USAGE:
    python3 test_semantic_extraction.py
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


async def test_semantic_extraction():
    """Test LLM-based semantic memory extraction."""
    # 1. Initialize MemoryManager and Agent
    memory = MemoryManager()
    session_id = memory.create_session(
        customer_email="test-semantic@example.com",
        metadata={"source": "test"},
    )

    agent = GeneralAgent(session_id=session_id, memory_manager=memory)
    await agent.initialize()

    # 2. Simulate conversation with extractable information

    queries = [
        "Busco una laptop gaming para diseño 3D y gaming",
        "Mi presupuesto es de aproximadamente $1500",
        "Necesito al menos 16GB RAM y una RTX 4060",
        "Prefiero contacto por WhatsApp después de las 6pm",
    ]

    for _i, query in enumerate(queries, 1):
        await agent.generate_response(query)

    # 3. Extract semantic memory using LLM
    try:
        memories = await agent.extract_semantic_memory(
            context="Usuario haciendo consulta de compra",
            auto_save=True,
        )

        if memories:
            for mem in memories:
                mem.get("block_label", "unknown")
                mem.get("block_value", "")
                mem.get("priority", 0)
                mem.get("agent_scope", "unknown")
                mem.get("reasoning", "")

        else:
            pass

    except Exception:
        pass

    # 4. Verify persistence
    blocks = memory.get_active_memory_blocks(session_id, agent_scope="shared")

    for block in blocks[:3]:  # Show first 3
        block["block_label"]
        block["block_value"][:60]
        block["priority"]

    # 5. Session statistics
    stats = memory.get_session_statistics(session_id)
    if stats:
        pass

    # Cleanup
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(test_semantic_extraction())
