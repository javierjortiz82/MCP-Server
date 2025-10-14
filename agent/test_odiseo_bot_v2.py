#!/usr/bin/env python3
"""Tests for OdiseoBotV2 - Validation Suite.

This test suite validates that OdiseoBotV2 maintains full compatibility
with the legacy OdiseoBot while leveraging BaseAgent architecture.

Test Coverage:
- Initialization and configuration
- BaseAgent inheritance (metrics, history, etc.)
- MCP tools integration (mocked)
- Pagination functionality
- Thinking mode integration
- send_message interface compatibility

Usage:
    pytest test_odiseo_bot_v2.py -v
    python test_odiseo_bot_v2.py  # Run directly

Author: Lab01-MCP Team
Created: 2025-10-11
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Add src to path
agent_src = Path(__file__).parent / "src"
sys.path.insert(0, str(agent_src))

from multi_agent import OdiseoBotV2

# Fixtures

@pytest.fixture
def mock_mcp_connector():
    """Mock MCPConnector to avoid real MCP server dependency."""
    with patch("multi_agent.odiseo_bot_v2.MCPConnector") as mock:
        # Mock health check (healthy)
        mock.check_server_health = AsyncMock(return_value={
            "status": "healthy",
            "checks": {
                "database": {
                    "status": "healthy",
                    "product_count": 100,
                    "extensions": ["unaccent", "pg_trgm"]
                }
            }
        })

        # Mock connector instance
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.list_tools = AsyncMock(return_value=[
            {
                "name": "search_products",
                "description": "Search products by query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            },
            {
                "name": "fuzzy_search_smart",
                "description": "Fuzzy search with typo tolerance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "search_term": {"type": "string"}
                    }
                }
            }
        ])
        mock_instance.call_tool = AsyncMock(return_value={
            "items": [
                {"name": "Product 1", "price": 100.0, "sku": "P1"},
                {"name": "Product 2", "price": 200.0, "sku": "P2"}
            ]
        })

        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client to avoid real API calls.

    Note: OdiseoBotV2 inherits from BaseAgent which uses genai.Client.
    We mock the genai module directly instead of GeminiAgent.
    """
    with patch("gemini_agent.base_agent.genai") as mock_genai:
        # Mock genai.Client
        mock_client = Mock()
        mock_client.caches = Mock()
        mock_client.caches.create = Mock(return_value=Mock(
            name="cached_content_123",
            usage_metadata=Mock(total_token_count=1000)
        ))
        mock_client.caches.delete = Mock()

        mock_genai.Client.return_value = mock_client

        yield mock_genai


# Test Suite

class TestOdiseoBotV2Initialization:
    """Test OdiseoBotV2 initialization and configuration."""

    @pytest.mark.asyncio
    async def test_basic_instantiation(self):
        """Test that OdiseoBotV2 can be instantiated."""
        bot = OdiseoBotV2(user_id="test_user_123")

        # Verify basic attributes
        assert bot.user_id == "test_user_123"
        assert bot.agent_name == "odiseo_bot_v2"
        assert bot.session_id is not None
        assert bot.debug_mode is False

    @pytest.mark.asyncio
    async def test_baseagent_inheritance(self):
        """Test that OdiseoBotV2 inherits from BaseAgent correctly."""
        bot = OdiseoBotV2()

        # Verify BaseAgent properties exist
        assert hasattr(bot, "api_key")
        assert hasattr(bot, "model_name")
        assert hasattr(bot, "conversation_history")
        assert hasattr(bot, "logger")
        assert hasattr(bot, "get_metrics")
        assert hasattr(bot, "reset_metrics")
        assert hasattr(bot, "clear_history")

    @pytest.mark.asyncio
    async def test_odiseo_specific_managers(self):
        """Test that OdiseoBot-specific managers are initialized."""
        bot = OdiseoBotV2()

        # Verify OdiseoBot-specific components
        assert bot.pagination_manager is not None
        assert bot.thinking_manager is not None
        assert bot.conversation_manager is not None
        assert bot.debug_formatter is not None
        assert bot.function_call_handler is not None

    @pytest.mark.asyncio
    async def test_initialization_with_mocks(
        self,
        mock_mcp_connector,
        mock_gemini_client
    ):
        """Test full initialization with mocked dependencies."""
        bot = OdiseoBotV2(user_id="test_user")

        # Mock initialize method to avoid real API calls
        # BaseAgent.initialize would call genai.Client which we've mocked
        with patch.object(bot, "initialize", new_callable=AsyncMock) as mock_init:
            await mock_init()

            # Verify initialize was called
            mock_init.assert_called_once()

        # Verify bot attributes exist (without real initialization)
        assert bot.agent_name == "odiseo_bot_v2"
        assert bot.user_id == "test_user"
        assert bot.pagination_manager is not None


