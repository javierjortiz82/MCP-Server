#!/usr/bin/env python3
"""AgentFactory Pattern - Demo and Validation.

This script demonstrates the AgentFactory pattern and validates that it works
correctly for all agent types.

Usage:
    python test_agent_factory.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
agent_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent import AgentFactory


def print_header(text: str, char: str = "="):
    """Print fancy header."""
    print("\n" + char * 80)
    print(f"  {text}")
    print(char * 80)


async def test_factory_basic():
    """Test 1: Basic factory usage."""
    print_header("TEST 1: Basic Factory Usage", "=")

    print("\n📋 Testing AgentFactory.create() for all agent types...")

    # Test each agent type
    agent_types = ["booking", "general", "sales"]

    for agent_type in agent_types:
        print(f"\n  Creating {agent_type} agent...")

        try:
            # Create agent (without auto-initialization to avoid API calls)
            agent = await AgentFactory.create(agent_type, auto_initialize=False)

            print(f"    ✅ {agent_type} agent created: {type(agent).__name__}")
            print(f"    ✅ Agent name: {agent.agent_name}")

        except Exception as e:
            print(f"    ❌ Failed to create {agent_type}: {e}")
            return False

    print("\n✅ TEST 1 PASSED: All agent types created successfully")
    return True


async def test_convenience_methods():
    """Test 2: Convenience methods."""
    print_header("TEST 2: Convenience Methods", "=")

    print("\n📋 Testing convenience methods...")

    tests = []

    # Test create_booking_agent
    try:
        agent = await AgentFactory.create_booking_agent(auto_initialize=False)
        print(f"  ✅ create_booking_agent() → {type(agent).__name__}")
        tests.append(True)
    except Exception as e:
        print(f"  ❌ create_booking_agent() failed: {e}")
        tests.append(False)

    # Test create_general_agent
    try:
        agent = await AgentFactory.create_general_agent(auto_initialize=False)
        print(f"  ✅ create_general_agent() → {type(agent).__name__}")
        tests.append(True)
    except Exception as e:
        print(f"  ❌ create_general_agent() failed: {e}")
        tests.append(False)

    # Test create_sales_agent
    try:
        agent = await AgentFactory.create_sales_agent(auto_initialize=False)
        print(f"  ✅ create_sales_agent() → {type(agent).__name__}")
        tests.append(True)
    except Exception as e:
        print(f"  ❌ create_sales_agent() failed: {e}")
        tests.append(False)

    if all(tests):
        print("\n✅ TEST 2 PASSED: All convenience methods work")
        return True
    else:
        print("\n❌ TEST 2 FAILED: Some convenience methods failed")
        return False


async def test_available_agents():
    """Test 3: Get available agents."""
    print_header("TEST 3: Get Available Agents", "=")

    print("\n📋 Testing AgentFactory.get_available_agents()...")

    try:
        available = AgentFactory.get_available_agents()
        print(f"  Available agents: {available}")

        expected = ["booking", "general", "sales"]
        if set(available) == set(expected):
            print(f"  ✅ All expected agents present: {expected}")
            print("\n✅ TEST 3 PASSED")
            return True
        else:
            print(f"  ❌ Mismatch - Expected: {expected}, Got: {available}")
            print("\n❌ TEST 3 FAILED")
            return False

    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("\n❌ TEST 3 FAILED")
        return False


async def test_error_handling():
    """Test 4: Error handling for invalid agent types."""
    print_header("TEST 4: Error Handling", "=")

    print("\n📋 Testing error handling for invalid agent type...")

    try:
        # This should raise ValueError
        await AgentFactory.create("invalid_type", auto_initialize=False)
        print("  ❌ Should have raised ValueError but didn't")
        print("\n❌ TEST 4 FAILED")
        return False

    except ValueError as e:
        print(f"  ✅ Correctly raised ValueError: {e}")
        print("\n✅ TEST 4 PASSED")
        return True

    except Exception as e:
        print(f"  ❌ Raised wrong exception type: {type(e).__name__}: {e}")
        print("\n❌ TEST 4 FAILED")
        return False


async def test_is_registered():
    """Test 5: Check if agent types are registered."""
    print_header("TEST 5: is_registered() Method", "=")

    print("\n📋 Testing AgentFactory.is_registered()...")

    tests = []

    # Test valid types
    for agent_type in ["booking", "general", "sales"]:
        is_reg = AgentFactory.is_registered(agent_type)
        if is_reg:
            print(f"  ✅ '{agent_type}' is registered")
            tests.append(True)
        else:
            print(f"  ❌ '{agent_type}' should be registered but isn't")
            tests.append(False)

    # Test invalid type
    if not AgentFactory.is_registered("invalid"):
        print("  ✅ 'invalid' correctly not registered")
        tests.append(True)
    else:
        print("  ❌ 'invalid' shouldn't be registered")
        tests.append(False)

    if all(tests):
        print("\n✅ TEST 5 PASSED")
        return True
    else:
        print("\n❌ TEST 5 FAILED")
        return False


async def test_custom_parameters():
    """Test 6: Creating agents with custom parameters."""
    print_header("TEST 6: Custom Parameters", "=")

    print("\n📋 Testing agent creation with custom parameters...")

    try:
        # Create agent with custom temperature
        agent = await AgentFactory.create(
            "booking", auto_initialize=False, temperature=0.8, top_k=100
        )

        print("  ✅ Agent created with custom parameters")
        print(f"     Agent type: {type(agent).__name__}")
        print(f"     Agent name: {agent.agent_name}")

        print("\n✅ TEST 6 PASSED")
        return True

    except Exception as e:
        print(f"  ❌ Failed: {e}")
        print("\n❌ TEST 6 FAILED")
        return False


async def main():
    """Run all factory tests."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  AGENT FACTORY PATTERN - VALIDATION TESTS".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    print("\n🎯 Testing AgentFactory implementation...")

    results = []

    # Run tests
    results.append(("Basic Factory Usage", await test_factory_basic()))
    results.append(("Convenience Methods", await test_convenience_methods()))
    results.append(("Get Available Agents", await test_available_agents()))
    results.append(("Error Handling", await test_error_handling()))
    results.append(("is_registered() Method", await test_is_registered()))
    results.append(("Custom Parameters", await test_custom_parameters()))

    # Summary
    print_header("TEST SUMMARY", "=")

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL TESTS PASSED - AgentFactory working correctly!")
        print("\n📚 Usage Examples:")
        print("""
# Example 1: Create booking agent
from multi_agent import AgentFactory
agent = await AgentFactory.create("booking", mcp_tools=tools)
response = await agent.generate_response("Quiero reservar")

# Example 2: Create general agent (no tools)
agent = await AgentFactory.create("general")
response = await agent.generate_response("¿Cuál es el horario?")

# Example 3: Create with custom config
agent = await AgentFactory.create(
    "sales",
    mcp_tools=tools,
    temperature=0.7
)

# Example 4: Using convenience methods
agent = await AgentFactory.create_booking_agent(mcp_tools=tools)
        """)
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
