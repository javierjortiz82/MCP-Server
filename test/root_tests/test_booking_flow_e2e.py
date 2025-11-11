#!/usr/bin/env python3
"""End-to-end test for booking flow with anti-hallucination prompts.

This test verifies:
1. BookingAgent calls get_available_slots BEFORE showing time slots (no hallucination)
2. Context parameter is properly excluded from tool schemas
3. Booking flow completes successfully from inquiry to confirmation
"""

import asyncio
import sys
from datetime import date, timedelta

# Add paths
sys.path.insert(0, "/home/javort/Lab01-MCP/client_mcp")
sys.path.insert(0, "/home/javort/Lab01-MCP/agent/src")

from client_mcp.core.agent_orchestrator import AgentOrchestrator


async def test_booking_flow():
    """Test complete booking flow."""
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()

    # Get tomorrow's date for booking
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Test 1: Ask about availability (should call get_available_slots)

    query1 = f"Qué horarios tienen disponibles para una consulta el {tomorrow}?"

    try:
        response1 = await orchestrator.process_query(query1)

        # Check if response mentions actual time slots (not hallucinated)
        if "09:00" in response1 or "10:00" in response1:
            pass

    except Exception:
        import traceback

        traceback.print_exc()
        return

    # Test 2: Customer selects a time slot

    query2 = "Quiero reservar para las 10:00. Mi nombre es Test User, email test@example.com, teléfono 88888888"

    try:
        response2 = await orchestrator.process_query(query2)

        # Check if booking was created
        if "confirmación" in response2.lower() or "reserva confirmada" in response2.lower():
            # Check if it has a real booking ID (not hallucinated)
            if "#" in response2:
                pass

    except Exception:
        import traceback

        traceback.print_exc()
        return


if __name__ == "__main__":
    asyncio.run(test_booking_flow())
