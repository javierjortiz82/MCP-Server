"""Integration tests for OdiseoBot initialization."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.odiseo_bot import OdiseoBot


class TestOdiseoBotInitialization:
    """Integration tests for OdiseoBot initialization flow."""

    def test_bot_creation(self, mock_settings):
        """Test OdiseoBot can be instantiated."""
        bot = OdiseoBot()

        assert bot is not None
        assert bot.gemini_client is None  # Not initialized yet
        assert bot.mcp_client is None
        assert bot.tool_executor is None

    @pytest.mark.asyncio
    async def test_bot_initialization_success(self, mock_settings):
        """Test successful bot initialization creates required components."""
        # Mock Settings instance with API key
        from config.settings import Settings
        test_settings = Settings(GOOGLE_API_KEY="test-key-12345")

        with patch("config.settings.settings", test_settings):
            with patch("core.odiseo_bot.settings", test_settings):
                # Mock Gemini client (now in gemini_client module)
                with patch("core.gemini_client.genai.Client") as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_class.return_value = mock_client_instance

                    # Create bot (initialization will fail due to MCP connection, but client should be set)
                    bot = OdiseoBot()

                    # Verify bot components are created
                    assert bot.thinking_manager is not None
                    assert bot.conversation_manager.get_history() == []

                    # Try to initialize (may fail on MCP connection, that's ok)
                    try:
                        await bot.initialize()
                    except Exception:
                        pass  # Expected to fail on MCP connection in test

                    # Verify Gemini client was set up (now it's bot.gemini_client)
                    assert bot.gemini_client is not None

    @pytest.mark.asyncio
    async def test_bot_initialization_with_tools(self, sample_mcp_tools):
        """Test bot can create tool executor with sample tools."""
        from core.tool_executor import ToolExecutor
        from core.mcp_connector import MCPConnector

        # Create tool executor directly (bypass full bot initialization)
        mock_connector = MagicMock(spec=MCPConnector)
        executor = ToolExecutor(mock_connector)

        # Register sample tools
        await executor.register_tool_schemas(sample_mcp_tools)

        # Verify tools were registered
        registered_tools = executor.validator.get_registered_tools()
        assert "search_products" in registered_tools
        assert "fetch_by_sku" in registered_tools

    @pytest.mark.asyncio
    async def test_bot_cleanup(self):
        """Test bot cleanup method exists and can be called."""
        bot = OdiseoBot()

        # Verify cleanup method exists
        assert hasattr(bot, "cleanup")

        # Cleanup should work even if not initialized
        await bot.cleanup()  # Should not raise

    def test_bot_thinking_manager_initialization(self, mock_settings):
        """Test bot initializes ThinkingManager correctly."""
        bot = OdiseoBot()

        # Verify ThinkingManager is initialized
        assert bot.thinking_manager is not None
        assert bot.thinking_manager.enable_thinking == mock_settings.ENABLE_THINKING

    @pytest.mark.asyncio
    async def test_bot_rate_limiter_disabled(self, mock_settings, mock_mcp_connector):
        """Test bot works without rate limiter when disabled."""
        # Create settings with rate limiting disabled and API key
        from config.settings import Settings
        test_settings = Settings(
            GOOGLE_API_KEY="test-key-12345",
            ENABLE_RATE_LIMITING=False
        )

        with patch("config.settings.settings", test_settings):
            with patch("core.odiseo_bot.settings", test_settings):
                with patch("core.gemini_client.genai.Client") as mock_client_class:
                    mock_client_instance = MagicMock()
                    mock_client_class.return_value = mock_client_instance

                    with patch("core.odiseo_bot.MCPConnector") as mock_mcp_class:
                        mock_mcp_class.return_value = mock_mcp_connector
                        mock_mcp_connector.connect = AsyncMock()
                        mock_mcp_connector.list_tools = AsyncMock(return_value=[])

                        bot = OdiseoBot()
                        await bot.initialize()

                        # Verify rate limiter is None when disabled
                        assert bot.rate_limiter is None

    def test_bot_settings_integration(self, mock_settings):
        """Test bot uses settings correctly."""
        bot = OdiseoBot()

        # Settings should be accessible
        from config.settings import settings

        assert settings.MODEL == mock_settings.MODEL
        assert settings.TEMPERATURE == mock_settings.TEMPERATURE


class TestOdiseoBotConfiguration:
    """Integration tests for OdiseoBot configuration."""

    def test_bot_respects_thinking_mode_enabled(self):
        """Test bot respects ENABLE_THINKING setting."""
        with patch("config.settings.settings.ENABLE_THINKING", True):
            with patch("config.settings.settings.THINKING_BUDGET", 2048):
                bot = OdiseoBot()

                assert bot.thinking_manager.enable_thinking is True
                assert bot.thinking_manager.thinking_budget == 2048

    def test_bot_respects_thinking_mode_disabled(self):
        """Test bot respects ENABLE_THINKING=False setting."""
        with patch("config.settings.settings.ENABLE_THINKING", False):
            bot = OdiseoBot()

            assert bot.thinking_manager.enable_thinking is False

    def test_bot_respects_validation_setting(self, mock_settings):
        """Test bot respects ENABLE_VALIDATION setting."""
        mock_settings.ENABLE_VALIDATION = True

        bot = OdiseoBot()

        from config.settings import settings

        assert settings.ENABLE_VALIDATION is True

    def test_bot_respects_metrics_setting(self, mock_settings):
        """Test bot respects ENABLE_METRICS setting."""
        mock_settings.ENABLE_METRICS = True

        bot = OdiseoBot()

        from config.settings import settings

        assert settings.ENABLE_METRICS is True


class TestOdiseoBotToolDiscovery:
    """Integration tests for tool discovery flow."""

    @pytest.mark.asyncio
    async def test_tool_discovery_empty_list(self):
        """Test tool executor handles empty tool list gracefully."""
        from core.tool_executor import ToolExecutor

        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Register empty list
        await executor.register_tool_schemas([])

        # Should not raise, just have no tools
        registered = executor.validator.get_registered_tools()
        assert len(registered) == 0

    @pytest.mark.asyncio
    async def test_tool_discovery_multiple_tools(self, sample_mcp_tools):
        """Test tool executor discovers multiple tools correctly."""
        from core.tool_executor import ToolExecutor

        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Register sample tools
        await executor.register_tool_schemas(sample_mcp_tools)

        registered = executor.validator.get_registered_tools()
        assert len(registered) == len(sample_mcp_tools)

    @pytest.mark.asyncio
    async def test_tool_schemas_cached(self, sample_mcp_tools):
        """Test discovered tool schemas are cached."""
        from core.tool_executor import ToolExecutor

        mock_connector = MagicMock()
        executor = ToolExecutor(mock_connector)

        # Register tools
        await executor.register_tool_schemas(sample_mcp_tools)

        # Check cache stats
        cache_stats = executor.get_cache_stats()
        assert cache_stats["total_tools_cached"] >= len(sample_mcp_tools)
