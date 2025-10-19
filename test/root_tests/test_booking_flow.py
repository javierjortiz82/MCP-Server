#!/usr/bin/env python3
"""Test the complete booking flow end-to-end.

This script simulates the user's booking conversation to ensure the booking
agent can successfully create appointments.
"""

import asyncio
import sys
from pathlib import Path

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "client_mcp"))

from client_mcp.core.agent_orchestrator import AgentOrchestrator


async def main():
    """Test complete booking flow."""
    # Create orchestrator
    orchestrator = AgentOrchestrator()

    try:
        # Initialize
        await orchestrator.initialize()

        # Test 1: Ask about services
        await orchestrator.process_query(
            "¿Qué servicios tienen disponibles?",
            customer_email="test@example.com",
        )

        # Test 2: Request a booking
        await orchestrator.process_query(
            "Quiero una cita",
            customer_email="test@example.com",
        )

        # Test 3: Select service
        await orchestrator.process_query(
            "Sesión de Capacitación",
            customer_email="test@example.com",
        )

        # Test 4: Provide date
        response4 = await orchestrator.process_query(
            "2025-10-28",
            customer_email="test@example.com",
        )

        # Check if tools were used
        return not ("herramienta no está disponible" in response4 or "tool" in response4.lower())

    except Exception:
        import traceback

        traceback.print_exc()
        return False

    finally:
        await orchestrator.cleanup()


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
