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
    print("=" * 70)
    print("🧪 Testing Complete Booking Flow")
    print("=" * 70)

    # Create orchestrator
    orchestrator = AgentOrchestrator()

    try:
        # Initialize
        print("\n[1/5] Initializing agent orchestrator...")
        await orchestrator.initialize()
        print("   ✅ Orchestrator initialized")

        # Test 1: Ask about services
        print("\n[2/5] Testing: '¿Qué servicios tienen disponibles?'")
        response1 = await orchestrator.process_query(
            "¿Qué servicios tienen disponibles?", customer_email="test@example.com"
        )
        print(f"   Response: {response1[:150]}...")

        # Test 2: Request a booking
        print("\n[3/5] Testing: 'Quiero una cita'")
        response2 = await orchestrator.process_query(
            "Quiero una cita", customer_email="test@example.com"
        )
        print(f"   Response: {response2[:150]}...")

        # Test 3: Select service
        print("\n[4/5] Testing: 'Sesión de Capacitación'")
        response3 = await orchestrator.process_query(
            "Sesión de Capacitación", customer_email="test@example.com"
        )
        print(f"   Response: {response3[:150]}...")

        # Test 4: Provide date
        print("\n[5/5] Testing: '2025-10-28'")
        response4 = await orchestrator.process_query(
            "2025-10-28", customer_email="test@example.com"
        )
        print(f"   Response: {response4[:300]}...")

        # Check if tools were used
        if "herramienta no está disponible" in response4 or "tool" in response4.lower():
            print("\n   ❌ FAIL: Agent still says tools are not available")
            return False
        else:
            print("\n   ✅ SUCCESS: Agent can now access booking tools!")
            return True

    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        await orchestrator.cleanup()
        print("\n" + "=" * 70)
        print("✅ Test completed")
        print("=" * 70)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