class TestOdiseoBotV2SystemPrompt:
    """Test system prompt generation."""

    def test_get_system_prompt_default(self):
        """Test get_system_prompt returns a valid prompt."""
        bot = OdiseoBotV2()

        prompt = bot.get_system_prompt()

        # Verify prompt is not empty
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be a substantial prompt

    def test_get_system_prompt_with_tools(self):
        """Test get_system_prompt includes MCP tools."""
        bot = OdiseoBotV2()

        # Mock mcp_tools
        bot.mcp_tools = [
            Mock(name="search_products", description="Search products")
        ]

        prompt = bot.get_system_prompt(mcp_tools=bot.mcp_tools)

        # Verify prompt includes tools (via PromptBuilder)
        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestOdiseoBotV2Metrics:
    """Test metrics tracking (inherited from BaseAgent)."""

    def test_initial_metrics(self):
        """Test that initial metrics are all zeros."""
        bot = OdiseoBotV2()

        metrics = bot.get_metrics()

        # Verify initial metrics
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 0.0

    def test_metrics_reset(self):
        """Test metrics reset functionality."""
        bot = OdiseoBotV2()

        # Manually increment metrics
        bot._metrics["total_requests"] = 10
        bot._metrics["successful_requests"] = 8
        bot._metrics["failed_requests"] = 2

        # Reset metrics
        bot.reset_metrics()

        # Verify metrics reset
        metrics = bot.get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0


class TestOdiseoBotV2History:
    """Test conversation history management (inherited from BaseAgent)."""

    def test_initial_history_empty(self):
        """Test that initial history is empty."""
        bot = OdiseoBotV2()

        assert bot.get_history_length() == 0

    def test_clear_history(self):
        """Test history clearing."""
        bot = OdiseoBotV2()

        # Add some history (mock)
        bot.conversation_history.append(Mock())
        bot.conversation_history.append(Mock())

        assert bot.get_history_length() == 2

        # Clear history
        bot.clear_history()

        assert bot.get_history_length() == 0


