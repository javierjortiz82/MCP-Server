#!/usr/bin/env python3
"""Quick test for MemoryManager functionality.

USAGE:
    PYTHONPATH="agent/src" python3 test_memory_manager.py
"""

import sys
from pathlib import Path

# Add both agent/src and mcp_server to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "agent" / "src"))
sys.path.insert(0, str(project_root / "mcp_server"))

from multi_agent import MEMORY_AVAILABLE, MemoryManager

if not MEMORY_AVAILABLE:
    print("ERROR: MemoryManager not available")
    sys.exit(1)

print("=" * 70)
print("TESTING MEMORY MANAGER")
print("=" * 70)

# Initialize
print("\n1. Initializing MemoryManager...")
memory = MemoryManager()
print(f"   ✅ Config: {memory.config}")

# Create session
print("\n2. Creating session...")
session_id = memory.create_session(
    customer_email="test@example.com", metadata={"source": "test"}
)
print(f"   ✅ Session ID: {session_id[:8]}...")

# Save messages
print("\n3. Saving messages...")
msg1_id = memory.save_message(
    session_id,
    role="user",
    message_text="Busco una laptop gaming",
    intent="sales",
)
print(f"   ✅ User message saved (id={msg1_id})")

msg2_id = memory.save_message(
    session_id,
    role="model",
    agent_name="sales",
    message_text="Tenemos excelentes laptops gaming con RTX 4060",
    intent="sales",
    response_time_ms=450,
)
print(f"   ✅ Model message saved (id={msg2_id})")

# Get recent messages
print("\n4. Getting recent messages...")
messages = memory.get_recent_messages(session_id, limit=10)
print(f"   ✅ Retrieved {len(messages)} messages")
for msg in reversed(messages):
    print(f"      - {msg['role']}: {msg['message_text'][:50]}...")

# Save memory block
print("\n5. Saving memory block...")
block_id = memory.save_memory_block(
    session_id,
    block_label="product_interest",
    block_value="Usuario interesado en laptops gaming con RTX 4060",
    priority=8,
    agent_scope="sales",
)
print(f"   ✅ Memory block saved (id={block_id})")

# Get memory blocks
print("\n6. Getting active memory blocks...")
blocks = memory.get_active_memory_blocks(session_id, agent_scope="sales")
print(f"   ✅ Retrieved {len(blocks)} active blocks")
for block in blocks:
    print(f"      - {block['block_label']}: {block['block_value'][:50]}...")

# Record context transfer
print("\n7. Recording context transfer...")
transfer_id = memory.record_context_transfer(
    session_id,
    from_agent="sales",
    to_agent="booking",
    transfer_reason="User wants to schedule demo",
    context_summary="Usuario interesado en laptop gaming",
    memory_blocks_transferred=1,
)
print(f"   ✅ Context transfer recorded (id={transfer_id})")

# Get statistics
print("\n8. Getting session statistics...")
stats = memory.get_session_statistics(session_id)
if stats:
    print("   ✅ Statistics:")
    print(f"      - Total messages: {stats['total_messages']}")
    print(f"      - User messages: {stats['user_messages']}")
    print(f"      - Model messages: {stats['model_messages']}")
    print(f"      - Memory blocks: {stats['memory_blocks']}")
    print(f"      - Context transfers: {stats['context_transfers']}")

print("\n" + "=" * 70)
print("✅ ALL TESTS PASSED")
print("=" * 70)
