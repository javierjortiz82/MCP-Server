#!/usr/bin/env python3
"""Test context-aware routing for multi-turn booking conversations.

This test verifies that the AgentRouter maintains context across conversation
turns, specifically testing the scenario where:
1. User initiates booking ("quiero una cita")
2. User selects service
3. User provides date
4. User provides personal data (name, email, phone)

The router should recognize that personal data is provided in response to
a booking request and maintain "booking" intent (not switch to "general").

Author: Lab01-MCP Team
Created: 2025-10-12
"""

import asyncio
import sys
from pathlib import Path

# Add agent/src to Python path
agent_src = Path(__file__).parent / "agent" / "src"
sys.path.insert(0, str(agent_src))

import logging

from gemini_agent.utils.logger import setup_logging
from multi_agent.agent_router import AgentRouter, Intent

logger = setup_logging("test_context_routing")

# Enable DEBUG logging for agent_router
logging.getLogger("agent_router").setLevel(logging.DEBUG)


async def test_booking_flow_with_context():
    """Test that router maintains booking intent when user provides personal data."""
    logger.info("=" * 70)
    logger.info("TEST: Context-Aware Routing for Booking Flow")
    logger.info("=" * 70)

    # Initialize router
    router = AgentRouter()
    await router.initialize()

    # Simulate conversation flow
    conversation = [
        {
            "turn": 1,
            "user_query": "quiero una cita",
            "expected_intent": Intent.BOOKING,
            "context": None,
            "bot_response": "¿Para qué servicio deseas agendar? Tenemos: Sesión de Capacitación, Consultoría Técnica, Soporte Premium",
        },
        {
            "turn": 2,
            "user_query": "Sesión de Capacitación",
            "expected_intent": Intent.BOOKING,
            "context": None,  # Will be built from previous turn
            "bot_response": "¿Qué fecha prefieres para tu Sesión de Capacitación?",
        },
        {
            "turn": 3,
            "user_query": "2025-10-15",
            "expected_intent": Intent.BOOKING,
            "context": None,  # Will be built from previous turn
            "bot_response": "Perfecto. Para confirmar la reserva necesito tus datos: nombre completo, correo electrónico y teléfono.",
        },
        {
            "turn": 4,
            "user_query": "Javier Ortiz, javier@ortiz.com, 88459904",
            "expected_intent": Intent.BOOKING,  # THIS IS THE CRITICAL TEST
            "context": None,  # Will be built from previous turn
            "bot_response": "¡Reserva confirmada!",
        },
    ]

    # Track context across turns
    last_intent = None
    last_bot_message = None

    all_passed = True

    for turn_data in conversation:
        turn_num = turn_data["turn"]
        query = turn_data["user_query"]
        expected = turn_data["expected_intent"]
        bot_response = turn_data["bot_response"]

        logger.info(f"\n{'=' * 70}")
        logger.info(f"TURN {turn_num}")
        logger.info(f"{'=' * 70}")
        logger.info(f"User query: '{query}'")

        # Build context from previous turn
        context = {}
        if last_intent:
            context["last_intent"] = last_intent.value
        if last_bot_message:
            context["last_bot_message"] = last_bot_message

        if context:
            logger.info("Context provided:")
            logger.info(f"  - last_intent: {context.get('last_intent')}")
            logger.info(
                f"  - last_bot_message: {context.get('last_bot_message')[:50]}...",
            )
        else:
            logger.info("No context (first turn)")

        # Classify with context
        intent = await router.classify_intent(
            query,
            context=context if context else None,
        )

        # Check result
        passed = intent == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"Expected: {expected.value}")
        logger.info(f"Got: {intent.value}")
        logger.info(f"{status}")

        if not passed:
            all_passed = False
            logger.error(
                f"❌ Turn {turn_num} FAILED: Expected {expected.value}, got {intent.value}",
            )

        # Update context for next turn
        last_intent = intent
        last_bot_message = bot_response

    # Final summary
    logger.info(f"\n{'=' * 70}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'=' * 70}")

    if all_passed:
        logger.info("✅ ALL TESTS PASSED")
        logger.info("✅ Context-aware routing is working correctly")
        logger.info("✅ Booking flow should complete without interruption")
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("❌ Context-aware routing needs adjustment")
        logger.error("❌ Review the router prompt or context passing logic")

    await router.cleanup()

    return all_passed


async def test_edge_cases():
    """Test edge cases for context-aware routing."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST: Edge Cases for Context-Aware Routing")
    logger.info("=" * 70)

    router = AgentRouter()
    await router.initialize()

    edge_cases = [
        {
            "name": "Phone number alone in booking context",
            "query": "88459904",
            "context": {
                "last_intent": "booking",
                "last_bot_message": "Por favor proporciona tu número de teléfono",
            },
            "expected": Intent.BOOKING,
        },
        {
            "name": "Email alone in booking context",
            "query": "javier@ortiz.com",
            "context": {
                "last_intent": "booking",
                "last_bot_message": "¿Cuál es tu correo electrónico?",
            },
            "expected": Intent.BOOKING,
        },
        {
            "name": "Confirmation in booking context",
            "query": "sí, confirmo",
            "context": {
                "last_intent": "booking",
                "last_bot_message": "¿Confirmas la reserva para 2025-10-15?",
            },
            "expected": Intent.BOOKING,
        },
        {
            "name": "New query after booking (should reset to general)",
            "query": "hola",
            "context": {
                "last_intent": "booking",
                "last_bot_message": "Tu reserva ha sido confirmada",
            },
            "expected": Intent.GENERAL,
        },
    ]

    all_passed = True

    for i, case in enumerate(edge_cases, 1):
        logger.info(f"\n{'=' * 70}")
        logger.info(f"Edge Case {i}: {case['name']}")
        logger.info(f"{'=' * 70}")
        logger.info(f"Query: '{case['query']}'")
        logger.info(f"Context: {case['context']}")

        intent = await router.classify_intent(case["query"], context=case["context"])

        passed = intent == case["expected"]
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"Expected: {case['expected'].value}")
        logger.info(f"Got: {intent.value}")
        logger.info(f"{status}")

        if not passed:
            all_passed = False

    await router.cleanup()

    return all_passed


async def main():
    """Run all context-aware routing tests."""
    try:
        # Test 1: Main booking flow
        test1_passed = await test_booking_flow_with_context()

        # Test 2: Edge cases
        test2_passed = await test_edge_cases()

        # Final result
        logger.info("\n" + "=" * 70)
        logger.info("FINAL RESULTS")
        logger.info("=" * 70)
        logger.info(
            f"Booking Flow Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}",
        )
        logger.info(f"Edge Cases Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

        if test1_passed and test2_passed:
            logger.info("\n✅ ALL TESTS PASSED - Context-aware routing is working!")
            return 0
        else:
            logger.error("\n❌ SOME TESTS FAILED - Review implementation")
            return 1

    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
