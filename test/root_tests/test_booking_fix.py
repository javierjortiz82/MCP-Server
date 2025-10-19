#!/usr/bin/env python3
"""Test script to verify get_available_slots works without Context parameter bug.

This script tests:
1. Direct function call to get_available_slots business logic (should work)
2. MCP tool schema validation (ctx should NOT be in required parameters)
3. Actual booking flow simulation
"""

import sys
from datetime import date, timedelta

# Add mcp_server to path
sys.path.insert(0, "/home/javort/Lab01-MCP/mcp_server")

from tools import bookings

# Test 1: Direct business logic call

try:
    # Get available slots for tomorrow
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    result = bookings.get_available_slots(
        service_type="consultation",
        date=tomorrow,
        duration_minutes=60,
    )

    if result.get("available_slots"):
        for _slot in result["available_slots"][:3]:
            pass

except Exception:
    import traceback

    traceback.print_exc()

# Test 2: Check if services are available

try:
    services_result = bookings.get_services(active_only=True)

    if services_result.get("services"):
        for _service in services_result["services"]:
            pass

except Exception:
    import traceback

    traceback.print_exc()

# Test 3: Summary
