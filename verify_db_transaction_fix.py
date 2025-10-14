#!/usr/bin/env python3
"""
Verify that database transactions are properly committed.

This test directly verifies the fix for the database transaction bug where
bookings appeared successful but weren't persisted to the database.
"""

import asyncio
import sys
from datetime import date, timedelta

import httpx

sys.path.insert(0, "/home/javort/Lab01-MCP/mcp_server")


async def test_booking_persistence():
    """Test that bookings are properly committed to the database."""

    print("=" * 80)
    print(" DATABASE TRANSACTION FIX VERIFICATION")
    print("=" * 80)
    print()

    # Get tomorrow's date for booking
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"📅 Testing booking for: {tomorrow}")
    print()

    # Step 1: Call create_booking via MCP HTTP endpoint
    print("🔧 Step 1: Creating booking via MCP create_booking tool...")

    mcp_url = "http://localhost:8009/mcp/"

    # Create booking request
    booking_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_booking",
            "arguments": {
                "customer_name": "Test Verification User",
                "customer_email": "test_verify@example.com",
                "customer_phone": "99999999",
                "service_type": "consultation",
                "booking_date": tomorrow,
                "booking_time": "10:00",
                "notes": "Database transaction fix verification test",
            },
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                mcp_url,
                json=booking_request,
                headers={
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                return False

            result = response.json()

            if "error" in result:
                print(f"❌ MCP Error: {result['error']}")
                return False

            # Extract booking_id from response
            tool_result = result.get("result", {})
            if isinstance(tool_result, dict) and "content" in tool_result:
                content = tool_result["content"]
                if isinstance(content, list) and len(content) > 0:
                    import json

                    booking_data = json.loads(content[0].get("text", "{}"))
                    booking_id = booking_data.get("booking_id")

                    if booking_id:
                        print("✅ Booking created successfully via MCP")
                        print(f"   Booking ID: {booking_id}")
                        print()

                        # Step 2: Verify booking exists in database
                        print("🔍 Step 2: Verifying booking persists in database...")
                        return await verify_in_database(booking_id)

            print("❌ Could not extract booking_id from response")
            print(f"Response: {result}")
            return False

    except Exception as e:
        print(f"❌ Error calling MCP tool: {e}")
        import traceback

        traceback.print_exc()
        return False


async def verify_in_database(booking_id: int) -> bool:
    """Verify booking exists in database using Docker exec."""

    import subprocess

    try:
        query = f"SELECT id, customer_name, customer_email, service_type, booking_date, status FROM test.appointments WHERE id = {booking_id};"

        result = subprocess.run(
            [
                "docker",
                "exec",
                "mcp-postgres",
                "psql",
                "-U",
                "mcp_user",
                "-d",
                "mcpdb",
                "-c",
                query,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        output = result.stdout

        print("📊 Database query result:")
        print(output)
        print()

        # Check if booking exists in database
        if "id | customer_name" in output and str(booking_id) in output:
            if "Test Verification User" in output:
                print("=" * 80)
                print(" ✅ SUCCESS - DATABASE TRANSACTION FIX IS WORKING!")
                print("=" * 80)
                print()
                print("🎉 The booking was created AND persisted to the database!")
                print("✅ Transaction commit is working correctly")
                print()
                return True

        print("=" * 80)
        print(" ❌ FAILED - BOOKING NOT FOUND IN DATABASE")
        print("=" * 80)
        print()
        print("⚠️ The booking was created but NOT persisted!")
        print("❌ Transaction may not have been committed")
        print()
        return False

    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    success = await test_booking_persistence()

    if success:
        print("=" * 80)
        print(" VERIFICATION SUMMARY")
        print("=" * 80)
        print("✅ Database transaction fix is working correctly")
        print("✅ Bookings are now properly committed to the database")
        print("✅ The 'ghost booking' bug has been fixed!")
        print()
        sys.exit(0)
    else:
        print("=" * 80)
        print(" VERIFICATION FAILED")
        print("=" * 80)
        print("❌ Database transaction fix may not be working")
        print("⚠️ Please check the logs for errors")
        print()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
