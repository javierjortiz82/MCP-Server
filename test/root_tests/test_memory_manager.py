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
    sys.exit(1)


# Initialize
memory = MemoryManager()

# Create session
session_id = memory.create_session(
    customer_email="test@example.com",
    metadata={"source": "test"},
)

# Save messages
msg1_id = memory.save_message(
    session_id,
    role="user",
    message_text="Busco una laptop gaming",
    intent="sales",
)

msg2_id = memory.save_message(
    session_id,
    role="model",
    agent_name="sales",
    message_text="Tenemos excelentes laptops gaming con RTX 4060",
    intent="sales",
    response_time_ms=450,
)

# Get recent messages
messages = memory.get_recent_messages(session_id, limit=10)
for _msg in reversed(messages):
    pass

# Save memory block
block_id = memory.save_memory_block(
    session_id,
    block_label="product_interest",
    block_value="Usuario interesado en laptops gaming con RTX 4060",
    priority=8,
    agent_scope="sales",
)

# Get memory blocks
blocks = memory.get_active_memory_blocks(session_id, agent_scope="sales")
for _block in blocks:
    pass

# Record context transfer
transfer_id = memory.record_context_transfer(
    session_id,
    from_agent="sales",
    to_agent="booking",
    transfer_reason="User wants to schedule demo",
    context_summary="Usuario interesado en laptop gaming",
    memory_blocks_transferred=1,
)

# Get statistics
stats = memory.get_session_statistics(session_id)
if stats:
    pass
