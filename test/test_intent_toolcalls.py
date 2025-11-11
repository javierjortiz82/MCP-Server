#!/usr/bin/env python3
"""Test script to verify intent and tool_calls storage in database."""

import asyncio
import sys
from pathlib import Path

# Add paths for imports (test/ is inside MCP-Server/)
project_root = Path(__file__).parent.parent
agent_path = project_root / "agent" / "src"
client_path = project_root / "client_mcp"
sys.path.insert(0, str(agent_path))
sys.path.insert(0, str(client_path))
sys.path.insert(0, str(project_root))

from client_mcp.core.agent_orchestrator import AgentOrchestrator
from client_mcp.config.settings import settings


async def test_intent_and_toolcalls():
    """Test that intent and tool_calls are properly stored."""
    print("=" * 70)
    print("Testing Intent & Tool_Calls Storage")
    print("=" * 70)

    # Initialize orchestrator
    print("\n1. Initializing orchestrator...")
    orchestrator = AgentOrchestrator()
    await orchestrator.initialize(customer_email="test-intent-toolcalls@example.com")
    print("✅ Orchestrator initialized")
    print(f"   Session ID: {orchestrator.session_id}")

    # Test booking query (should trigger get_services tool)
    print("\n2. Testing booking query (should store intent='booking' and tool_calls)...")
    query = "quiero reservar"
    print(f"Query: {query}")

    response = await orchestrator.process_query(query)
    print(f"Response: {response[:100]}...")

    # Wait a moment for DB to persist
    await asyncio.sleep(2)

    print("\n3. Checking database for intent and tool_calls...")
    import subprocess

    session_id = orchestrator.session_id
    query_sql = f"""
            SELECT id, agent_name, role, intent,
                   CASE WHEN tool_calls IS NOT NULL
                        THEN jsonb_pretty(tool_calls)
                        ELSE 'NULL'
                   END as tool_calls,
                   response_time_ms,
                   LEFT(message_text, 40) as message
            FROM test.conversation_messages
            WHERE session_id = '{session_id}'
            ORDER BY created_at DESC
            LIMIT 4;
            """

    result = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            "PGUSER=mcp_user",
            "mcp-postgres",
            "psql",
            "-d",
            "mcpdb",
            "-c",
            query_sql,
        ],
        capture_output=True,
        text=True,
    )

    print(result.stdout)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")

    print("\n4. Testing sales query (should store intent='sales')...")
    query2 = "busco laptop gaming"
    print(f"Query: {query2}")

    response2 = await orchestrator.process_query(query2)
    print(f"Response: {response2[:100]}...")

    await asyncio.sleep(2)

    print("\n5. Final database check...")

    summary_sql = f"""
            SELECT agent_name, intent, COUNT(*) as count
            FROM test.conversation_messages
            WHERE session_id = '{session_id}'
              AND role = 'model'
            GROUP BY agent_name, intent;
            """

    result2 = subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            "PGUSER=mcp_user",
            "mcp-postgres",
            "psql",
            "-d",
            "mcpdb",
            "-c",
            summary_sql,
        ],
        capture_output=True,
        text=True,
    )

    print(result2.stdout)

    print("\n=" * 70)
    print("Test completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_intent_and_toolcalls())