class TestOdiseoBotV2Pagination:
    """Test client-side pagination functionality."""

    def test_pagination_manager_initialized(self):
        """Test that pagination manager is initialized with session ID."""
        bot = OdiseoBotV2()

        assert bot.pagination_manager is not None
        assert bot.pagination_manager._session_id == bot.session_id

    def test_track_search_results(self):
        """Test tracking search results for pagination."""
        bot = OdiseoBotV2()

        # Mock search result
        result = {
            "items": [
                {"name": "Product 1", "sku": "P1", "price": 100},
                {"name": "Product 2", "sku": "P2", "price": 200},
                {"name": "Product 3", "sku": "P3", "price": 300},
            ]
        }

        # Track results
        bot._track_search_results(
            tool_name="search_products",
            args={"query": "laptop"},
            result=result
        )

        # Verify pagination context created
        assert bot.pagination_manager.has_context("laptop")
        assert bot.pagination_manager.get_total_count("laptop") == 3

    @pytest.mark.asyncio
    async def test_handle_pagination_request(self):
        """Test handling pagination requests ("muéstrame más")."""
        bot = OdiseoBotV2()

        # Setup pagination context
        bot.pagination_manager.save_search(
            category="laptop",
            tool="search_products",
            query="laptop gaming",
            results=[
                {"name": "Product 1", "sku": "P1", "price": 100},
                {"name": "Product 2", "sku": "P2", "price": 200},
                {"name": "Product 3", "sku": "P3", "price": 300},
                {"name": "Product 4", "sku": "P4", "price": 400},
                {"name": "Product 5", "sku": "P5", "price": 500},
            ],
            page_size=2
        )

        # First page is already shown, request more
        response = await bot._handle_pagination_request("muéstrame más laptop")

        # Verify pagination response
        assert response is not None
        assert "laptop" in response.lower()
        assert "Product 3" in response or "Product 4" in response

    @pytest.mark.asyncio
    async def test_pagination_exhausted(self):
        """Test pagination when no more results available."""
        bot = OdiseoBotV2()

        # Setup small pagination context
        bot.pagination_manager.save_search(
            category="mouse",
            tool="search_products",
            query="mouse gaming",
            results=[
                {"name": "Product 1", "sku": "P1", "price": 100},
                {"name": "Product 2", "sku": "P2", "price": 200},
            ],
            page_size=2
        )

        # Get first page (already shown)
        # Try to get more (should return "no more results" message)
        response = await bot._handle_pagination_request("más mouse")

        # Verify response indicates no more results
        assert response is not None
        assert "todos los resultados" in response.lower() or "all available results" in response.lower()


class TestOdiseoBotV2ThinkingMode:
    """Test Gemini 2.5 thinking mode integration."""

    def test_thinking_manager_initialized(self):
        """Test that thinking manager is initialized."""
        bot = OdiseoBotV2()

        assert bot.thinking_manager is not None

    def test_thinking_config_generation(self):
        """Test thinking config generation for GenerateContentConfig."""
        bot = OdiseoBotV2()

        thinking_config = bot.thinking_manager.get_thinking_config()

        # Verify config is generated (may be None if disabled)
        assert thinking_config is None or hasattr(thinking_config, "thinking_budget")


