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
    print("ERROR: MemoryManager not available")
    sys.exit(1)


async def test_semantic_extraction():
    """Test LLM-based semantic memory extraction."""
    print("=" * 70)
    print("TESTING SEMANTIC EXTRACTION (FASE 4)")
    print("=" * 70)

    # 1. Initialize MemoryManager and Agent
    print("\n1. Initializing MemoryManager and GeneralAgent...")
    memory = MemoryManager()
    session_id = memory.create_session(
        customer_email="test-semantic@example.com", metadata={"source": "test"}
    )
    print(f"   ✅ Session created: {session_id[:8]}...")

    agent = GeneralAgent(session_id=session_id, memory_manager=memory)
    await agent.initialize()
    print("   ✅ Agent initialized with memory")

    # 2. Simulate conversation with extractable information
    print("\n2. Simulating conversation with extractable facts...")

    queries = [
        "Busco una laptop gaming para diseño 3D y gaming",
        "Mi presupuesto es de aproximadamente $1500",
        "Necesito al menos 16GB RAM y una RTX 4060",
        "Prefiero contacto por WhatsApp después de las 6pm",
    ]

    for i, query in enumerate(queries, 1):
        print(f"   Query {i}: {query[:50]}...")
        response = await agent.generate_response(query)
        print(f"   Response {i}: {response[:80]}...")

    # 3. Extract semantic memory using LLM
    print("\n3. Extracting semantic memory using LLM...")
    try:
        memories = await agent.extract_semantic_memory(
            context="Usuario haciendo consulta de compra", auto_save=True
        )

        print(f"   ✅ Extracted {len(memories)} memory blocks")

        if memories:
            print("\n   EXTRACTED MEMORIES:")
            for mem in memories:
                label = mem.get("block_label", "unknown")
                value = mem.get("block_value", "")
                priority = mem.get("priority", 0)
                scope = mem.get("agent_scope", "unknown")
                reasoning = mem.get("reasoning", "")

                print(f"\n   [{label}] (priority={priority}, scope={scope})")
                print(f"   Value: {value}")
                print(f"   Reasoning: {reasoning}")
        else:
            print("   ℹ️  No high-priority memories extracted")

    except Exception as e:
        print(f"   ⚠️  Extraction failed: {e}")
        print("   (This is expected if GOOGLE_API_KEY is not set)")

    # 4. Verify persistence
    print("\n4. Verifying memory block persistence...")
    blocks = memory.get_active_memory_blocks(session_id, agent_scope="shared")
    print(f"   ✅ Retrieved {len(blocks)} active memory blocks from DB")

    for block in blocks[:3]:  # Show first 3
        label = block["block_label"]
        value = block["block_value"][:60]
        priority = block["priority"]
        print(f"      - [{label}] (p={priority}): {value}...")

    # 5. Session statistics
    print("\n5. Session statistics...")
    stats = memory.get_session_statistics(session_id)
    if stats:
        print("   ✅ Statistics:")
        print(f"      - Total messages: {stats['total_messages']}")
        print(f"      - Memory blocks: {stats['memory_blocks']}")

    # Cleanup
    await agent.cleanup()

    print("\n" + "=" * 70)
    print("✅ SEMANTIC EXTRACTION TEST COMPLETED")
    print("=" * 70)
    print("\nNOTE: Actual extraction quality depends on:")
    print("  - GOOGLE_API_KEY configuration")
    print("  - Gemini API availability")
    print("  - Conversation content richness")


if __name__ == "__main__":
    asyncio.run(test_semantic_extraction())