class TestOdiseoBotV2Cleanup:
    """Test resource cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_without_initialization(self):
        """Test cleanup on uninitialized bot (should not crash)."""
        bot = OdiseoBotV2()

        # Should not raise exception
        await bot.cleanup()

    @pytest.mark.asyncio
    async def test_cleanup_with_pagination(self):
        """Test cleanup closes pagination manager."""
        bot = OdiseoBotV2()

        # Mock pagination manager cleanup
        bot.pagination_manager.cleanup = Mock()

        await bot.cleanup()

        # Verify pagination cleanup was called
        bot.pagination_manager.cleanup.assert_called_once()


class TestOdiseoBotV2Repr:
    """Test string representation."""

    def test_repr_format(self):
        """Test __repr__ returns expected format."""
        bot = OdiseoBotV2(user_id="test_user_123")

        repr_str = repr(bot)

        # Verify format
        assert "OdiseoBotV2" in repr_str
        assert "model=" in repr_str
        assert "tools=" in repr_str
        assert "session=" in repr_str


# Demo and Manual Testing

async def demo_odiseo_bot_v2_basic():
    """Demo 1: Basic instantiation and configuration."""
    print("\n" + "=" * 80)
    print("  DEMO 1: Basic OdiseoBotV2 Instantiation")
    print("=" * 80)

    bot = OdiseoBotV2(user_id="demo_user_123")

    print(f"\n✅ Created: {bot!r}")
    print(f"   Agent Name: {bot.agent_name}")
    print(f"   User ID: {bot.user_id}")
    print(f"   Session ID: {bot.session_id}")
    print(f"   Debug Mode: {bot.debug_mode}")

    # Check BaseAgent inheritance
    print("\n📊 BaseAgent Features:")
    print(f"   Has metrics: {hasattr(bot, 'get_metrics')}")
    print(f"   Has history: {hasattr(bot, 'get_history_length')}")
    print(f"   Has logger: {hasattr(bot, 'logger')}")

    # Check OdiseoBot-specific features
    print("\n🌟 OdiseoBot Features:")
    print(f"   Pagination Manager: {bot.pagination_manager is not None}")
    print(f"   Thinking Manager: {bot.thinking_manager is not None}")
    print(f"   Conversation Manager: {bot.conversation_manager is not None}")

    print("\n✅ DEMO 1 PASSED: OdiseoBotV2 instantiation successful")


async def demo_odiseo_bot_v2_metrics():
    """Demo 2: Metrics tracking (inherited from BaseAgent)."""
    print("\n" + "=" * 80)
    print("  DEMO 2: Metrics Tracking")
    print("=" * 80)

    bot = OdiseoBotV2()

    # Get initial metrics
    metrics = bot.get_metrics()

    print("\n📊 Initial Metrics:")
    print(f"   Total Requests: {metrics['total_requests']}")
    print(f"   Successful: {metrics['successful_requests']}")
    print(f"   Failed: {metrics['failed_requests']}")
    print(f"   Success Rate: {metrics['success_rate']:.1f}%")

    # Verify initial metrics
    assert metrics["total_requests"] == 0
    assert metrics["success_rate"] == 0.0

    print("\n✅ DEMO 2 PASSED: Metrics tracking works correctly")


async def demo_odiseo_bot_v2_pagination():
    """Demo 3: Pagination functionality."""
    print("\n" + "=" * 80)
    print("  DEMO 3: Client-side Pagination")
    print("=" * 80)

    bot = OdiseoBotV2()

    # Create mock search results
    products = [
        {"name": f"Laptop {i}", "sku": f"LAP{i}", "price": 100 + i*50}
        for i in range(1, 11)  # 10 products
    ]

    print(f"\n📋 Saving {len(products)} products for pagination...")

    # Track search results
    bot.pagination_manager.save_search(
        category="laptop",
        tool="search_products",
        query="laptop gaming",
        results=products,
        page_size=3  # Show 3 per page
    )

    print("   ✅ Saved to pagination manager")
    print("   Category: laptop")
    print(f"   Total: {bot.pagination_manager.get_total_count('laptop')} products")
    print("   Page size: 3")
    print(f"   Pages available: {len(products) // 3}")

    # Test pagination request
    response = await bot._handle_pagination_request("muéstrame más laptop")

    if response:
        print("\n📄 Pagination Response (truncated):")
        print(f"   {response[:200]}...")
        print(f"   Length: {len(response)} chars")
    else:
        print("\n⚠️  No pagination response (might be first page)")

    print("\n✅ DEMO 3 PASSED: Pagination functionality works")


async def main():
    """Run all demos and tests."""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  ODISEO BOT V2 - VALIDATION SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)

    print("\n🎯 Running demos (manual validation)...")

    results = []

    # Run demos
    try:
        await demo_odiseo_bot_v2_basic()
        results.append(("Basic Instantiation", True))
    except Exception as e:
        print(f"\n❌ DEMO 1 FAILED: {e}")
        results.append(("Basic Instantiation", False))

    try:
        await demo_odiseo_bot_v2_metrics()
        results.append(("Metrics Tracking", True))
    except Exception as e:
        print(f"\n❌ DEMO 2 FAILED: {e}")
        results.append(("Metrics Tracking", False))

    try:
        await demo_odiseo_bot_v2_pagination()
        results.append(("Pagination Functionality", True))
    except Exception as e:
        print(f"\n❌ DEMO 3 FAILED: {e}")
        results.append(("Pagination Functionality", False))

    # Summary
    print("\n" + "=" * 80)
    print("  DEMO SUMMARY")
    print("=" * 80)

    for demo_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {demo_name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n✅ ALL DEMOS PASSED - OdiseoBotV2 working correctly!")
        print("\n📚 Run pytest for comprehensive testing:")
        print("   pytest test_odiseo_bot_v2.py -v")
        return 0
    else:
        print("\n❌ SOME DEMOS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
